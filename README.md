# CarbonGuard-Q

**Carbon-aware, scenario-aware supply-chain recovery using QUBO + QAOA**

CarbonGuard-Q is a small hybrid quantum–classical prototype. It asks: when a supply-chain disruption happens, which two recovery actions restore enough supply while balancing cost and emissions across normal and high-carbon scenarios?

All data are synthetic and intended only for demonstration. This prototype does not establish quantum advantage.

## Decision model

| Variable | Action | Capacity | Cost units | Normal emissions units | Carbon-shock emissions units |
|---|---|---:|---:|---:|---:|
| `x1` | Regional alternative supplier | 3 | 5 | 4 | 5 |
| `x2` | Shift production to backup plant | 3 | 6 | 3 | 7 |
| `x3` | Lower-carbon ground freight | 2 | 3 | 1 | 2 |
| `x4` | Air-freight expediting | 2 | 7 | 8 | 10 |

- One cost unit represents $100; one emissions unit represents 100 kg CO₂e.
- Scenario weights are 60% normal / 40% carbon shock, illustrative assumptions.
- Objective: `cost + 0.5 * expected_emissions` in the scaled units above.
- Constraints: exactly two actions; capacity at least four; ground freight and air expediting are mutually exclusive.
- Three binary slack bits encode excess capacity above four. Penalty coefficient: 50.

## Exact classical baseline

`main.py` enumerates all 16 operational action combinations and all 128 seven-bit QUBO states. It verifies that the direct constraint expression, expanded QUBO polynomial, and Ising energy agree on all 128 bitstrings.

Expected exact optimum:

- Actions: `x = (1, 0, 1, 0)` — regional alternative supplier + lower-carbon ground freight.
- Slack: `(s0, s1, s2) = (1, 0, 0)`.
- Capacity: 5 recovery units.
- Cost: 8 units ($800).
- Normal emissions: 5 units (500 kg CO₂e).
- Carbon-shock emissions: 7 units (700 kg CO₂e).
- Expected emissions: 5.8 units (580 kg CO₂e).
- Objective: 10.9.

These are results from a tiny synthetic example, not a real-world forecast.

## Run local classical checks

Requires Python 3, but not Qiskit:

```bash
python run_tests.py
```

Expected final line:

```text
PASS: QUBO and Ising energies match on 128 states; exact optimum verified.
```

## Run in Qollab

1. Create a Python/Qiskit project in Qollab.
2. Copy `main.py` into the project editor.
3. Run it using the Qollab-provided, preconfigured `backend`. The script does not configure credentials or select a provider.
4. Start with the built-in/local simulator; optionally test an IonQ simulator/noise model if available.
5. Review the formulation checks, exact baseline, QAOA counts, feasible-shot rate, optimal-plan frequency and objective gap.

The script expects a Qiskit-compatible object named `backend` to be exposed by Qollab. If the project runtime uses a different documented variable name, adapt only that binding. Do not place API keys or credentials in source code.

## Technical notes

For `E(x) = c + Σ a_i x_i + Σ b_ij x_i x_j`, with `x_i = (1 - Z_i)/2`:

- `offset = c + Σ(a_i / 2) + Σ(b_ij / 4)`
- `h_i = -a_i / 2 - Σ(b_ij / 4)` for each quadratic term incident on i
- `J_ij = b_ij / 4`

The cost layer uses `rz(2 * gamma * h_i)` and `rzz(2 * gamma * J_ij)`; the mixer uses `rx(2 * beta)`. The global Ising offset does not affect measurement probabilities.

Initial settings `gamma=0.02`, `beta=0.35`, `p=1`, and 2,048 shots are fixed demonstration parameters, not tuned parameters. QAOA may fail to sample a feasible or optimal state. The exact classical result remains the reference answer.

## Scope and limitations

- Synthetic data, simplified scenarios, and a weighted-sum objective.
- Two scenarios with assumed probabilities.
- Capacity is fixed across scenarios; emissions factors change.
- No real-world validation, production-readiness claim or quantum-advantage claim.
- Seven qubits are intentionally small so the entire state space can be verified.

Potential extensions: parameter sweep, scenario-dependent capacity, worst-case carbon regret, cost/emissions Pareto comparison, and sensitivity analysis.


## Required attribution

This effort is supported by Qollab & IonQ.


## Experimental branch: slack-free custom penalty

`slack_free.py` is a separate four-qubit experiment motivated by arXiv:2504.12611. It uses a step penalty evaluated directly on each 4-bit action assignment, so no capacity slack bits are needed. Because this custom cost is generally non-quadratic, the exact 16-value truth table is expanded into a diagonal Pauli-Z Hamiltonian that can be implemented with parity CNOT ladders and RZ gates. This is a diagonal cost-function QAOA experiment, not a standard quadratic QUBO.

Run its classical checks with `python test_slack_free.py`. The circuit itself must be run in Qollab with its configured `backend`. The current step penalty is a toy choice; its scale and circuit cost should be benchmarked. This implementation does not reproduce the paper's VQE experiments and does not implement the PBS paper's tree-specific constrained mixer.

## Robust-objective sensitivity experiment

The slack-free branch now supports three cost/emissions risk models, selected by `OBJECTIVE_MODE` in `slack_free.py`:

- `expected`: nominal 60% normal / 40% carbon-shock scenario weights.
- `worst_case`: use the larger of the normal- and shock-scenario emissions for each plan.
- `interval_robust` (default): maximize expected emissions over an uncertain shock probability in `[0.20, 0.60]`. Since expected emissions are linear in that probability, checking both interval endpoints is sufficient for this two-scenario model.

All three modes are enumerated classically across the five feasible plans. The default interval-robust formulation also defines the diagonal energy used to build the four-qubit QAOA cost layer. This is a small robust-sensitivity demonstration, not a full two-stage distributionally robust optimization model: the interval and data are illustrative, and costs/capacity are not scenario-dependent. The nominal, worst-case and interval-robust objective values should be reported side by side, and QAOA sampling results should be compared against each mode's exact classical baseline.

Run checks:

```bash
python run_tests.py
python test_slack_free.py
```

The tests verify the original QUBO/Ising equivalence and the slack-free Pauli-Z expansion for all 16 action states under all three risk models. They do not execute QAOA; run the circuit in Qollab to collect measured results.
