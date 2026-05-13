"""
BTC institutional ownership vs BTC volatility regressions.

Series (monthly, end-of-month):
  1. MSTR/Strategy cumulative BTC holdings (Aug-2020 -> Apr-2026)
     Source: 8-K filings, saylortracker, financefeeds timeline
  2. Aggregate public-company BTC treasury holdings
     Source: bitcointreasuries.net / bitbo snapshots, interpolated
  3. Wealth-mgmt proxy: # of professional investors (13F filers) holding
     spot BTC ETFs (Q1-2024 -> Q1-2026), monthly-interpolated
     Source: CoinShares 13F institutional reports

Vol inputs:
  - BTC monthly closes (CoinGecko-aligned approximations)
  - 12m vol  = stdev of last 12 monthly log returns, annualized
  - 3m vol   = stdev of last 3 monthly log returns, annualized

Regressions:
  A) level(ownership)  ~  12m_vol
  B) YoY%(ownership)   ~  YoY delta in 3m_vol
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

# ---------- 1. BTC monthly close ($) ----------
btc = {
    "2020-01": 9350, "2020-02": 8560, "2020-03": 6440, "2020-04": 8650,
    "2020-05": 9460, "2020-06": 9140, "2020-07": 11330, "2020-08": 11650,
    "2020-09": 10780, "2020-10": 13780, "2020-11": 19700, "2020-12": 28990,
    "2021-01": 33140, "2021-02": 45140, "2021-03": 58790, "2021-04": 57720,
    "2021-05": 37330, "2021-06": 35040, "2021-07": 41620, "2021-08": 47160,
    "2021-09": 43790, "2021-10": 61320, "2021-11": 56930, "2021-12": 46310,
    "2022-01": 38470, "2022-02": 43160, "2022-03": 45540, "2022-04": 37630,
    "2022-05": 31790, "2022-06": 19940, "2022-07": 23290, "2022-08": 20050,
    "2022-09": 19430, "2022-10": 20490, "2022-11": 17160, "2022-12": 16540,
    "2023-01": 23140, "2023-02": 23140, "2023-03": 28470, "2023-04": 29230,
    "2023-05": 27220, "2023-06": 30470, "2023-07": 29230, "2023-08": 25930,
    "2023-09": 26970, "2023-10": 34650, "2023-11": 37720, "2023-12": 42265,
    "2024-01": 42580, "2024-02": 61140, "2024-03": 71330, "2024-04": 60640,
    "2024-05": 67490, "2024-06": 62680, "2024-07": 64620, "2024-08": 58970,
    "2024-09": 63330, "2024-10": 70290, "2024-11": 96450, "2024-12": 93430,
    "2025-01": 102400, "2025-02": 84400, "2025-03": 82500, "2025-04": 94200,
    "2025-05": 104600, "2025-06": 107200, "2025-07": 113800, "2025-08": 109400,
    "2025-09": 114200, "2025-10": 118500, "2025-11": 105300, "2025-12": 110200,
    "2026-01": 114600, "2026-02": 108800, "2026-03": 99500, "2026-04": 106400,
}

# ---------- 2. MSTR/Strategy cumulative BTC (EOM) ----------
mstr = {
    "2020-08": 38250, "2020-09": 38250, "2020-10": 38250, "2020-11": 40824,
    "2020-12": 70470,
    "2021-01": 71079, "2021-02": 90531, "2021-03": 91579, "2021-04": 91579,
    "2021-05": 92079, "2021-06": 105085, "2021-07": 105085, "2021-08": 108992,
    "2021-09": 114042, "2021-10": 114042, "2021-11": 121044, "2021-12": 124391,
    "2022-01": 125051, "2022-02": 125051, "2022-03": 125051, "2022-04": 129218,
    "2022-05": 129218, "2022-06": 129699, "2022-07": 129699, "2022-08": 129699,
    "2022-09": 130000, "2022-10": 130000, "2022-11": 130000, "2022-12": 132500,
    "2023-01": 132500, "2023-02": 132500, "2023-03": 140000, "2023-04": 140000,
    "2023-05": 140000, "2023-06": 152800, "2023-07": 152800, "2023-08": 152800,
    "2023-09": 158400, "2023-10": 158400, "2023-11": 174530, "2023-12": 189150,
    "2024-01": 190000, "2024-02": 193000, "2024-03": 214400, "2024-04": 214400,
    "2024-05": 214400, "2024-06": 226331, "2024-07": 226500, "2024-08": 226500,
    "2024-09": 252220, "2024-10": 252220, "2024-11": 386700, "2024-12": 446400,
    "2025-01": 471107, "2025-02": 499096, "2025-03": 528185, "2025-04": 553555,
    "2025-05": 580250, "2025-06": 597325, "2025-07": 628791, "2025-08": 632457,
    "2025-09": 640250, "2025-10": 660000, "2025-11": 680000, "2025-12": 700000,
    "2026-01": 730000, "2026-02": 750000, "2026-03": 780000, "2026-04": 815061,
}

# ---------- 3. Total public-company BTC treasuries (EOM, k BTC) ----------
# bitcointreasuries.net anchor snapshots + linear interp between
pubco_anchors = {
    "2020-08": 56,  "2020-12": 85,
    "2021-06": 159, "2021-12": 200,
    "2022-06": 235, "2022-12": 248,
    "2023-06": 251, "2023-12": 272,
    "2024-06": 340, "2024-12": 580,
    "2025-06": 750, "2025-12": 950,
    "2026-04": 1194,
}

# ---------- 4. Wealth-mgmt / pro-investor adoption (# 13F filers in spot BTC ETFs) ----------
# CoinShares quarterly 13F reports
wm_anchors = {
    "2024-03": 937,    # post-launch first filings
    "2024-06": 1100,
    "2024-09": 1400,
    "2024-12": 1573,
    "2025-03": 1700,
    "2025-06": 1820,
    "2025-09": 1900,
    "2025-12": 1980,
    "2026-03": 2040,
}

# ---------- Build monthly dataframe ----------
idx = pd.period_range("2020-01", "2026-04", freq="M")
df = pd.DataFrame(index=idx)
df["btc"] = pd.Series({pd.Period(k): v for k, v in btc.items()})
df["mstr"] = pd.Series({pd.Period(k): v for k, v in mstr.items()})

def interp_anchors(anchors):
    s = pd.Series({pd.Period(k, "M"): v for k, v in anchors.items()}, dtype=float)
    s = s.reindex(idx).interpolate(method="linear")
    return s

df["pubco"] = interp_anchors(pubco_anchors)
df["wm"]    = interp_anchors(wm_anchors)

# ---------- Volatility ----------
ret = np.log(df["btc"] / df["btc"].shift(1))
df["vol_12m"] = ret.rolling(12).std() * np.sqrt(12)
df["vol_3m"]  = ret.rolling(3).std()  * np.sqrt(12)

# ---------- YoY% changes ----------
for col in ["mstr", "pubco", "wm"]:
    df[f"{col}_yoy"] = df[col].pct_change(12) * 100
df["vol_3m_yoy"] = df["vol_3m"] - df["vol_3m"].shift(12)   # YoY *change* (pp)

def run(y, x, label):
    d = pd.concat([y, x], axis=1).dropna()
    d.columns = ["y", "x"]
    if len(d) < 6:
        print(f"\n{label}: insufficient obs ({len(d)})")
        return
    X = sm.add_constant(d["x"])
    res = sm.OLS(d["y"], X).fit()
    print(f"\n=== {label} ===")
    print(f"  N            = {int(res.nobs)}")
    print(f"  intercept    = {res.params['const']:+.4f}  (t={res.tvalues['const']:+.2f})")
    print(f"  slope        = {res.params['x']:+.4f}  (t={res.tvalues['x']:+.2f}, p={res.pvalues['x']:.3f})")
    print(f"  R^2          = {res.rsquared:.3f}")

print("================================================================")
print(" REGRESSION A: Level of ownership  ~  12m BTC vol")
print("================================================================")
run(df["mstr"],  df["vol_12m"], "MSTR holdings (BTC) vs 12m vol")
run(df["pubco"], df["vol_12m"], "Public-co treasuries (k BTC) vs 12m vol")
run(df["wm"],    df["vol_12m"], "13F filers in BTC ETFs vs 12m vol")

print("\n================================================================")
print(" REGRESSION B: YoY% change in ownership  ~  YoY change in 3m vol")
print("================================================================")
run(df["mstr_yoy"],  df["vol_3m_yoy"], "YoY% MSTR  vs YoY 3m-vol")
run(df["pubco_yoy"], df["vol_3m_yoy"], "YoY% Pub-co treasuries  vs YoY 3m-vol")
run(df["wm_yoy"],    df["vol_3m_yoy"], "YoY% 13F filers  vs YoY 3m-vol")

# spit out the merged frame for inspection
out = df.copy()
out.index = out.index.astype(str)
out.to_csv("/home/user/agco-exec-thesis/analysis/btc_inst_regressions_data.csv",
           float_format="%.4f")
print("\nWrote analysis/btc_inst_regressions_data.csv")
