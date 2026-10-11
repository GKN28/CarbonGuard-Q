# CarbonGuard-Q — Project Card

**Theme:** Quantum Impact

**Problem:** Emergency supply-chain recovery can restore service while increasing emissions through carbon-intensive production or expedited transport. Cost-only decisions can hide this environmental trade-off.

**Approach:** Four recovery actions are binary decisions. The model balances scaled cost and expected emissions under normal and carbon-shock scenarios. Action-count, minimum-capacity and compatibility constraints are encoded in a QUBO. A one-layer QAOA circuit samples candidate solutions. An exact classical baseline enumerates 16 action combinations, while a 128-state check validates QUBO and Ising energies.

**Synthetic baseline result:** The exact optimum selects a regional alternative supplier and lower-carbon ground freight, objective 10.9 in the stated toy units. Report QAOA results only after the actual Qollab run; do not assume it reaches the classical optimum.

**Impact:** Demonstrates comparing recovery strategies on cost and emissions under a change in carbon intensity, rather than optimizing cost or service in isolation.

**Novelty claim:** A transparent scenario-aware, carbon-sensitive recovery formulation with end-to-end QUBO/Ising consistency checks and an exact classical reference. It is not a new quantum algorithm and does not claim quantum advantage.

**Limitations:** Synthetic data; four actions and two scenarios; assumed scenario probabilities; simplified objective weights; untuned QAOA parameters; no real-world validation.

**AI assistance:** AI assistance was used for ideation, mathematical formulation, implementation drafting, and documentation. Run and review the code in Qollab before submission.

**Required attribution:** This effort is supported by Qollab & IonQ.


## Experimental extension
A separate `slack_free.py` branch uses four decision qubits and a direct step penalty over the 4-bit truth table. Its non-quadratic diagonal cost is expanded exactly into Pauli-Z strings. This is motivated by slack-free penalty research, but it is not a reproduction of that paper's VQE method and does not implement a constrained mixer.


**Robustness extension:** The slack-free four-qubit branch compares nominal expected emissions (60/40 scenario weights), worst-case scenario emissions, and an interval-robust objective where carbon-shock probability varies between 20% and 60%. The default QAOA cost layer uses the interval-robust objective. This is a small sensitivity analysis, not a full distributionally robust optimization model; assumptions and data are synthetic.
