# app.py
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from dataclasses import dataclass
from typing import Tuple, List
import re
from scipy.stats import chi2_contingency 

st.set_page_config(page_title="CAROL / eADMS Audit", layout="wide")

# --- 1) Map finding rows -> system buckets --------------------
SYSTEM_PATTERNS = [
    # (bucket name, list of regexes to search in category/description)
    ("Flight Controls", [
        r"\bflight control", r"\bailer", r"\belevat", r"\brudder",
        r"\btrim\b", r"\bflap", r"\bspoiler", r"\bslat", r"\bcontrol column|\byoke\b|\bstick\b",
        r"\bservo\b", r"\bactuator\b(?!\s*fuel)", r"\bcontrol\s*cable", r"\bautopilot\b"
    ]),
    ("Powerplant/Propulsion", [
        r"\bpower plant|\bpowerplant|\bengine", r"\bpropeller", r"\bturbo(charger)?",
        r"\bcompressor\b", r"\bfuel (control|metering|nozzle|pump)", r"\bignition\b"
    ]),
    ("Hydraulic/Pneumatic", [
        r"\bhydraul", r"\bpneumat", r"\baccumulator\b", r"\bactuator\b"
    ]),
    ("Avionics/Electrical", [
        r"\bavionic", r"\belectri", r"\bbus\b", r"\bEFIS\b|\bPFD\b|\bMFD\b|\bFMS\b|\bADC\b|\bIRS\b",
        r"\bradio\b", r"\btransponder\b", r"\bantenna\b"
    ]),
    ("Landing Gear/Brakes", [
        r"\blanding gear|\bgear\b", r"\bbrake", r"\btire\b|\bwheel\b|\bstrut\b"
    ]),
    ("Airframe/Structures", [
        r"\bstructure|\bairframe|\bfuselage|\bwing\b|\bempennage\b|\bspar\b|\brib\b|\bskin\b"
    ]),
    ("Fluids/Fuel/Oil", [
        r"\bfuel\b", r"\boil\b", r"\bhydraul"
    ]),
]

def _first_match_bucket(cat: str, desc: str | None = None) -> str | None:
    text = (cat or "")
    if desc:
        text += " " + desc
    text = text.lower()
    for bucket, pats in SYSTEM_PATTERNS:
        if any(re.search(p, text) for p in pats):
            return bucket
    return None

def add_system_buckets_to_findings(finding_f: pd.DataFrame) -> pd.DataFrame:
    if finding_f.empty:
        return finding_f
    df = finding_f.copy()
    # Choose the best text fields you have
    cat_col  = "finding_category" if "finding_category" in df.columns else "cat_text"
    desc_col = "finding_description" if "finding_description" in df.columns else None
    if cat_col not in df.columns:
        df["system_bucket"] = pd.NA
        return df

    df["system_bucket"] = df.apply(
        lambda r: _first_match_bucket(
            str(r.get(cat_col, "")),
            str(r.get(desc_col, "")) if desc_col in df.columns else None
        ),
        axis=1
    )
    return df

# --- 2) Roll up to event level --------------------------------
def event_level_with_system_flags(event_f: pd.DataFrame, finding_f: pd.DataFrame) -> pd.DataFrame:
    if event_f.empty or finding_f.empty or "ev_id" not in event_f.columns or "ev_id" not in finding_f.columns:
        return event_f.copy()

    f = add_system_buckets_to_findings(finding_f)
    # any flight-controls finding per event?
    fc = (f.assign(_is_fc = f["system_bucket"].eq("Flight Controls"))
            .groupby("ev_id")["_is_fc"].max().astype(bool).rename("has_flight_controls"))

    # most frequent system bucket per event (for bar chart)
    top_sys = (f.dropna(subset=["system_bucket"])
                 .groupby(["ev_id","system_bucket"]).size()
                 .reset_index(name="n")
                 .sort_values(["ev_id","n"], ascending=[True, False])
                 .drop_duplicates("ev_id")
                 .set_index("ev_id")["system_bucket"]
                 .rename("system_bucket"))

    ev2 = event_f.copy()
    ev2 = ev2.merge(fc, how="left", left_on="ev_id", right_index=True)
    ev2 = ev2.merge(top_sys, how="left", left_on="ev_id", right_index=True)
    ev2["has_flight_controls"] = ev2["has_flight_controls"].fillna(False)
    return ev2

