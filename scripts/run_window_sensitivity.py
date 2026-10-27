"""Step 11 window sensitivity: backtests with W = 250 or 1000 next to the default 500.

    .venv\\Scripts\\python scripts\run_window_sensitivity.py 250
Writes backtest_*_{W}.parquet and backtest_selection_{dev,val}_{W}.parquet; never changes champion.json.
"""

import sys

import pandas as pd

from quantedge import pipeline as p
from quantedge.config import load_config
from quantedge.paths import ARTIFACTS

window = int(sys.argv[1])
cfg = load_config()
macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
sel = p.run_portfolio_selection(cfg, macro)
focus = str(sel["scorecard"].index[0])
out = p.run_backtests(cfg, sel["results"][focus], f"{focus} (provisional)", window=window)
cols = ["exceptions", "expected", "kupiec_p", "cc_p", "rolling_red", "z2_zone", "pinball", "passes"]
print(f"W = {window}: champion by the rule would be {out['champion']}")
print(out["tables"]["val"][cols].round(5).to_string())
