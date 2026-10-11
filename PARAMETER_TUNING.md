# CarbonGuard-Q: QAOA parameter-tuning experiment

## Goal

Improve the p=1 slack-free QAOA sampling distribution by comparing feasible-shot rate and optimal-plan frequency across a small grid of fixed parameters. This is a transparent, manual parameter sweep; it is not a claim of globally optimal parameters.

## Important Qollab execution constraint

The Qollab runner may allow only **one circuit execution job per code run**. Therefore, run each parameter pair in a separate execution. Do not put a loop that submits multiple `backend.run(...)` jobs into one Qollab run.

## Baseline

The current baseline is:

- Objective: `interval_robust`
- QAOA depth: `p=1`
- `GAMMA = 0.04`
- `BETA = 0.30`
- Shots: `2048`

Baseline result from the reported IonQ Aria noise-model simulator run:

- Feasible-shot rate: `12.6%`
- Optimal-plan frequency: `3.0%`
- Best feasible sampled plan: `(1, 0, 1, 0)`
- Objective gap to exact feasible optimum: `0.0`

These values are from one run and may vary between executions.

## Suggested grid

Keep the objective, circuit depth, and shots fixed. Change only `GAMMA` and `BETA` at the top of `slack_free.py`.

| Trial | GAMMA | BETA |
|---|---:|---:|
| Baseline | 0.04 | 0.30 |
| T1 | 0.02 | 0.20 |
| T2 | 0.02 | 0.30 |
| T3 | 0.02 | 0.40 |
| T4 | 0.04 | 0.20 |
| T5 | 0.04 | 0.40 |
| T6 | 0.06 | 0.20 |
| T7 | 0.06 | 0.30 |
| T8 | 0.06 | 0.40 |

Run the baseline once more if you want a repeated baseline measurement, then run T1–T8 separately. Use the same shot count for every trial so the comparison is fair.

## What to record

For every run, record:

1. Gamma and beta values.
2. Backend selected (e.g., `IonQ Aria 1 simulator (25q)`).
3. Shot count.
4. Feasible-shot rate.
5. Optimal-plan frequency.
6. Best feasible sampled plan and objective gap.
7. Whether the run completed without error.

Choose the preferred pair primarily by **feasible-shot rate**, then by **optimal-plan frequency** and objective gap. If two pairs are close, repeat them because finite-shot variation can change the ranking. Do not choose a parameter pair based on the most frequent bitstring alone; it may be infeasible.

## Qollab workflow

1. Open the Qollab code editor containing `slack_free.py`.
2. At the top of the file, change only `GAMMA` and `BETA` to the next row in the grid.
3. Keep `SHOTS = 2048` and `OBJECTIVE_MODE = "interval_robust"` unchanged.
4. Run the project once and wait for the output.
5. Copy the metrics into your results table.
6. Repeat with the next pair. One run = one submitted circuit job.

The Qollab editor may call `main()` automatically. If so, remove the final two lines:

```python
if __name__ == "__main__":
    main()
```

Do not remove the `def main():` function itself. This avoids accidental duplicate execution in runners that invoke `main()` automatically.

## Results table template

| Trial | Gamma | Beta | Shots | Feasible % | Optimal-plan % | Best feasible plan | Gap | Backend / notes |
|---|---:|---:|---:|---:|---:|---|---:|---|
| Baseline | 0.04 | 0.30 | 2048 | 12.6 | 3.0 | `(1,0,1,0)` | 0.0 | IonQ Aria simulator |
| T1 | 0.02 | 0.20 | 2048 | | | | | |
| T2 | 0.02 | 0.30 | 2048 | | | | | |
| T3 | 0.02 | 0.40 | 2048 | | | | | |
| T4 | 0.04 | 0.20 | 2048 | | | | | |
| T5 | 0.04 | 0.40 | 2048 | | | | | |
| T6 | 0.06 | 0.20 | 2048 | | | | | |
| T7 | 0.06 | 0.30 | 2048 | | | | | |
| T8 | 0.06 | 0.40 | 2048 | | | | | |

## Reporting responsibly

- Label results from `IonQ Aria 1 (25q) simulator` as **noise-model simulator results**, not physical QPU results.
- The exact classical enumeration is the baseline for this four-bit instance.
- A better sample rate is a circuit-tuning result, not evidence of quantum advantage.
- All supply-chain data are synthetic and illustrative.
