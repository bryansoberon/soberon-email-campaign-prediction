import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, FunctionTransformer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
from experiment.core import SEED

CANDIDATES = ['ridge_1','ridge_100','rf_30','rf_100','lgbm_15','lgbm_31']
BASELINES = ['global_mean','global_median','company_mean','last5_median','last','zero']


def make_model(name):
    if name.startswith('ridge_'):
        return make_pipeline(FunctionTransformer(np.log1p), StandardScaler(), Ridge(alpha=float(name.split('_')[1])))
    if name.startswith('rf_'):
        return RandomForestRegressor(n_estimators=160, min_samples_leaf=int(name.split('_')[1]),
            max_depth=14, max_features=.8, bootstrap=True, max_samples=.7, n_jobs=6, random_state=SEED)
    if name.startswith('lgbm_'):
        return LGBMRegressor(objective='regression_l1', n_estimators=400, learning_rate=.04,
            num_leaves=int(name.split('_')[1]), min_child_samples=100, reg_lambda=1.,
            verbosity=-1, n_jobs=6, random_state=SEED, deterministic=True, force_col_wise=True)
    raise ValueError(name)


def baseline(name, frame, target, mean, median):
    if name == 'global_mean': return np.full(len(frame),mean)
    if name == 'global_median': return np.full(len(frame),median)
    if name == 'zero': return np.zeros(len(frame))
    field = {'company_mean':'mean','last5_median':'last5_median','last':'last'}[name]
    return np.where(frame.history_n.gt(0), frame[f'history_{target}_{field}'], median)
