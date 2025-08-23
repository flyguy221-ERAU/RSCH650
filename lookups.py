import pandas as pd
from config import CT_SEQEVT_CSV, DICT_CSV


def _extract_last_int(s: pd.Series) -> pd.Series:
    s = s.astype("string")
    out = s.str.extract(r"(\d+)$")[0]
    out = out.fillna(s.str.extract(r"(\d+)")[0])
    return pd.to_numeric(out, errors="coerce").astype("Int64")


def _pick_cols(df: pd.DataFrame):
    lower = {c.lower(): c for c in df.columns}
    # likely code & meaning columns
    code_col = next(
        (
            lower[k]
            for k in [
                "code",
                "occurrence_code",
                "occurrence_no",
                "phase_no",
                "phase_code",
                "ct_code",
                "code_iaids",
            ]
            if k in lower
        ),
        None,
    )
    meaning_col = next(
        (
            lower[k]
            for k in [
                "meaning",
                "desc",
                "description",
                "occurrence",
                "phase",
                "phase_meaning",
            ]
            if k in lower
        ),
        None,
    )
    # fallbacks
    if code_col is None:
        for c in df.columns:
            if df[c].astype(str).str.contains(r"\d").mean() > 0.5:
                code_col = c
                break
    if meaning_col is None:
        for c in df.columns:
            if c != code_col and df[c].astype(str).str.contains(r"[A-Za-z]").mean() > 0.5:
                meaning_col = c
                break
    return code_col, meaning_col


def build_phase_and_event_lookups_from_seq(
    seq: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (phase_lk, event_lk) mapping the *actual* values present in seq to meanings in ct_seqevt."""
    codes = pd.read_csv(CT_SEQEVT_CSV, dtype="string", low_memory=False)
    code_col, meaning_col = _pick_cols(codes)
    if code_col is None or meaning_col is None:
        return pd.DataFrame(columns=["phase_no", "phase_meaning"]), pd.DataFrame(
            columns=["eventsoe_no", "event_meaning"]
        )

    codes = codes[[code_col, meaning_col]].dropna().copy()
    codes["code_int"] = _extract_last_int(codes[code_col])

    # Build phase lookup for values we actually have
    phase_lk = pd.DataFrame(columns=["phase_no", "phase_meaning"])
    if "phase_no" in seq.columns and seq["phase_no"].notna().any():
        present = seq["phase_no"].dropna().astype("Int64").unique()
        m = codes[codes["code_int"].isin(present)].copy()
        phase_lk = m.rename(columns={"code_int": "phase_no", meaning_col: "phase_meaning"})[
            ["phase_no", "phase_meaning"]
        ].drop_duplicates()

    # Build event lookup for eventsoe_no values we have
    event_lk = pd.DataFrame(columns=["eventsoe_no", "event_meaning"])
    if "eventsoe_no" in seq.columns and seq["eventsoe_no"].notna().any():
        present = seq["eventsoe_no"].dropna().astype("Int64").unique()
        m = codes[codes["code_int"].isin(present)].copy()
        event_lk = m.rename(columns={"code_int": "eventsoe_no", meaning_col: "event_meaning"})[
            ["eventsoe_no", "event_meaning"]
        ].drop_duplicates()

    return phase_lk, event_lk


def build_modifier_lookup() -> pd.DataFrame:
    """
    From eADMSPUB_DataDictionary:
      Table == 'Findings' AND Column == 'modifier_no'
    'xxxxxxxx06' → modifier_no = 6 → 'Fatigue/wear/corrosion'
    """
    dd = pd.read_csv(DICT_CSV, dtype="string", low_memory=False)
    needed = {"Table", "Column", "code_iaids", "meaning"}
    if not needed.issubset(dd.columns):
        return pd.DataFrame(columns=["modifier_no", "modifier_meaning"])
    m = dd[
        (dd["Table"].str.strip().str.lower() == "findings")
        & (dd["Column"].str.strip().str.lower() == "modifier_no")
    ][["code_iaids", "meaning"]].dropna()
    if m.empty:
        return pd.DataFrame(columns=["modifier_no", "modifier_meaning"])
    m = m.rename(columns={"code_iaids": "modifier_mask", "meaning": "modifier_meaning"})
    m["modifier_no"] = m["modifier_mask"].str.extract(r"(\d{2})$").astype("Int64")
    m = m.drop_duplicates(subset=["modifier_no"]).dropna(subset=["modifier_no"])
    return m[["modifier_no", "modifier_meaning"]]
