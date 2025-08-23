import pandas as pd
from config import (
    OUT_EVENT_LEVEL, OUT_FINDING_LEVEL, OUT_FINDING_LEVEL_LABELED, OUT_SEQ_LABELED
)
from loaders import read_events, read_findings, read_aircraft, read_events_sequence
from labelers import build_event_level, build_finding_level, label_findings, label_sequence
from audit import quick_audit

def pct(s): 
    return 0.0 if s is None else float(pd.notna(s).mean()*100)

def main():
    # Load
    events   = read_events()
    findings = read_findings()
    aircraft = read_aircraft()
    seq      = read_events_sequence()

    # Build base tables
    event_level = build_event_level(events, aircraft)
    finding_lvl = build_finding_level(events, findings, aircraft)

    # Label sequence & findings
    seq_labeled = label_sequence(seq)
    finding_lab = label_findings(finding_lvl)

    # Save
    event_level.to_parquet(OUT_EVENT_LEVEL, index=False)
    finding_lvl.to_parquet(OUT_FINDING_LEVEL, index=False)
    finding_lab.to_parquet(OUT_FINDING_LEVEL_LABELED, index=False)
    seq_labeled.to_parquet(OUT_SEQ_LABELED, index=False)

    # Coverage
    if "phase_meaning_primary" in seq_labeled:
        print(f"Phase label coverage: {pct(seq_labeled['phase_meaning_primary']):.1f}%")
    if "occurrence_meaning" in seq_labeled:
        print(f"Occurrence label coverage (decoder): {pct(seq_labeled['occurrence_meaning']):.1f}%")
    if "phase_meaning" in seq_labeled:
        print(f"Phase label coverage (final): {pct(seq_labeled['phase_meaning']):.1f}%")

    # Audits
    quick_audit(event_level, "Event-level (per ev_id)")
    quick_audit(finding_lab, "Finding-level (labeled)")

    # Example cross-tabs
    if {"phase_meaning","occurrence_meaning"}.issubset(seq_labeled.columns):
        ct2 = pd.crosstab(seq_labeled["phase_meaning"], seq_labeled["occurrence_meaning"])
        print("\nPhase × Occurrence (first 10×10):")
        print(ct2.iloc[:10,:10])
    if {"finding_category","ev_highest_injury"}.issubset(finding_lab.columns):
        ct = pd.crosstab(finding_lab["finding_category"], finding_lab["ev_highest_injury"]).sort_values("FATL", ascending=False)
        print("\nTop finding categories by FATL counts:\n", ct.head(20))
    if {"Cause_Factor","finding_category"}.issubset(finding_lab.columns):
        cf_map = {"C":"Cause","F":"Factor","B":"Both","U":"Unknown"}
        tmp = finding_lab.copy()
        tmp["Cause_Factor_lbl"] = tmp["Cause_Factor"].map(cf_map).fillna(tmp["Cause_Factor"])
        ct3 = pd.crosstab(tmp["finding_category"], tmp["Cause_Factor_lbl"])
        print("\nCause/Factor by finding_category (first 20):\n", ct3.head(20))

if __name__ == "__main__":
    main()