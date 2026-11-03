"""Reproduce the PSEO education-vs-earnings analysis.

Reads the cleaned CSVs in data/, runs both regression models, and writes
summary tables to outputs/tables/ and charts to outputs/charts/.

Run from the repo root:  python src/analysis.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
TABLES.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

# Category groupings as defined in the group's final presentation (slide 5)
CATEGORY = {
    "Accounting": "Social Sciences & Business", "Economics": "Social Sciences & Business",
    "Criminal Justice": "Social Sciences & Business", "Homeland Security": "Social Sciences & Business",
    "Psychology": "Social Sciences & Business",
    "Computer Science": "STEM", "Civil Engineering": "STEM", "Mechanical Engineering": "STEM",
    "Electrical Engineering": "STEM", "Astronomy": "STEM", "Animal Science": "STEM", "Agriculture": "STEM",
    "Nursing": "Health & Human Services", "HDFS": "Health & Human Services", "Education": "Social Sciences & Business",
    "History": "Arts & Humanities", "Philosophy": "Arts & Humanities", "Fine Arts": "Arts & Humanities",
    "Journalism": "Arts & Humanities", "Architecture": "Arts & Humanities",
}
COLORS = {"STEM": "#2a6f97", "Social Sciences & Business": "#e07a1f",
          "Health & Human Services": "#3a9d5d", "Arts & Humanities": "#8c5aa8"}

plt.rcParams.update({"figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titleweight": "bold"})
usd = mtick.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K")

majors = pd.read_csv(DATA / "pa_major_earnings_by_degree.csv")
reg = pd.read_csv(DATA / "regression_data.csv")

# ---------- Tables ----------
bach = majors[["major", "year1_bachelors", "year10_bachelors"]].copy()
bach["category"] = bach["major"].map(CATEGORY)
bach["growth_$"] = bach["year10_bachelors"] - bach["year1_bachelors"]
bach["growth_%"] = (bach["growth_$"] / bach["year1_bachelors"] * 100).round(1)
bach = bach.sort_values("year10_bachelors", ascending=False)
bach.to_csv(TABLES / "bachelors_earnings_by_major.csv", index=False)

cat = (bach.groupby("category")[["year1_bachelors", "year10_bachelors", "growth_%"]]
       .median().round(1).sort_values("year10_bachelors", ascending=False))
cat.to_csv(TABLES / "median_earnings_by_category.csv")

by_degree = (reg.groupby(["degree_level", "degree"])[["year1_earnings", "year10_earnings"]]
             .agg(["count", "median", "mean"]).round(0))
by_degree.columns = ["_".join(c) for c in by_degree.columns]
by_degree.reset_index().to_csv(TABLES / "earnings_by_degree_level.csv", index=False)

m1 = smf.ols("year10_earnings ~ degree_level", data=reg).fit()
m2 = smf.ols("year10_earnings ~ degree_level + C(major)", data=reg).fit()
summary = pd.DataFrame([
    {"model": "Degree level only", "n": int(m1.nobs), "r_squared": m1.rsquared, "adj_r_squared": m1.rsquared_adj,
     "degree_level_coef": m1.params["degree_level"], "degree_level_p": m1.pvalues["degree_level"],
     "model_f_p": m1.f_pvalue},
    {"model": "Degree level + major fixed effects", "n": int(m2.nobs), "r_squared": m2.rsquared,
     "adj_r_squared": m2.rsquared_adj, "degree_level_coef": m2.params["degree_level"],
     "degree_level_p": m2.pvalues["degree_level"], "model_f_p": m2.f_pvalue},
]).round(4)
summary.to_csv(TABLES / "regression_summary.csv", index=False)
(TABLES / "regression_full_output.txt").write_text(
    "MODEL 1: year10_earnings ~ degree_level\n" + str(m1.summary()) +
    "\n\n\nMODEL 2: year10_earnings ~ degree_level + C(major)\n" + str(m2.summary()))

# ---------- Charts ----------
# 1. Year 10 bachelor's earnings by major (Excel "Slide 7 Graph")
d = bach.sort_values("year10_bachelors")
fig, ax = plt.subplots(figsize=(8, 7))
ax.barh(d["major"], d["year10_bachelors"], color=d["category"].map(COLORS))
ax.xaxis.set_major_formatter(usd)
ax.set_title("Year 10 Median Earnings by Major (Bachelor's, PA)")
for c, col in COLORS.items():
    ax.bar(0, 0, color=col, label=c)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(CHARTS / "01_year10_earnings_by_major.png"); plt.close(fig)

# 2. Top 10 majors: Year 1 vs Year 10 (Excel "Slide 8 Graph")
d = bach.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 6))
y = range(len(d))
ax.barh([i + 0.2 for i in y], d["year1_bachelors"], height=0.4, label="Year 1", color="#9ccae8")
ax.barh([i - 0.2 for i in y], d["year10_bachelors"], height=0.4, label="Year 10", color="#2a6f97")
ax.set_yticks(list(y)); ax.set_yticklabels(d["major"])
ax.xaxis.set_major_formatter(usd)
ax.set_title("Top 10 Majors: Year 1 vs Year 10 Median Earnings")
ax.legend(frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(CHARTS / "02_top10_year1_vs_year10.png"); plt.close(fig)

# 3. Earnings growth slope chart (Excel "Slide 9 Graph")
slope_majors = ["Astronomy", "Philosophy", "Economics", "History", "Animal Science",
                "Journalism", "Accounting", "Psychology", "Criminal Justice", "Fine Arts"]
d = bach.set_index("major").loc[slope_majors]
fig, ax = plt.subplots(figsize=(7, 6))
# spread end labels so they don't overlap (min gap of $2.6K)
d = d.sort_values("year10_bachelors")
label_y, last = [], -1e9
for v in d["year10_bachelors"]:
    last = max(v, last + 2600)
    label_y.append(last)
for (m, r), ly in zip(d.iterrows(), label_y):
    col = COLORS[r["category"]]
    ax.plot([0, 1], [r["year1_bachelors"], r["year10_bachelors"]], marker="o", color=col, lw=2)
    ax.text(1.04, ly, f"{m} (+{r['growth_%']:.0f}%)", va="center", fontsize=8.5, color=col)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Year 1", "Year 10"]); ax.set_xlim(-0.1, 1.6)
ax.yaxis.set_major_formatter(usd)
ax.set_title("Earnings Growth from Year 1 to Year 10 (Bachelor's)")
fig.tight_layout(); fig.savefig(CHARTS / "03_growth_year1_to_year10.png"); plt.close(fig)

# 4. Degree level comparison (Excel "Slide 10 Graph")
d = majors.dropna(subset=["year10_masters"]).set_index("major")[
    ["year10_bachelors", "year10_masters", "year10_phd"]]
d.columns = ["Bachelor's", "Master's", "PhD"]
ax = d.plot(kind="bar", figsize=(7, 5), color=["#9ccae8", "#2a6f97", "#163d57"], rot=0, width=0.75)
ax.yaxis.set_major_formatter(usd)
ax.set_title("Year 10 Median Earnings by Degree Level"); ax.set_xlabel("")
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(CHARTS / "04_degree_level_comparison.png"); plt.close()

# 5. Regression: degree level vs year 10 earnings, with model fit
fig, ax = plt.subplots(figsize=(7, 5))
jitter = reg["degree_level"] + (reg.index % 5 - 2) * 0.03
ax.scatter(jitter, reg["year10_earnings"], color=reg["major"].map(CATEGORY).map(COLORS), alpha=0.8)
xs = pd.Series([1, 3])
ax.plot(xs, m1.params["Intercept"] + m1.params["degree_level"] * xs, color="black", lw=1.5,
        label=f"OLS fit (R² = {m1.rsquared:.2f})")
ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["Bachelor's", "Master's", "PhD"])
ax.yaxis.set_major_formatter(usd)
ax.set_title("Degree Level vs Year 10 Earnings (n = 49)")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(CHARTS / "05_regression_degree_vs_earnings.png"); plt.close(fig)

# 6. Median year 10 earnings by category
fig, ax = plt.subplots(figsize=(7, 4))
c = cat.sort_values("year10_bachelors")
ax.barh(c.index, c["year10_bachelors"], color=[COLORS[i] for i in c.index])
ax.xaxis.set_major_formatter(usd)
ax.set_title("Median Year 10 Earnings by Major Category (Bachelor's)")
fig.tight_layout(); fig.savefig(CHARTS / "06_earnings_by_category.png"); plt.close(fig)

print(summary.to_string(index=False))
