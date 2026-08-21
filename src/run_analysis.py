"""Run the full A/B analysis and persist results (consumed by report + README)."""

import json
from pathlib import Path

import pandas as pd

from src.stats_utils import (
    chi_square_independence,
    required_sample_size,
    retrospective_power,
    srm_check,
    two_proportion_ztest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "marketing_AB.csv"
OUT = PROJECT_ROOT / "report" / "results.json"

# The dataset ships without an experiment spec; the observed ~96/4 split is
# the standard ad-industry holdout design (PSA shown to a small control).
ASSUMED_RATIO = 0.96


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW, index_col=0)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    return df


def main() -> None:
    df = load()
    res = {"n_rows": int(len(df)), "n_users": int(df["user_id"].nunique())}

    # ---- sanity checks ----
    res["duplicate_users"] = int(len(df) - df["user_id"].nunique())
    both = df.groupby("user_id")["test_group"].nunique()
    res["users_in_both_groups"] = int((both > 1).sum())

    ad = df[df["test_group"] == "ad"]
    psa = df[df["test_group"] == "psa"]
    res["srm"] = srm_check(len(ad), len(psa), expected_ratio=ASSUMED_RATIO)

    # ---- primary test ----
    conv_ad, n_ad = int(ad["converted"].sum()), len(ad)
    conv_psa, n_psa = int(psa["converted"].sum()), len(psa)
    z = two_proportion_ztest(conv_ad, n_ad, conv_psa, n_psa)
    chi = chi_square_independence(conv_ad, n_ad, conv_psa, n_psa)
    res["primary"] = {
        "n_ad": n_ad, "n_psa": n_psa,
        "conv_ad": conv_ad, "conv_psa": conv_psa,
        **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in z.items()},
        "chi2": round(chi["chi2"], 2), "chi2_p": chi["p_value"],
    }
    res["power"] = {k: round(v, 4) for k, v in retrospective_power(
        z["rate_b"], z["rate_a"], n_psa, n_ad).items()}
    res["sample_size_10pct_mde"] = required_sample_size(z["rate_b"], 0.10)

    # ---- segmentation: exposure terciles + day of most ads ----
    df["exposure"] = pd.cut(df["total_ads"], bins=[0, 10, 50, df["total_ads"].max()],
                            labels=["Low (1-10)", "Medium (11-50)", "High (50+)"],
                            include_lowest=True)
    seg_rows = []
    for seg, grp in df.groupby("exposure", observed=True):
        a, p = grp[grp["test_group"] == "ad"], grp[grp["test_group"] == "psa"]
        if len(a) < 500 or len(p) < 500:
            continue
        t = two_proportion_ztest(int(a["converted"].sum()), len(a),
                                 int(p["converted"].sum()), len(p))
        seg_rows.append({"segment": str(seg), "n_ad": len(a), "n_psa": len(p),
                         **{k: round(v, 6) for k, v in t.items()}})
    res["by_exposure"] = seg_rows

    day_rows = []
    for day, grp in df.groupby("most_ads_day"):
        a, p = grp[grp["test_group"] == "ad"], grp[grp["test_group"] == "psa"]
        t = two_proportion_ztest(int(a["converted"].sum()), len(a),
                                 int(p["converted"].sum()), len(p))
        day_rows.append({"segment": day, "n_ad": len(a), "n_psa": len(p),
                         **{k: round(v, 6) for k, v in t.items()}})
    res["by_day"] = day_rows

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: res[k] for k in ["n_users", "duplicate_users",
                                          "users_in_both_groups", "srm", "primary",
                                          "power"]}, indent=2))


if __name__ == "__main__":
    main()
