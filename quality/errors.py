# quality/errors.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UXError:
    code: str
    title: str
    hint: str


# Reusable messages
MISSING_DATA = UXError(
    code="E-DATA-001",
    title="Required data not found",
    hint="Place raw CSVs in data/raw and run `make build`, or verify Parquet files in data/out.",
)

BAD_CSV = UXError(
    code="E-CSV-001",
    title="Could not parse one or more CSV files",
    hint="Open the file to check header/encoding; re-download from CAROL if corrupted.",
)

PIPELINE_FAIL = UXError(
    code="E-PIPE-001",
    title="Pipeline step failed",
    hint="Re-run `make build` and review console output; see README > Troubleshooting.",
)
