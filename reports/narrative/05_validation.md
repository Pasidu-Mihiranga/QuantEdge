Every model forecasts each day using only earlier data and the weights actually held. We chose on 2019–2022 and tested once on 2023–2026, after freezing the method.

On validation the rule picked GJR conditional EVT: the lowest pinball loss among models passing Kupiec, Christoffersen conditional coverage, rolling Basel zones and the ES test (14 breaches against 10.1 expected; Kupiec p = 0.24). Every breach has a documented market cause and none is a data error. Six were the first days of a new crisis.

On the one-shot test the model passed: 9 breaches against 9.6 expected over 955 days, Kupiec p = 0.86, conditional coverage p = 0.19, and the lowest loss of eleven models. Models without GJR's asymmetry failed because their breaches clustered. Our independent notebook reproduced every breach count and loss.

Limits: about ten expected breaches give limited power, so the test shows the model is not detectably wrong, not that it is right. Over 2008–2026 the joint coverage test falls just below 5% because of clustering in 2008.
