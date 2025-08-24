import pandas as pd

from audit import quick_audit
from config import (
    OUT_EVENT_LEVEL,
    OUT_FINDING_LEVEL,
    OUT_FINDING_LEVEL_LABELED,
    OUT_SEQ_LABELED,
)
from loaders import read_aircraft, read_events, read_events_sequence, read_findings
from lookups import build_finding_lookup, build_occurrence_lookup, build_phase_lookup


def main():
    # ---- Load core tables
    events = read_events()
    findings = read_findings()
    aircraft = read_aircraft()
    seq = read_events_sequence()

    # ---- Event-level (first aircraft per event)
    aircraft_per_event = aircraft.sort_values(["ev_id", "Aircraft_Key"]).drop_duplicates(subset=["ev_id"], keep="first")
    event_level = events.merge(aircraft_per_event, on="ev_id", how="left")

    # ---- Finding-level (1:N to events)
    finding_level = findings.merge(events, on="ev_id", how="inner").merge(aircraft_per_event, on="ev_id", how="left")

    # ---- Build & join lookups
    finding_lk = build_finding_lookup()
    finding_level_labeled = finding_level.merge(finding_lk, on="finding_code", how="left")

    occ_lk = build_occurrence_lookup()
    phase_lk = build_phase_lookup()

    seq_labeled = seq.merge(occ_lk, on="Occurrence_No", how="left").merge(phase_lk, on="phase_no", how="left")

    # ---- Save outputs
    event_level.to_parquet(OUT_EVENT_LEVEL, index=False)
    finding_level.to_parquet(OUT_FINDING_LEVEL, index=False)
    finding_level_labeled.to_parquet(OUT_FINDING_LEVEL_LABELED, index=False)
    seq_labeled.to_parquet(OUT_SEQ_LABELED, index=False)

    # ---- Audits (quick signals)
    quick_audit(event_level, "Event-level (one row per ev_id)")
    quick_audit(finding_level, "Finding-level (raw)")
    # Coverage of labels:
    if "finding_meaning" in finding_level_labeled.columns:
        cov = finding_level_labeled["finding_meaning"].notna().mean() * 100
        print(f"\nFinding code label coverage: {cov:.1f}%")
    if {"occurrence_meaning", "phase_meaning"}.issubset(seq_labeled.columns):
        cov_occ = seq_labeled["occurrence_meaning"].notna().mean() * 100
        cov_ph = seq_labeled["phase_meaning"].notna().mean() * 100
        print(f"Occurrence label coverage: {cov_occ:.1f}% | Phase label coverage: {cov_ph:.1f}%")

    # ---- Example: first actionable crosstab when labels exist
    if {"finding_meaning", "ev_highest_injury"}.issubset(finding_level_labeled.columns):
        ct = pd.crosstab(
            finding_level_labeled["finding_meaning"],
            finding_level_labeled["ev_highest_injury"],
        )
        print(
            "\nTop systems by FATL counts:\n",
            ct.sort_values("FATL", ascending=False).head(15),
        )


if __name__ == "__main__":
    main()