# --- 3) Build outputs used in the System Risk tab -------------
from scipy.stats import chi2_contingency

def system_risk_tables(event_f: pd.DataFrame, finding_f: pd.DataFrame):
    """
    Returns:
      ct   : by-system bucket summary (fatals, total, pct_fatal)
      xt   : 2x2 table (Flight controls vs Other) × (Nonfatal, Fatal)
      stats: dict with chi2, df, p_value (when valid), odds ratio + CI, expected counts, residuals
    """
    # --- roll up ---
    evx = event_level_with_system_flags(event_f, finding_f)
    if evx.empty or "ev_highest_injury" not in evx.columns:
        return pd.DataFrame(), pd.DataFrame(), {}

    # --- by-system bucket contingency (event level, "top" system per event) ---
    ct = pd.DataFrame()
    if "system_bucket" in evx.columns:
        tmp = evx.dropna(subset=["system_bucket"]).copy()
        fat_bool = tmp["ev_highest_injury"].astype("string").str.upper().eq("FATL")
        tmp["is_fatal"] = np.where(fat_bool.fillna(False), 1, 0)
        ct = (tmp.groupby("system_bucket", dropna=False)
                .agg(fatals=("is_fatal","sum"), total=("is_fatal","count"))
                .reset_index())
        ct["pct_fatal"] = np.where(ct["total"]>0, 100.0*ct["fatals"]/ct["total"], 0.0)
        ct = ct.sort_values("pct_fatal", ascending=False, kind="mergesort")

    # --- 2×2: Flight controls vs Other × Fatal vs Nonfatal ---
    xt = evx.copy()
    fat_bool_all = xt["ev_highest_injury"].astype("string").str.upper().eq("FATL")
    xt["is_fatal"] = fat_bool_all.fillna(False)
    xt["is_fc"]    = xt["has_flight_controls"].fillna(False).astype(bool)

    xt = pd.crosstab(xt["is_fc"], xt["is_fatal"])
    # make sure both rows/cols exist (even if zeros)
    xt = xt.reindex(index=[False, True], columns=[False, True], fill_value=0)
    # pretty labels
    xt.index = ["Other systems", "Flight controls"]
    xt.columns = ["Nonfatal", "Fatal"]

    stats_payload = {}
    # If any row or column is all zeros, chi-square is undefined; guard it.
    row_sums = xt.sum(axis=1).to_numpy()
    col_sums = xt.sum(axis=0).to_numpy()
    chi2_ok = (row_sums > 0).all() and (col_sums > 0).all()

    # odds ratio with Haldane–Anscombe correction (always safe to compute)
    a, b = xt.loc["Other systems",  ["Nonfatal","Fatal"]].to_numpy()
    c, d = xt.loc["Flight controls",["Nonfatal","Fatal"]].to_numpy()
    a2, b2, c2, d2 = a+0.5, b+0.5, c+0.5, d+0.5
    or_val = (d2/c2) / (b2/a2)
    se_log_or = np.sqrt(1/a2 + 1/b2 + 1/c2 + 1/d2)
    log_or = np.log(or_val)
    or_lo = float(np.exp(log_or - 1.96*se_log_or))
    or_hi = float(np.exp(log_or + 1.96*se_log_or))

    if chi2_ok:
        chi2, p, dof, expected = chi2_contingency(xt.to_numpy(), correction=False)
        expected = np.asarray(expected, dtype=float)
        resid = (xt.to_numpy() - expected) / np.sqrt(np.where(expected==0, np.nan, expected))
        stats_payload.update({
            "chi2": float(chi2),
            "df": int(dof),
            "p_value": float(p),
            "expected_counts": expected,
            "std_residuals": resid,
        })
    else:
        # no chi-square; still return useful info
        stats_payload.update({
            "chi2": None, "df": None, "p_value": None,
            "expected_counts": None, "std_residuals": None,
        })

    stats_payload.update({
        "odds_ratio_FC_vs_Other": float(or_val),
        "or_95CI_low": or_lo,
        "or_95CI_high": or_hi,
    })

    return ct, xt, stats_payload

