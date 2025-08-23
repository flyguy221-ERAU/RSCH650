import pandas as pd
from analysis.system_risk import build_contingency, chisq_table, FilterSpec

def _toy():
    # 4 events: 2 FC (1 fatal), 2 Other (0 fatal)
    return pd.DataFrame({
        "ev_year":[2015, 2016, 2017, 2018],
        "far_part":["91","91","121","135"],
        "acft_category":["Airplane","Airplane","Airplane","Airplane"],
        "system_component":["Flight Control","Flight Control","Engine","Avionics"],
        "ev_highest_injury":["FATL","NONE","NONE","MINR"]
    })

def test_contingency_basic():
    df = _toy()
    spec = FilterSpec(years=(2009,2025), include_far_parts={"91","121","135"}, exclude_rotorcraft=True)
    ct = build_contingency(df, spec=spec)
    assert "Flight Control" in set(ct["system_bucket"])
    fc = ct[ct["system_bucket"]=="Flight Control"].iloc[0]
    assert fc["total"] == 2
    assert fc["fatals"] == 1
    assert abs(fc["pct_fatal"] - 50.0) < 1e-6

def test_chisq_shape():
    df = _toy()
    xt = chisq_table(df, spec=FilterSpec())
    assert list(xt.columns) == ["Fatal","Nonfatal"]
    assert xt.shape == (2,2)
    assert xt.loc["Flight Control","Fatal"] == 1