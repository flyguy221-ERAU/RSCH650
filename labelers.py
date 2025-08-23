import pandas as pd
from normalize import split_finding_description
from decoder import decode_occurrence_code, build_phase_numeric_lookup


def build_event_level(events: pd.DataFrame, aircraft: pd.DataFrame) -> pd.DataFrame:
    aircraft_per_event = aircraft.sort_values(["ev_id", "Aircraft_Key"]).drop_duplicates(
        subset=["ev_id"], keep="first"
    )
    return events.merge(aircraft_per_event, on="ev_id", how="left")


def build_finding_level(
    events: pd.DataFrame, findings: pd.DataFrame, aircraft: pd.DataFrame
) -> pd.DataFrame:
    aircraft_per_event = aircraft.sort_values(["ev_id", "Aircraft_Key"]).drop_duplicates(
        subset=["ev_id"], keep="first"
    )
    return findings.merge(events, on="ev_id", how="inner").merge(
        aircraft_per_event, on="ev_id", how="left"
    )


def label_findings(finding_level: pd.DataFrame) -> pd.DataFrame:
    fd_parts = split_finding_description(finding_level["finding_description"])
    df = pd.concat([finding_level, fd_parts], axis=1)
    df["finding_category"] = df["cat_text"].str.split(" - ", n=1, expand=True).iloc[:, 0].fillna("")
    return df


def label_sequence(seq: pd.DataFrame) -> pd.DataFrame:
    out = seq.copy()

    # Occurrence_Code decoding: exact > right3; plus left3-derived phase family
    if "Occurrence_Code" in out.columns:
        occ_exact, occ_right, phase_left = decode_occurrence_code(out["Occurrence_Code"])
        out["occurrence_meaning"] = occ_exact.fillna(occ_right)
        out["phase_meaning_fallback"] = phase_left

    # Numeric phase (primary) from phase_no
    if "phase_no" in out.columns:
        ph_lk = build_phase_numeric_lookup()
        if not ph_lk.empty:
            out = out.merge(
                ph_lk.rename(columns={"code_int": "phase_no", "meaning": "phase_meaning_primary"}),
                on="phase_no",
                how="left",
            )

    # Final phase: primary else fallback
    out["phase_meaning"] = out.get("phase_meaning_primary")
    if "phase_meaning_fallback" in out.columns:
        out["phase_meaning"] = out["phase_meaning"].fillna(out["phase_meaning_fallback"])

    return out
