# QuantEdge 1.0: Risk-Aware Portfolio for the Serendib University Endowment

A Python and Streamlit application for the QuantEdge 1.0 Final Challenge. It recommends how to invest a USD 10M conservative endowment using seven ETFs (SPY, EFA, EEM, AGG, GLD, XLE, XLK).

The application:
- builds and selects the portfolio with quantitative methods;
- measures its risk with Value-at-Risk, Expected Shortfall and Extreme Value Theory;
- checks those risk estimates out-of-sample with Kupiec, Christoffersen and the Basel traffic light;
- compares the best conventional model with a machine-learning challenger (linear quantile regression; LightGBM and an LSTM were evaluated and rejected);
- stress-tests the portfolio against historical and hypothetical crises;
- gives an accept / adjust the risk limit / reject outcome, with the final recommendation written by the team.

## Run it

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). On Windows use `.\make.ps1 <target>`; elsewhere `make <target>`.

```
.\make.ps1 setup       # create .venv (Python 3.12) and install pinned requirements + the package
.\make.ps1 pipeline    # recompute every artifact from the frozen snapshot (about 20 s with cached backtests)
.\make.ps1 pipeline --force-backtests   # also recompute the walk-forward backtests (about 10 min)
.\make.ps1 run         # start the Streamlit app (reads data/artifacts only, no network)
.\make.ps1 test        # fast tests; .\make.ps1 test-all includes the slow ones
```

The raw data snapshot in `data/raw/` is frozen and SHA-256 hashed (`data/raw/manifest.json`). Refreshing it is an explicit step: `.\make.ps1 data`.

## Where things are

| Path | Contents |
|---|---|
| `config.yaml` | every parameter (dates, IPS limits, model settings, decision thresholds) |
| `src/quantedge/` | the package: data, portfolio, risk, backtest, stress, decision, ml |
| `app/` | Streamlit app: Home plus 10 pages |
| `tests/` | pytest suite (closed-form, simulation-recovery, textbook and leakage tests) |
| `doc/decisions/` | team decision records and the methodology-freeze checklist |
| `TODO.md` | implementation progress, step by step |
| `AGENTS.md` | conventions for anyone writing code in this repository |

## Planning documents

- [Master implementation plan](doc/QuantEdge_Implementation_Plan.md)
- [Hybrid validation and ML challenger plan](doc/ML_Challenger_and_Partition_Plan.md): a leakage-safe chronological partition combined with walk-forward, with a linear quantile-regression challenger against the best conventional VaR model (LightGBM and LSTM rejected, archived at the git tag `archive/mirofish-ml`)
- [Step-by-step plans (index)](doc/steps/00_INDEX.md): 23 steps, from data acquisition to the pitch. Steps 19–21 (MiroFish behavioural stress lab, its evaluation, research papers) and 23 (LSTM) were removed on 2026-10-28 after an independent audit; they are archived at the git tag `archive/mirofish-ml`

## Status

Steps 01–13, the ML challengers and the Streamlit app are implemented and tested. Results are provisional until the methodology freeze: the data split is development 2004–2018, validation 2019–2022 (all selection decisions) and a locked final test from 2023, which is evaluated once after the freeze. See [TODO.md](TODO.md) and [the freeze checklist](doc/decisions/freeze_checklist.md).
