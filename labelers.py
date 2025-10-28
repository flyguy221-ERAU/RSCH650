import pandas as pd

from decoder import build_phase_numeric_lookup, decode_occurrence_code
from normalize import split_finding_description

# -------------------------
# Event/Finding builders
# -------------------------


def build_event_level(events: pd.DataFrame, aircraft: pd.DataFrame) -> pd.DataFrame:
    aircraft_per_event = aircraft.sort_values(["ev_id", "Aircraft_Key"]).drop_duplicates(subset=["ev_id"], keep="first")
    return events.merge(aircraft_per_event, on="ev_id", how="left")


def build_finding_level(events: pd.DataFrame, findings: pd.DataFrame, aircraft: pd.DataFrame) -> pd.DataFrame:
    aircraft_per_event = aircraft.sort_values(["ev_id", "Aircraft_Key"]).drop_duplicates(subset=["ev_id"], keep="first")
    return findings.merge(events, on="ev_id", how="inner").merge(aircraft_per_event, on="ev_id", how="left")


def label_findings(finding_level: pd.DataFrame) -> pd.DataFrame:
    """
    Adds parsed finding parts:
      - cat_text, subcat_text, section_text, modifier_text (from finding_description)
      - finding_category: first token before " - "
    """
    fd_parts = split_finding_description(finding_level["finding_description"])
    df = pd.concat([finding_level, fd_parts], axis=1)
    df["finding_category"] = df["cat_text"].astype("string").str.split(" - ", n=1, expand=True).iloc[:, 0].fillna("")
    return df


# -------------------------
# Sequence labeling
# -------------------------


def label_sequence(
    seq: pd.DataFrame,
    phase_map_path,  # Path or str to phase map CSV (or your eADMS dict as fallback)
    ct_seqevt_path,  # Path or str to CAST/ICAO seq events map (occ_code -> occ_desc)
) -> pd.DataFrame:
    """
    Enriches the events_sequence table with:
      - occurrence_meaning (via exact code or right3 fallback)
      - phase_meaning_primary (via numeric phase map)
      - phase_meaning_fallback (via left3 "family" derived from occ_desc)
      - phase_meaning (primary else fallback)
    """
    out = seq.copy()

    # ---- Build lookups from the provided paths
    phase_lu = build_phase_numeric_lookup(phase_map_path)  # cols: phase_code, phase_desc
    se_lu = decode_occurrence_code(ct_seqevt_path)  # cols: occ_code,  occ_desc

    # Index them for fast mapping
    occ_exact_map = dict(zip(se_lu["occ_code"], se_lu["occ_desc"], strict=False))

    # Build "right3" map (last 3 chars) and "left3 family" map
    # Example: "SCF-NP" -> right3 "NP";    left3 "SCF"
    se_lu_right3 = se_lu.copy()
    se_lu_right3["right3"] = se_lu_right3["occ_code"].astype("string").str[-3:]
    right3_map = dict(zip(se_lu_right3["right3"], se_lu_right3["occ_desc"], strict=False))

    # Family = first token of occ_desc before ":" if present
    # e.g., "System/Component Failure: Non-Powerplant" -> "System/Component Failure"
    se_lu_left3 = se_lu.copy()
    se_lu_left3["left3"] = se_lu_left3["occ_code"].astype("string").str[:3]
    se_lu_left3["family"] = (
        se_lu_left3["occ_desc"].astype("string").str.split(":", n=1, expand=True).iloc[:, 0].str.strip()
    )
    # pick the first family for each left3
    left3_map = dict(
        zip(se_lu_left3.drop_duplicates("left3")["left3"], se_lu_left3.drop_duplicates("left3")["family"], strict=False)
    )

    # ---- Occurrence_Code → meanings
    if "Occurrence_Code" in out.columns:
        occ_series = out["Occurrence_Code"].astype("string")

        # exact match
        occ_exact = occ_series.map(occ_exact_map)

        # right3 fallback (if exact not found)
        right3_keys = occ_series.str[-3:]
        occ_right3 = right3_keys.map(right3_map)

        # left3-derived "family" (used later as a phase fallback if needed)
        left3_keys = occ_series.str[:3]
        phase_left_family = left3_keys.map(left3_map)

        out["occurrence_meaning"] = occ_exact.fillna(occ_right3)
        out["phase_meaning_fallback"] = phase_left_family

    # ---- Numeric phase → primary phase meaning
    # Expect phase_lu has columns: phase_code (int), phase_desc (str)
    if "phase_no" in out.columns and not phase_lu.empty:
        # normalize types for the merge
        tmp = phase_lu.rename(columns={"phase_code": "phase_no", "phase_desc": "phase_meaning_primary"}).copy()
        tmp["phase_no"] = tmp["phase_no"].astype("Int64")
        out["phase_no"] = out["phase_no"].astype("Int64")
        out = out.merge(tmp, on="phase_no", how="left")

    # ---- Final phase meaning: primary else fallback
    out["phase_meaning"] = out.get("phase_meaning_primary")
    if "phase_meaning_fallback" in out.columns:
        out["phase_meaning"] = out["phase_meaning"].fillna(out["phase_meaning_fallback"])

    return out
