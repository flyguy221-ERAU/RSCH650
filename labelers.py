import pandas as pd

from decoder import build_occ_phase_maps
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
    dict_csv_path,  # Path or str to eADMSPUB_DataDictionary.csv
) -> pd.DataFrame:
    """
    Enrich seq with:
      - occurrence_meaning: exact 6-digit map else right-3 map (from eADMS dict)
      - phase_meaning_primary: via phase_no using left-3 phase map (PPPxxx)
      - phase_meaning_fallback: via Occurrence_Code left-3 (PPP) if primary missing
      - phase_meaning: primary else fallback
    """
    out = seq.copy()
    exact_map, right3_map, left3_phase_map = build_occ_phase_maps(dict_csv_path)

    # --- Occurrence meaning (exact first, else right3)
    if "Occurrence_Code" in out.columns:
        occ = out["Occurrence_Code"].astype("string").str.zfill(6)

        occ_meaning = occ.map(exact_map)  # exact 6-digit if available
        occ_meaning = occ_meaning.fillna(occ.str[-3:].map(right3_map))  # fallback to right-3

        out["occurrence_meaning"] = occ_meaning

        # phase fallback from left3 family (PPP)
        out["phase_meaning_fallback"] = occ.str[:3].map(left3_phase_map)

    # --- Phase primary via numeric phase_no (PPP)
    if "phase_no" in out.columns and not left3_phase_map.empty:
        phase_key = out["phase_no"].astype("Int64").astype("string").str.zfill(3)
        out["phase_meaning_primary"] = phase_key.map(left3_phase_map)

    # --- Final phase meaning
    out["phase_meaning"] = out.get("phase_meaning_primary")
    if "phase_meaning_fallback" in out.columns:
        out["phase_meaning"] = out["phase_meaning"].fillna(out["phase_meaning_fallback"])

    return out
