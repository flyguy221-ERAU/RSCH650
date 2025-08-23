# cli/analyze_systems.py
import argparse
import pandas as pd
import json
from analysis.system_risk import build_contingency, chisq_table, FilterSpec
from analysis.logit_models import fit_logit


def main():
    ap = argparse.ArgumentParser(description="System risk analysis (CAROL/eADMS)")
    ap.add_argument("--events", required=True, help="Path to event-level Parquet/CSV")
    ap.add_argument("--out", required=True, help="Directory for outputs")
    ap.add_argument("--parts", nargs="*", default=["91", "121", "135"], help="FAR parts to include")
    ap.add_argument("--start", type=int, default=2009)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--format", choices=["parquet", "csv"], default="csv")
    args = ap.parse_args()

    # Load events
    ev = (
        pd.read_parquet(args.events)
        if args.events.endswith(".parquet")
        else pd.read_csv(args.events)
    )

    spec = FilterSpec(
        years=(args.start, args.end),
        include_far_parts=set(args.parts),
        exclude_rotorcraft=True,
    )

    ct = build_contingency(ev, spec=spec)
    xt = chisq_table(ev, spec=spec)

    # Optional: stats test
    try:
        import scipy.stats as st

        chi2, p, dof, expected = st.chi2_contingency(xt.values)
        stats = {
            "chi2": float(chi2),
            "p": float(p),
            "dof": int(dof),
            "expected": expected.tolist(),
        }
    except Exception as e:
        stats = {"error": str(e)}

    # Logistic regression (optional if statsmodels installed)
    try:
        model, or_df = fit_logit(ev, spec=spec)
        or_out = or_df
        summ = model.summary().as_text()
    except Exception as e:
        or_out = pd.DataFrame({"term": [], "coef": [], "OR": [], "p": []})
        summ = f"Logit not run: {e}"

    # Save
    out = args.out.rstrip("/")
    if args.format == "csv":
        ct.to_csv(f"{out}/system_contingency.csv", index=False)
        xt.to_csv(f"{out}/fc_vs_other_2x2.csv")
        or_out.to_csv(f"{out}/logit_or.csv", index=False)
        with open(f"{out}/chisq.json", "w") as f:
            json.dump(stats, f, indent=2)
        with open(f"{out}/logit_summary.txt", "w") as f:
            f.write(summ)
    else:
        ct.to_parquet(f"{out}/system_contingency.parquet", index=False)
        xt.to_parquet(f"{out}/fc_vs_other_2x2.parquet")
        or_out.to_parquet(f"{out}/logit_or.parquet", index=False)
        with open(f"{out}/chisq.json", "w") as f:
            json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
