"""psm_baseline.py — paper's baseline: propensity-score analysis on structured
covariates, estimating ATE of early vasopressor on 28-day mortality."""
import glob
import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

cohort = pd.read_parquet("results/master_cohort.parquet")
COVS = ["age","male","sofa_peak","sapsii","charlson","map","heart_rate",
        "resp_rate","temperature","spo2","creatinine","wbc","platelets",
        "bilirubin_total","lactate"]
cohort = cohort.dropna(subset=["treated","mortality_28d"]).copy()
T = cohort["treated"].astype(int).values
Y = cohort["mortality_28d"].astype(int).values

X = cohort[COVS].copy()
print(f"Cohort {len(X)}; missing before impute:")
print((X.isna().mean().sort_values(ascending=False).head(6)*100).round(1).to_string())
imp = IterativeImputer(max_iter=10, random_state=0, sample_posterior=False)
Xi = pd.DataFrame(imp.fit_transform(X), columns=COVS, index=X.index)

Xs = StandardScaler().fit_transform(Xi.values)
ps_model = LogisticRegression(max_iter=1000, C=1.0).fit(Xs, T)
ps = ps_model.predict_proba(Xs)[:,1]
print(f"\nPropensity score range: [{ps.min():.3f}, {ps.max():.3f}], "
      f"treated mean PS {ps[T==1].mean():.3f}, control mean PS {ps[T==0].mean():.3f}")

crude = Y[T==1].mean() - Y[T==0].mean()

p_treat = T.mean()
w = np.where(T==1, p_treat/ps, (1-p_treat)/(1-ps))
lo,hi = np.percentile(ps,[1,99])
keep = (ps>=lo)&(ps<=hi)
Yk,Tk,wk = Y[keep],T[keep],w[keep]
ipw_treated = np.sum(wk[Tk==1]*Yk[Tk==1])/np.sum(wk[Tk==1])
ipw_control = np.sum(wk[Tk==0]*Yk[Tk==0])/np.sum(wk[Tk==0])
ate_ipw = ipw_treated - ipw_control

from scipy.spatial import cKDTree
tr_idx = np.where(T==1)[0]; ct_idx = np.where(T==0)[0]
tree = cKDTree(ps[ct_idx].reshape(-1,1))
d,match = tree.query(ps[tr_idx].reshape(-1,1), k=1)
cal = d<=0.05
matched_control = ct_idx[match[cal]]
matched_treated = tr_idx[cal]
ate_match = Y[matched_treated].mean() - Y[matched_control].mean()

from sklearn.linear_model import LogisticRegression as LR
Xt = np.column_stack([Xs, T])
out_model = LR(max_iter=1000).fit(Xt, Y)
X1 = np.column_stack([Xs, np.ones(len(T))])
X0 = np.column_stack([Xs, np.zeros(len(T))])
ate_reg = (out_model.predict_proba(X1)[:,1] - out_model.predict_proba(X0)[:,1]).mean()

print(f"\n===== ATE ESTIMATES (early vasopressor -> 28-day mortality) =====")
print(f"  crude (unadjusted):        {crude:+.3f}")
print(f"  IPW (stabilized, trimmed): {ate_ipw:+.3f}   (n={keep.sum()})")
print(f"  PS matching (1:1, cal.05): {ate_match:+.3f}   (n_matched={cal.sum()})")
print(f"  regression adjustment:     {ate_reg:+.3f}")