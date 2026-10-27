# Step 23: LSTM Deep Challenger (Joint VaR/ES Network)

**Owner:** R (lead), D (training infrastructure), V (evaluation) · **Week:** 3, Days 1–4 (**time-boxed**) · **Depends on:** 22 (M1–M2: partition, features, leakage tests, scoring) · **Feeds:** 22 (arena), 15 (Model Arena tab), 17, 18, 21 (Paper B)

---

## 1. Target

- A small **LSTM network** that forecasts 1-day portfolio VaR at 90, 95 and 99%, **and 99% ES jointly**. It is trained with a strictly consistent joint loss (FZ0), not with a quantile loss alone.
- It competes in the **same arena** as the champion, LightGBM and linear QR, under the same partition, walk-forward and adoption rule (Step 22 §3.8). It gets no special treatment.
- **Fallback:** the LSTM must be validated by the end of Week 3, Day 4. Otherwise it is dropped from the competition submission and completed in post-competition Weeks 5–8 for Paper B. The competition result never depends on it.

## 2. Why it matters

- **Comparative question:** does a sequence model learn tail dynamics that GARCH and gradient-boosted trees miss? Answering that with the same protocol makes the study worth publishing.
- **The joint ES contribution:** most ML VaR work predicts quantiles only. Training VaR and ES together with an elicitable joint loss (Fissler & Ziegel, 2016; Patton, Ziegel & Chen, 2019), and evaluating with the same loss, is the novel angle Paper B will emphasise.
- **Honesty:** deep models are data-hungry, and there are only about 35 tail days at 99% in development. The design below is deliberately small and regularised, and the result is reported even if the LSTM loses.

## 3. How to achieve it

### 3.1 Inputs

- **Sequence:** the last L trading days (L ∈ {20, 60}) of the **Step 22 feature set** plus pro-forma returns at w_τ(t). The inputs are identical to LightGBM's, so the comparison isolates the model, not the data.
- **Standardisation:** mean and standard deviation from the **training window only**, refitted at every retrain. Never full-sample.
- **Target:** ℓ_{t+1} at point-in-time weights (Step 22 §3.2).

### 3.2 Architecture (non-crossing and ES ≥ VaR by construction)

```
x_{t-L+1..t} → LSTM(1 layer, hidden H ∈ {16, 32}) → dropout 0.2 → Dense(16, ReLU) → head
head:  q90  = a
       q95  = q90 + softplus(b)
       q99  = q95 + softplus(c)
       ES99 = q99 + softplus(d)
```

The softplus increments guarantee q90 ≤ q95 ≤ q99 ≤ ES99 on every day, so no rearrangement is needed, unlike LightGBM.

### 3.3 Loss

- L = pinball_90(q90) + pinball_95(q95) + λ · FZ0(VaR99 = q99, ES99), with λ = 1.
- FZ0 is evaluated in the return convention (VaR, ES < 0) and shares the single implementation in `backtest/scoring.py` (Step 22), so training and evaluation use the identical function.
- Numerical guard: ES is floored at 1e-6 before the log term of FZ0.

### 3.4 Training protocol

| Item | Choice |
|---|---|
| Window | Expanding; **retrain every 63 trading days** (quarterly) inside the walk-forward, with warm-start from the previous weights |
| Early stopping | On the last 20% of each training window (time-ordered), patience 20 epochs, max 300 epochs |
| Optimiser | Adam, learning rate 1e-3, batch 64, gradient clipping at 1.0 |
| Regularisation | Dropout 0.2; weight decay ∈ {1e-4, 1e-3} |
| Grid (validation only) | L ∈ {20, 60} × H ∈ {16, 32} × weight decay ∈ {1e-4, 1e-3} = 8 configurations, chosen once on the validation primary metric |
| Ensemble | **5 seeds**, with outputs averaged (averaging preserves the ordering) |
| Determinism | `torch.manual_seed`, `torch.use_deterministic_algorithms(True)`, CPU only, `num_threads` fixed; seeds recorded in the freeze record |
| Cost estimate | About 30 retrains × 5 seeds × a small network on CPU, roughly 1–2 hours per configuration; run the grid overnight |