# --- FilterSpec (use this or import your real one) ---
@dataclass
class FilterSpec:
    years: tuple[int, int] | None = None
    severity: list[str] | None = None
    phases: list[str] | None = None
    occurrences: list[str] | None = None
    defining_only: bool = False
    makes: list[str] | None = None
    model_contains: str | None = None
    parts: list[str] | None = None  # if you want FAR part filtering

# --- Project paths / imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (
    OUT_EVENT_LEVEL, OUT_FINDING_LEVEL_LABELED, OUT_SEQ_LABELED
)

# Optional fallback: load pipeline to build Parquet if missing
def _ensure_parquets():
    missing = [p for p in [OUT_EVENT_LEVEL, OUT_FINDING_LEVEL_LABELED, OUT_SEQ_LABELED] if not Path(p).exists()]
    if not missing:
        return
    try:
        from loaders import read_events, read_findings, read_aircraft, read_events_sequence
        from labelers import build_event_level, build_finding_level, label_findings, label_sequence
        # Build minimal to satisfy the dashboard
        events   = read_events()
        findings = read_findings()
        acft     = read_aircraft()
        seq      = read_events_sequence()
        event_level = build_event_level(events, acft)
        finding_lvl = build_finding_level(events, findings, acft)
        finding_lab = label_findings(finding_lvl)
        seq_labeled = label_sequence(seq)
        event_level.to_parquet(OUT_EVENT_LEVEL, index=False)
        finding_lab.to_parquet(OUT_FINDING_LEVEL_LABELED, index=False)
        seq_labeled.to_parquet(OUT_SEQ_LABELED, index=False)
    except Exception as e:
        st.error(f"Could not build Parquet outputs automatically. Error: {e}")


