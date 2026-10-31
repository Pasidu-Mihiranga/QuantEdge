We tested machine-learning challengers because a risk model should be challenged. LightGBM and an LSTM failed coverage on validation in every configuration and were dropped. Linear quantile regression stayed as the reported challenger.

The adoption rule was fixed in advance: a challenger must be better on validation, pass coverage, and stay within a 2% margin of the champion on the final test. Linear QR passed coverage on the final test, but its loss was 5.4% worse than the champion's, so it was not adopted. No machine-learning model improved calibrated 99% forecasts for this portfolio.