### 3.5 Engineering boundaries

- PyTorch (CPU wheel) goes in **`requirements-research.txt`**, not in `requirements.txt`. The Streamlit app **never imports torch**; it reads precomputed predictions from `data/artifacts/lstm_preds_{split}.parquet`.
- Model checkpoints are hashed into the freeze record. Large checkpoints stay out of git (GitHub release asset, or regenerated from seeds).
- `LSTMQuantileModel` wraps the cached predictions behind the Step 08 `RiskModel` protocol, so the Step 11 backtest engine and the Step 22 arena treat it like any other model.

### 3.6 Paper-only ablation

An **MLP** with the same head and loss, fed only the day-t features (no sequence), isolates the gain from recurrence:
- LSTM vs MLP: does the sequence matter?
- MLP vs LightGBM: neural network vs trees.
- LightGBM vs linear QR: does non-linearity matter?

The MLP runs post-competition, for Paper B.

## 4. Implementation plan

| # | File / function | Detail |
|---|---|---|
| 1 | `ml/sequences.py::make_sequences(features, L, train_end)` | Windowed tensors; scaler fitted on rows ≤ train_end only |
| 2 | `ml/lstm_quantile.py::JointQuantileLSTM(nn.Module)` | Architecture §3.2 |
| 3 | `ml/lstm_quantile.py::train_window(...)` | Loss §3.3, early stopping, seed handling |
| 4 | `ml/lstm_quantile.py::walk_forward_lstm(features, target, cfg, split)` | Quarterly retrains, 5-seed ensemble → parquet |
| 5 | `ml/lstm_quantile.py::LSTMQuantileModel` | `RiskModel` adapter over the cached predictions |
| 6 | `scripts/run_lstm_grid.py` | Runs the 8-configuration grid on validation; writes `lstm_grid_val.parquet` |
| 7 | `config.yaml` → `ml.lstm:` | L, H, dropout, weight-decay grid, seeds, retrain cadence, λ |

## 5. Acceptance tests

- **Ordering:** for random inputs, q90 ≤ q95 ≤ q99 ≤ ES99 holds on every output row.
- **Loss correctness:** the FZ0 used in training equals `scoring.fz0` on the same tensors (to 1e-8).
- **Leakage:** the scaler and the sequences built with `train_end = t` are unchanged when data after t is replaced with noise.
- **Recovery:** on simulated GARCH-t losses with known conditional quantiles, 95% coverage of the trained LSTM lies within the binomial band, and its pinball loss is no worse than 10% above the oracle's.
- **Determinism:** two runs with the same seed give identical predictions on CPU.
- **App boundary:** `import torch` does not appear under `app/` (enforced by a grep test).

## 6. Pitfalls

- Over-sized networks for about 3,500 training rows and about 35 tail days. Keep H ≤ 32 and a single layer.
- Shuffled validation for early stopping, which leaks across time.
- Reporting the best seed instead of the ensemble.
- Tuning the grid after seeing test results. The freeze tag forbids it.
- Comparing an LSTM fed with more features against a LightGBM fed with fewer. The inputs must be identical.
- Letting torch into the deployed app (memory, cold starts on Streamlit Cloud).

## 7. Defend it in Q&A

- *"Why an LSTM with so little tail data? Isn't it overfit?"*
  - It is deliberately tiny, regularised, early-stopped on time-ordered data, and averaged over 5 seeds.
  - It was tuned on validation only and tested once.
  - If it lost, we say so; that is a result too.
- *"What does the LSTM add that GARCH doesn't?"* GARCH σ is already one of its inputs. The LSTM can only win by learning non-linear dynamics *beyond* GARCH, such as the interaction of VIX spikes with falling correlation, and the arena measures whether it does.
- *"Why train on FZ0?"* FZ0 is a strictly consistent scoring function for the (VaR, ES) pair. Training on it targets exactly what we are later evaluated on, and it gives a coherent ES forecast rather than a ratio heuristic.
- *"Is it reproducible?"* Yes: fixed seeds, deterministic CPU kernels, hashed checkpoints and cached predictions. The app does not even need PyTorch installed.
