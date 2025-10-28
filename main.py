# main.py
from __future__ import annotations

from pathlib import Path

import pandas as pd

from audit import quick_audit
from config import (
    CT_SEQEVT_CSV,
    DICT_CSV,
    # outputs
    OUT_EVENT_LEVEL,
    OUT_FINDING_LEVEL,
    OUT_FINDING_LEVEL_LABELED,
    OUT_SEQ_LABELED,
    # lookup/taxonomy paths
    PHASE_MAP_CSV,
)
from labelers import build_event_level, build_finding_level, label_findings, label_sequence
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
    events = read_events()  # expects ev_id, ev_year, ev_date, ev_highest_injury, ...
    findings = read_findings()  # expects finding_description, codes, Cause_Factor, ...
    aircraft = read_aircraft()  # expects ev_id, Aircraft_Key, acft_make, acft_model
    seq = read_events_sequence()  # expects ev_id, Aircraft_Key, Occurrence_No, phase_no, Occurrence_Code, Defining_ev

    # -------------------------
    # Build base tables
    # -------------------------
    event_level = build_event_level(events, aircraft)
    finding_lvl = build_finding_level(events, findings, aircraft)

    # -------------------------
    # Label sequence & findings
    # (pass lookup paths explicitly)
    # -------------------------
    phase_map_path = PHASE_MAP_CSV if Path(PHASE_MAP_CSV).exists() else DICT_CSV
    seq_labeled = label_sequence(seq, phase_map_path=phase_map_path, ct_seqevt_path=CT_SEQEVT_CSV)
    finding_lab = label_findings(finding_lvl)

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
            ct2.sum(axis=1).sort_values(ascending=False).index, ct2.sum(axis=0).sort_values(ascending=False).index
        ]
        print("\nPhase x Occurrence (top 10x10 by totals):")
        print(ct2.iloc[:10, :10])

    # Top finding categories by injury
    if {"finding_category", "ev_highest_injury"}.issubset(finding_lab.columns):
        ct = pd.crosstab(finding_lab["finding_category"], finding_lab["ev_highest_injury"])

        # Add TOTAL and choose a sensible sort column
        ct["TOTAL"] = ct.sum(axis=1)
        sort_col = "FATL" if "FATL" in ct.columns else "TOTAL"
        ct_sorted = ct.sort_values(by=sort_col, ascending=False)

        print("\nTop finding categories by injury counts (head):")
        # Show the injury columns first (if FATL exists, bring it forward), then TOTAL
        injury_cols = [c for c in ct.columns if c not in {"TOTAL"}]
        if "FATL" in injury_cols:
            injury_cols = ["FATL"] + [c for c in injury_cols if c != "FATL"]
        print(ct_sorted[*injury_cols, "TOTAL"].head(20))

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


if __name__ == "__main__":
    main()