@st.cache_data(show_spinner=False)
def load_data():
    _ensure_parquets()
    ev   = pd.read_parquet(OUT_EVENT_LEVEL) if Path(OUT_EVENT_LEVEL).exists() else pd.DataFrame()
    flab = pd.read_parquet(OUT_FINDING_LEVEL_LABELED) if Path(OUT_FINDING_LEVEL_LABELED).exists() else pd.DataFrame()
    seq  = pd.read_parquet(OUT_SEQ_LABELED) if Path(OUT_SEQ_LABELED).exists() else pd.DataFrame()

    year_series = []
    for d in (ev, flab, seq):
        if "ev_year" in d.columns:
            s = pd.to_numeric(d["ev_year"], errors="coerce").dropna().astype(int)
            if not s.empty:
                year_series.append(s)

    if year_series:
        vals = pd.concat(year_series, ignore_index=True)
        min_year, max_year = int(vals.min()), int(vals.max())
    else:
        # sensible defaults if everything is empty
        min_year, max_year = 2009, 2025

    # hygiene
    for df in (ev, flab, seq):
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        for c in ["ev_year", "Aircraft_Key", "Occurrence_No", "phase_no", "eventsoe_no", "Defining_ev"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if "ev_date" in df.columns:
            df["ev_date"] = pd.to_datetime(df["ev_date"], errors="coerce")
        for s in ["ev_highest_injury", "acft_make", "acft_model", "occurrence_meaning", "phase_meaning"]:
            if s in df.columns:
                df[s] = df[s].astype("string")
    return ev, flab, seq
 
# ----------------------------------------
# Load data
event_df, finding_df, seq_df = load_data()

# ----------------------------------------
# Sidebar controls (define ONCE)
with st.sidebar:
    st.header("Filters")

    # Year slider from actual data
    def _collect_year_bounds(*dfs):
        vals = pd.Series(dtype="float64")
        for d in dfs:
            if isinstance(d, pd.DataFrame) and "ev_year" in d.columns:
                vals = pd.concat([vals, pd.to_numeric(d["ev_year"], errors="coerce")])
        vals = vals.dropna()
        if vals.empty:
            return 2009, 2025
        return int(vals.min()), int(vals.max())

    yr_min, yr_max = _collect_year_bounds(event_df, finding_df, seq_df)
    year_range = st.slider("Event Year", min_value=yr_min, max_value=yr_max,
                           value=(max(2009, yr_min), yr_max), step=1)

    sev_opts = ["FATL", "SERS", "MINR", "NONE"]
    sev_sel = st.multiselect("Highest Injury (event/finding)", sev_opts, default=sev_opts)

    # Sequence fields
    phases = sorted(seq_df.get("phase_meaning", pd.Series(dtype="string")).dropna().unique().tolist())
    phase_sel = st.multiselect("Phase of Flight (sequence)", phases, default=[])

    occs = sorted(seq_df.get("occurrence_meaning", pd.Series(dtype="string")).dropna().unique().tolist())
    occ_sel = st.multiselect("Occurrence (sequence)", occs, default=[])

    def_only = st.checkbox("Defining events only (sequence)", value=False)

    # FAR Parts (optional)
    parts = st.multiselect("FAR Parts", options=["91", "121", "135"], default=["91", "121", "135"])

    # Make/model (from finding-level)
    makes = sorted(finding_df.get("acft_make", pd.Series(dtype="string")).dropna().unique().tolist())
    make_sel = st.multiselect("Make (finding-level)", makes, default=[])
    model_sel = st.text_input("Model contains (substring, case-insensitive)", "")

# ----------------------------------------
# Build FilterSpec object from controls
spec = FilterSpec(
    years=(year_range[0], year_range[1]),
    severity=sev_sel,
    phases=phase_sel,
    occurrences=occ_sel,
    defining_only=def_only,
    makes=make_sel,
    model_contains=model_sel,
    parts=parts,
)
# -------------------------------
# Lightweight filtering helpers
# -------------------------------
def _between_years(df: pd.DataFrame, years: Tuple[int, int]) -> pd.DataFrame:
    if df.empty or "ev_year" not in df.columns or years is None:
        return df
    y = pd.to_numeric(df["ev_year"], errors="coerce")
    return df[(y >= years[0]) & (y <= years[1])]

def apply_filters(event_df, finding_df, seq_df, spec: FilterSpec):
    ev = _between_years(event_df.copy(), spec.years)
    fl = _between_years(finding_df.copy(), spec.years)
    sq = _between_years(seq_df.copy(), spec.years)

    # severity on event & finding if present
    if spec.severity:
        if "ev_highest_injury" in ev.columns:
            ev = ev[ev["ev_highest_injury"].isin(spec.severity)]
        if "ev_highest_injury" in fl.columns:
            fl = fl[fl["ev_highest_injury"].isin(spec.severity)]

    # FAR part (if you’ve labeled it; handles either numeric or string)
    if spec.parts and "far_part" in ev.columns:
        ev = ev[ev["far_part"].astype(str).isin(spec.parts)]
    if spec.parts and "far_part" in fl.columns:
        fl = fl[fl["far_part"].astype(str).isin(spec.parts)]
    if spec.parts and "far_part" in sq.columns:
        sq = sq[sq["far_part"].astype(str).isin(spec.parts)]

    # sequence filters
    if spec.defining_only and "Defining_ev" in sq.columns:
        sq = sq[sq["Defining_ev"] == 1]
    if spec.phases and "phase_meaning" in sq.columns:
        sq = sq[sq["phase_meaning"].isin(spec.phases)]
    if spec.occurrences and "occurrence_meaning" in sq.columns:
        sq = sq[sq["occurrence_meaning"].isin(spec.occurrences)]

    # finding-level make/model
    if spec.makes and "acft_make" in fl.columns:
        fl = fl[fl["acft_make"].isin(spec.makes)]
    if spec.model_contains and "acft_model" in fl.columns:
        fl = fl[fl["acft_model"].str.contains(spec.model_contains, case=False, na=False)]

    return ev, fl, sq

# -------------------------------
# Minimal analytics for System Risk
# -------------------------------
def build_contingency(ev: pd.DataFrame) -> pd.DataFrame:
    """
    Expect event-level columns:
      - system_bucket (or a similar categorical you built in your pipeline)
      - ev_highest_injury (FATL/SERS/MINR/NONE)
    """
    if ev.empty or "ev_highest_injury" not in ev.columns:
        return pd.DataFrame()

    system_col = "system_bucket" if "system_bucket" in ev.columns else None
    if system_col is None:
        # fallback: try 'system_component' if you named it differently
        for c in ["system_component", "System_Component", "finding_system"]:
            if c in ev.columns:
                system_col = c
                break
    if system_col is None:
        return pd.DataFrame()

    tmp = ev[[system_col, "ev_highest_injury"]].copy()
    tmp["is_fatal"] = (tmp["ev_highest_injury"] == "FATL").astype(int)
    agg = (tmp.groupby(system_col)
              .agg(fatals=("is_fatal","sum"),
                   total =(system_col,"count"))
              .reset_index()
              .rename(columns={system_col:"system_bucket"}))
    agg["pct_fatal"] = np.where(agg["total"]>0, 100.0*agg["fatals"]/agg["total"], 0.0)
    return agg.sort_values("pct_fatal", ascending=False)

def chisq_table(ev: pd.DataFrame) -> pd.DataFrame:
    """
    2×2 table: Flight Controls vs Other  × Fatal vs Nonfatal
    Requires a system column containing 'Flight Controls' bucket.
    """
    system_col = "system_bucket" if "system_bucket" in ev.columns else None
    if system_col is None:
        for c in ["system_component", "System_Component", "finding_system"]:
            if c in ev.columns:
                system_col = c
                break
    if ev.empty or system_col is None or "ev_highest_injury" not in ev.columns:
        return pd.DataFrame()

    ev = ev.copy()
    ev["is_fatal"] = (ev["ev_highest_injury"] == "FATL")
    ev["is_fcs"]   = ev[system_col].fillna("").str.contains("flight control", case=False, na=False) | \
                     ev[system_col].isin(["Flight Controls","Flight Control","FLT CTRL"])

    xt = pd.crosstab(ev["is_fcs"], ev["is_fatal"])
    # pretty labels
    xt.index = ["Other systems","Flight controls"]
    xt.columns = ["Nonfatal","Fatal"]
    return xt

def pct_notna(series) -> float:
    if series is None:
        return 0.0
    s = pd.Series(series)
    if s.empty:
        return 0.0
    return float(pd.notna(s).mean() * 100.0)

# -------------------------------
# Apply filters once
# -------------------------------
event_f, finding_f, seq_f = apply_filters(event_df, finding_df, seq_df, spec)

# -------------------------------
# Top banner + quick sanity
# -------------------------------

st.title("CAROL / eADMS Audit Dashboard")
st.caption(f"Loaded rows — events: {len(event_df):,} | findings: {len(finding_df):,} | sequence: {len(seq_df):,}")

if event_df.empty and finding_df.empty and seq_df.empty:
    st.error("No data found. Make sure CSVs are in data/raw and run your build step to create Parquet files in data/out.")
    st.stop()

# -------------------------------
# Tabs
# -------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Phase×Occurrence", "Findings", "System Risk"])

# ---- Overview tab
with tab1:
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        st.metric("Unique Events", int(event_f["ev_id"].nunique()) if "ev_id" in event_f.columns else len(event_f))
    with c2:
        st.metric("Findings (rows)", len(finding_f))
    with c3:
        st.metric("Sequences (rows)", len(seq_f))
    with c4:
        occ_series = seq_f["occurrence_meaning"] if "occurrence_meaning" in seq_f.columns else pd.Series(dtype="float64")
        st.metric("Occurrence label coverage", f"{pct_notna(occ_series):.1f}%")
    with c5:
        if "phase_meaning_primary" in seq_f.columns:
            ph_cov = seq_f["phase_meaning_primary"]
        elif "phase_meaning" in seq_f.columns:
            ph_cov = seq_f["phase_meaning"]
        else:
            ph_cov = pd.Series(dtype="float64")
        st.metric("Phase label coverage", f"{pct_notna(ph_cov):.1f}%")

    st.divider()
    st.write("Use the sidebar to filter the dataset. Other tabs will update automatically.")

# ---- Phase × Occurrence heatmap
with tab2:
    st.subheader("Phase × Occurrence Heatmap (Sequence)")
    if {"phase_meaning","occurrence_meaning"}.issubset(seq_f.columns):
        top_occ   = seq_f["occurrence_meaning"].value_counts().head(25).index.tolist()
        top_phase = seq_f["phase_meaning"].value_counts().head(25).index.tolist()
        heat = (seq_f[seq_f["occurrence_meaning"].isin(top_occ) & seq_f["phase_meaning"].isin(top_phase)]
                .groupby(["phase_meaning","occurrence_meaning"])
                .size().reset_index(name="count"))
        st.altair_chart(
            alt.Chart(heat).mark_rect().encode(
                x=alt.X("occurrence_meaning:N", sort=top_occ, title="Occurrence"),
                y=alt.Y("phase_meaning:N", sort=top_phase, title="Phase"),
                color=alt.Color("count:Q", title="Count"),
                tooltip=["phase_meaning","occurrence_meaning","count"]
            ).properties(height=500),
            use_container_width=True
        )
    else:
        st.info("Sequence table missing required columns for this chart.")

# ---- Findings tab
with tab3:
    st.subheader("Top Finding Categories by Injury Severity")
    if {"finding_category","ev_highest_injury"}.issubset(finding_f.columns):
        topN = st.slider("Top N categories (by FATL)", 5, 30, 20, step=1)
        ct = (pd.crosstab(finding_f["finding_category"], finding_f["ev_highest_injury"])
                .assign(_FATL=lambda d: d.get("FATL", 0))
                .sort_values("_FATL", ascending=False)
                .drop(columns=["_FATL"]))
        top_cats = (ct.head(topN).reset_index()
                      .melt(id_vars="finding_category", var_name="injury", value_name="count"))
        st.altair_chart(
            alt.Chart(top_cats).mark_bar().encode(
                x=alt.X('count:Q', title='Count'),
                y=alt.Y('finding_category:N', sort='-x', title='Finding category'),
                color=alt.Color('injury:N', title='Injury'),
                tooltip=['finding_category','injury','count']
            ).properties(height=30*min(topN, 25)),
            use_container_width=True
        )
    else:
        st.info("Finding-level data missing required columns for this chart.")

# ---- System Risk tab
with tab4:
    st.subheader("Fatality risk by system/component (derived from findings)")

    if event_df.empty or finding_df.empty:
        st.info("Need both event-level and finding-level data.")
    else:
        ct, xt, stats = system_risk_tables(event_f, finding_f)

        # By-system table + bar
        if ct.empty:
            st.info("No system buckets derived. Check that your finding categories/descriptions are present.")
        else:
            st.markdown("**By system bucket (event-level, top bucket per event)**")
            st.dataframe(ct, use_container_width=True)

            st.altair_chart(
                alt.Chart(ct).mark_bar().encode(
                    y=alt.Y("system_bucket:N", sort='-x', title="System"),
                    x=alt.X("pct_fatal:Q", title="Fatality %"),
                    tooltip=["system_bucket","fatals","total","pct_fatal"]
                ).properties(height=420),
                use_container_width=True
            )

            # Download
            st.download_button(
                "Download system-bucket table (CSV)",
                data=ct.to_csv(index=False).encode("utf-8"),
                file_name="system_bucket_fatality_rates.csv",
                mime="text/csv"
            )

        # 2×2 table
        if not xt.empty:
            st.markdown("**Flight Controls vs Other — Fatal vs Nonfatal (2×2)**")
            st.dataframe(xt, use_container_width=True)

            st.download_button(
                "Download 2x2 table (CSV)",
                data=xt.to_csv().encode("utf-8"),
                file_name="fc_vs_other_2x2.csv",
                mime="text/csv"
            )

        # Stats
        if stats:
            st.markdown("**Odds ratio (Fatal odds: Flight Controls vs Other)**")
            st.write({
                "odds_ratio": round(stats["odds_ratio_FC_vs_Other"], 3),
                "95% CI": (round(stats["or_95CI_low"], 3), round(stats["or_95CI_high"], 3)),
            })

            if stats.get("chi2") is None:
                st.warning(
                    "Chi-square not computed: at least one row or column in the 2×2 table sums to zero "
                    "(no events in a group or no fatals/nonfatals under current filters)."
                )
            else:
                st.markdown("**Chi-square test (independence)**")
                st.write({
                    "chi2": round(stats["chi2"], 4),
                    "df": stats["df"],
                    "p_value": f'{stats["p_value"]:.4g}',
                })

                # Expected counts and standardized residuals (optional display)
                exp_df = pd.DataFrame(stats["expected_counts"],
                                      index=xt.index, columns=xt.columns).round(2)
                st.expander("Expected counts (under independence)").dataframe(exp_df, use_container_width=True)

                resid = pd.DataFrame(stats["std_residuals"],
                                     index=xt.index, columns=xt.columns).round(2)
                st.expander("Standardized residuals").dataframe(resid, use_container_width=True)