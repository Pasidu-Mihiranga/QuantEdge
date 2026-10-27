# QuantEdge 1.0: Risk-Aware Portfolio for the Serendib University Endowment

A Python and Streamlit application for the QuantEdge 1.0 Final Challenge. It recommends how to invest a USD 10M conservative endowment using seven ETFs (SPY, EFA, EEM, AGG, GLD, XLE, XLK).

The application will:
- build and select the portfolio with quantitative methods;
- measure its risk with Value-at-Risk, Expected Shortfall and Extreme Value Theory;
- check those risk estimates out-of-sample with Kupiec, Christoffersen and the Basel traffic light;
- stress-test it against historical and hypothetical crises;
- give an accept / adjust / reject recommendation.

## Planning documents

- [Master implementation plan](doc/QuantEdge_Implementation_Plan.md)
- [Hybrid validation and ML challenger plan](doc/ML_Challenger_and_Partition_Plan.md): chronological train/validation/test partition combined with walk-forward, plus a LightGBM quantile-VaR challenger
- [Step-by-step plans (index)](doc/steps/00_INDEX.md): 21 steps, from data acquisition to the pitch, plus the MiroFish behavioural stress lab, its with/without evaluation, and the research paper track

## Status

The planning phase is complete. Source code, data snapshot and the Streamlit app will be added following the step plans.
