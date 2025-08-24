# analysis/logit_models.py
from collections.abc import Sequence

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .system_risk import FilterSpec, _is_fatal, _normalize_system, filter_event_level


def fit_logit(
    event_df: pd.DataFrame,
    spec: FilterSpec | None = None,
    system_col: str = "system_component",
    injury_col: str = "ev_highest_injury",
    controls: Sequence[str] | None = None,
) -> smf.discrete.discrete_model.BinaryResultsWrapper:
    if spec is None:
        spec = FilterSpec()
    controls = list(controls or [])
    d = filter_event_level(event_df, spec)
    need = {system_col, injury_col}.union(controls)
    missing = [c for c in need if c not in d.columns]
    if missing:
        raise KeyError(f"Missing columns for logit: {missing}")

    d["fatal"] = _is_fatal(d[injury_col]).astype(int)
    d["system_bucket"] = _normalize_system(d[system_col])

    # Binary indicator for Flight Control; you can extend to multi-category models later
    d["fc"] = (d["system_bucket"] == "Flight Control").astype(int)

    # Simple, defensible model: fatal ~ fc + year + FAR part
    # (Drop super-sparse categories to avoid perfect separation.)
    d = d.dropna(subset=["fatal", "fc"])
    d["ev_year"] = pd.to_numeric(d["ev_year"], errors="coerce")

    # Minimal controls; expand as data supports
    f = "fatal ~ fc + C(far_part) + ev_year"
    model = smf.logit(formula=f, data=d).fit(disp=False)
    # Return tidy summary + odds ratios
    or_df = pd.DataFrame(
        {
            "term": model.params.index,
            "coef": model.params.values,
            "OR": np.exp(model.params.values),
            "p": model.pvalues.values,
        }
    )
    return model, or_df.sort_values("term")
