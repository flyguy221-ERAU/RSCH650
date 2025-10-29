# main.py
from __future__ import annotations

import pandas as pd

from audit import quick_audit
from config import (
    DICT_CSV,  # eADMS data dictionary (ground truth for decoding)
    OUT_EVENT_LEVEL,
    OUT_FINDING_LEVEL,
    OUT_FINDING_LEVEL_LABELED,
    OUT_SEQ_LABELED,
)
from labelers import (
    build_event_level,
    build_finding_level,
    label_findings,
    label_sequence,
)
from loaders import read_aircraft, read_events, read_events_sequence, read_findings


def pct(series_like) -> float:
    """Return % non-null (0.0-100.0) for any Series-like; safe on None or missing."""
    try:
        s = pd.Series(series_like)
        return float(s.notna().mean() * 100.0)
    except Exception:
        return 0.0


def existing(cols: list[str], df: pd.DataFrame) -> list[str]:
    """Filter a list of column names to those present in df."""
    return [c for c in cols if c in df.columns]


def main():
    # -------------------------
    # Load raw frames
    # -------------------------
    events = read_events()  # ev_id, ev_year, ev_date, ev_highest_injury, ...
    findings = read_findings()  # finding_description, codes, Cause_Factor, ...
    aircraft = read_aircraft()  # ev_id, Aircraft_Key, acft_make, acft_model
    seq = read_events_sequence()  # ev_id, Aircraft_Key, Occurrence_No, phase_no, Occurrence_Code, Defining_ev

    # -------------------------
    # Build base tables
    # -------------------------
    event_level = build_event_level(events, aircraft)
    finding_lvl = build_finding_level(events, findings, aircraft)

    # -------------------------
    # Label sequence & findings (dictionary-native decoding)
    # -------------------------
    seq_labeled = label_sequence(seq, dict_csv_path=DICT_CSV)
    finding_lab = label_findings(finding_lvl)

    # Optional: show decoder hit mix (exact vs right-3)
    from decoder import build_occ_phase_maps

    exact_map, right3_map, _ = build_occ_phase_maps(DICT_CSV)
    occ = seq["Occurrence_Code"].astype("string").str.zfill(6)
    hits_exact = occ.map(exact_map).notna().sum()
    hits_r3 = occ.str[-3:].map(right3_map).notna().sum()
    print(f"Decoder hits — exact: {hits_exact:,} | right3: {hits_r3:,}")

    # -------------------------
    # Save Parquet outputs
    # -------------------------
    OUT_EVENT_LEVEL.parent.mkdir(parents=True, exist_ok=True)
    event_level.to_parquet(OUT_EVENT_LEVEL, index=False)
    finding_lvl.to_parquet(OUT_FINDING_LEVEL, index=False)
    finding_lab.to_parquet(OUT_FINDING_LEVEL_LABELED, index=False)
    seq_labeled.to_parquet(OUT_SEQ_LABELED, index=False)

    # -------------------------
    # Coverage summaries (safe)
    # -------------------------
    if "phase_meaning_primary" in seq_labeled.columns:
        print(f"Phase label coverage (primary): {pct(seq_labeled['phase_meaning_primary']):.1f}%")
    if "occurrence_meaning" in seq_labeled.columns:
        print(f"Occurrence label coverage (decoder): {pct(seq_labeled['occurrence_meaning']):.1f}%")
    if "phase_meaning" in seq_labeled.columns:
        print(f"Phase label coverage (final): {pct(seq_labeled['phase_meaning']):.1f}%")

    # -------------------------
    # Audits (defensive: only request columns that exist)
    # -------------------------
    quick_audit(
        "event_level",
        event_level,
        key_cols=existing(["ev_id", "ev_date", "ev_highest_injury", "far_part"], event_level),
    )
    quick_audit(
        "finding_level",
        finding_lvl,
        key_cols=existing(["ev_id", "Aircraft_Key", "finding_description", "Cause_Factor"], finding_lvl),
    )
    quick_audit(
        "sequence_labeled",
        seq_labeled,
        key_cols=existing(["ev_id", "Occurrence_Code", "phase_no", "Defining_ev"], seq_labeled),
    )

    # -------------------------
    # Quick exploratory tables (defensive)
    # -------------------------

    # Phase x Occurrence meaning (limit size for console)
    if {"phase_meaning", "occurrence_meaning"}.issubset(seq_labeled.columns):
        ct2 = pd.crosstab(seq_labeled["phase_meaning"], seq_labeled["occurrence_meaning"])
        # Sort rows/cols by totals for a more informative preview
        ct2 = ct2.loc[
            ct2.sum(axis=1).sort_values(ascending=False).index,
            ct2.sum(axis=0).sort_values(ascending=False).index,
        ]
        print("\nPhase x Occurrence (top 10 x 10 by totals):")
        print(ct2.iloc[:10, :10])

    # Top finding categories by injury
    if {"finding_category", "ev_highest_injury"}.issubset(finding_lab.columns):
        tmp = finding_lab.copy()
        # Normalize injury labels to avoid drift like 'FATL ' vs 'FATL'
        tmp["ev_highest_injury_norm"] = tmp["ev_highest_injury"].astype("string").str.strip().str.upper()

        ct = pd.crosstab(tmp["finding_category"], tmp["ev_highest_injury_norm"])

        # Add TOTAL and choose a sensible sort column
        ct["TOTAL"] = ct.sum(axis=1)
        sort_col = "FATL" if "FATL" in ct.columns else "TOTAL"
        ct_sorted = ct.sort_values(by=sort_col, ascending=False)

        # Build the display column order: injury cols (FATL first if present) + TOTAL
        injury_cols = [c for c in ct.columns if c != "TOTAL"]
        if "FATL" in injury_cols:
            injury_cols = ["FATL"] + [c for c in injury_cols if c != "FATL"]

        print("\nTop finding categories by injury counts (head):")
        # Use .loc with a LIST of columns, not a tuple
        cols_to_show = [*injury_cols, "TOTAL"]
        print(ct_sorted.loc[:, cols_to_show].head(20))

    # Cause/Factor by finding_category
    if {"Cause_Factor", "finding_category"}.issubset(finding_lab.columns):
        cf_map = {"C": "Cause", "F": "Factor", "B": "Both", "U": "Unknown"}
        tmp = finding_lab.copy()
        tmp["Cause_Factor_lbl"] = tmp["Cause_Factor"].map(cf_map).fillna(tmp["Cause_Factor"])

        ct3 = pd.crosstab(tmp["finding_category"], tmp["Cause_Factor_lbl"])
        # Order columns consistently and sort rows by TOTAL
        ct3 = ct3.reindex(columns=[c for c in ["Cause", "Factor", "Both", "Unknown"] if c in ct3.columns])
        ct3["TOTAL"] = ct3.sum(axis=1)
        ct3 = ct3.sort_values(by="TOTAL", ascending=False)

        print("\nCause/Factor by finding_category (head):")
        print(ct3.head(20))

        # A. Select SCF-NP events (optionally only defining events)
        scfnp_mask = seq_labeled["occurrence_meaning"].str.contains(
            "SYS/COMP MALF/FAIL (NON-POWER)", case=False, na=False, regex=False
        )
        defining_mask = seq_labeled.get("Defining_ev").astype("Int64").eq(1)  # 1/TRUE means defining

        # choose one:
        scfnp_core = seq_labeled[scfnp_mask & defining_mask]  # primary driver only
        # scfnp_any  = seq_labeled[scfnp_mask]                 # any occurrence in sequence

        scfnp_ev_ids = scfnp_core["ev_id"].dropna().unique()
        print(f"- defining events: {len(scfnp_ev_ids):,}")

    # B1. Label procedure-related findings (finding-level)
    PROC_KEYWORDS = [
        "CHECKLIST",
        "PROCEDURE",
        "SOP",
        "STANDARD OPERATING PROCEDURE",
        "BRIEFING",
        "BRIEF",
        "CALLOUT",
        "CALL OUT",
        "INSPECTION",
        "INSPECT",
        "MAINTENANCE PROCEDURE",
        "CONFIGURATION",
        "CONFIGURE",
        "VERIFY",
        "VERIFICATION",
        "CROSSCHECK",
        "CROSS-CHECK",
        "CROSS CHECK",
        "USE OF EQUIP/INFO",  # eADMS phrasing
        "TASK PERFORMANCE-USE OF EQUIP",  # category string fragment
    ]

    def is_procedural(text: pd.Series) -> pd.Series:
        s = text.fillna("").str.upper()
        mask = pd.Series(False, index=s.index)
        for kw in PROC_KEYWORDS:
            mask = mask | s.str.contains(kw, na=False)
        return mask

    finding_lab["ProcedureFinding"] = is_procedural(finding_lab["finding_description"])

    # Optionally restrict to CAUSE ('C') or BOTH ('B') if you want “mitigation failure” not just contributing factors:
    is_cause_like = finding_lab["Cause_Factor"].isin(["C", "B"])
    finding_lab["ProcedureFinding_CauseOrBoth"] = finding_lab["ProcedureFinding"] & is_cause_like

    # B2. Roll-up to event level
    proc_event = finding_lab.groupby("ev_id", as_index=False).agg(
        proc_any=("ProcedureFinding", "any"),
        proc_cause_or_both=("ProcedureFinding_CauseOrBoth", "any"),
    )

    # Join to event_level for outcomes
    event_enriched = event_level.merge(proc_event, on="ev_id", how="left")
    event_enriched[["proc_any", "proc_cause_or_both"]] = event_enriched[["proc_any", "proc_cause_or_both"]].fillna(
        False
    )

    # Mark - events
    event_enriched["is_scfnp"] = event_enriched["ev_id"].isin(scfnp_ev_ids)

    # Outcome: fatal vs non-fatal (binary)
    event_enriched["fatal"] = event_enriched["ev_highest_injury"].astype(str).str.upper().str.strip().eq("FATL")

    print(event_enriched[["is_scfnp", "proc_any", "proc_cause_or_both", "fatal"]].head())
    print(event_enriched["is_scfnp"].value_counts())
    print(finding_lab["ProcedureFinding"].value_counts())
    print(finding_lab.loc[finding_lab["ProcedureFinding"], "finding_description"].sample(20))
    overlap = event_enriched[event_enriched["is_scfnp"] & event_enriched["proc_any"]]
    print(f"- events with ANY procedural finding: {len(overlap)}")
    print(f"…of which fatal: {overlap['fatal'].sum()} ({overlap['fatal'].mean() * 100:.1f}% fatal)")
    print(events["ev_id"].dtype, findings["ev_id"].dtype, aircraft["ev_id"].dtype)

    import numpy as np
    import statsmodels.formula.api as smf
    from scipy.stats import fisher_exact

    # ------------------------------
    # C1.  - x Procedural (Cause/Both)
    # ------------------------------
    tab1 = pd.crosstab(event_enriched["is_scfnp"], event_enriched["proc_cause_or_both"])
    print("\nC1. - x Procedural (Cause/Both):\n", tab1)

    odds1, p1 = fisher_exact(tab1.values)
    print(f"Fisher exact: OR={odds1:0.2f}, p={p1:0.4f}")

    # ------------------------------
    # C2.  Within -: Procedural x Fatal
    # ------------------------------
    sub = event_enriched[event_enriched["is_scfnp"]].copy()
    tab2 = pd.crosstab(sub["proc_cause_or_both"], sub["fatal"])
    print("\nC2. Within -: Procedural(C/B) x Fatal:\n", tab2)

    odds2, p2 = fisher_exact(tab2.values)
    print(f"Fisher exact (- only): OR={odds2:0.2f}, p={p2:0.4f}")

    # ------------------------------
    # C3.  Logistic Regression
    # ------------------------------
    df = event_enriched.copy()
    df["fatal"] = df["fatal"].astype(int)
    df["is_scfnp"] = df["is_scfnp"].astype(int)
    df["proc_cb"] = df["proc_cause_or_both"].astype(int)

    model = smf.logit("fatal ~ is_scfnp + proc_cb + is_scfnp:proc_cb", data=df).fit(disp=False)
    print(model.summary())
    print("\nExponentiated coefficients (odds ratios):")
    print(np.exp(model.params))


if __name__ == "__main__":
    main()
