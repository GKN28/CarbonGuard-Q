"""CarbonGuard-Q slack-free experiment.

This is an experimental branch alongside main.py, not a replacement for the
7-qubit quadratic-QUBO baseline. It uses four decision qubits and an exact
non-quadratic diagonal cost function with a custom step penalty. The diagonal
function is expanded into a 4-qubit Pauli-Z Hamiltonian for standard QAOA.

All data are synthetic. No quantum advantage is claimed.
"""
from itertools import product
from math import isclose

N = 4
CAPACITY = (3, 3, 2, 2)
COST = (5.0, 6.0, 3.0, 7.0)
NORMAL = (4.0, 3.0, 1.0, 8.0)
SHOCK = (5.0, 7.0, 2.0, 10.0)
NORMAL_WEIGHT = 0.60
SHOCK_WEIGHT = 0.40
# Robust sensitivity interval: the carbon-shock probability may be anywhere
# from 20% to 60%. These are illustrative assumptions, not calibrated data.
SHOCK_PROBABILITY_INTERVAL = (0.20, 0.60)
OBJECTIVE_MODE = "interval_robust"  # expected | worst_case | interval_robust
CARBON_WEIGHT = 0.50
PENALTY = 50.0
SHOTS = 2048
# GAMMA = 0.04
# BETA = 0.30
GAMMA = 0.08
BETA = 0.30
ACTIONS = ("alternative supplier", "backup plant", "ground freight", "air freight")


def expected_emissions(x, shock_weight=SHOCK_WEIGHT):
    normal_weight = 1.0 - shock_weight
    return sum(x[i] * (normal_weight * NORMAL[i] + shock_weight * SHOCK[i]) for i in range(N))


def scenario_emissions(x):
    return (sum(x[i] * NORMAL[i] for i in range(N)),
            sum(x[i] * SHOCK[i] for i in range(N)))


def objective(x, shock_weight=SHOCK_WEIGHT, mode="expected"):
    """Cost + carbon-weighted emissions under one of three risk models.

    expected: use the nominal 60/40 scenario weights.
    worst_case: use the worse of the normal and shock emissions scenarios.
    interval_robust: maximize expected emissions over shock probability
    p in SHOCK_PROBABILITY_INTERVAL. Since this is linear in p, an endpoint
    is worst; evaluating both endpoints avoids assuming which one in general.
    """
    cost = sum(x[i] * COST[i] for i in range(N))
    normal, shock = scenario_emissions(x)
    if mode == "expected":
        emissions = expected_emissions(x, shock_weight)
    elif mode == "worst_case":
        emissions = max(normal, shock)
    elif mode == "interval_robust":
        lo, hi = SHOCK_PROBABILITY_INTERVAL
        emissions = max((1-p)*normal + p*shock for p in (lo, hi))
    else:
        raise ValueError(f"Unknown objective mode: {mode}")
    return cost + CARBON_WEIGHT * emissions


def capacity(x):
    return sum(x[i] * CAPACITY[i] for i in range(N))


def feasible(x):
    return sum(x) == 2 and capacity(x) >= 4 and not (x[2] and x[3])


def custom_energy(x, penalty=PENALTY, mode=OBJECTIVE_MODE):
    """Exact diagonal energy: original objective + step penalty for any violation.

    This avoids slack variables. It is generally not quadratic; the complete
    4-bit truth table is mapped to a diagonal Pauli-Z Hamiltonian below.
    """
    violation = (sum(x) != 2) or (capacity(x) < 4) or (x[2] and x[3])
    return objective(x, mode=mode) + (penalty if violation else 0.0)


def exact_baseline(shock_weight=SHOCK_WEIGHT, mode=OBJECTIVE_MODE):
    plans=[]
    for x in product((0,1), repeat=N):
        if feasible(x):
            plans.append({
                "x": x,
                "capacity": capacity(x),
                "cost": sum(x[i]*COST[i] for i in range(N)),
                "normal_emissions": sum(x[i]*NORMAL[i] for i in range(N)),
                "shock_emissions": sum(x[i]*SHOCK[i] for i in range(N)),
                "expected_emissions": expected_emissions(x, shock_weight),
                "objective": objective(x, shock_weight, mode),
                "expected_objective": objective(x, shock_weight, "expected"),
                "worst_case_objective": objective(x, shock_weight, "worst_case"),
                "interval_robust_objective": objective(x, shock_weight, "interval_robust"),
                "robust_emissions": max((1-p)*sum(x[i]*NORMAL[i] for i in range(N)) + p*sum(x[i]*SHOCK[i] for i in range(N))
                                         for p in SHOCK_PROBABILITY_INTERVAL),
            })
    return sorted(plans, key=lambda p:p["objective"])


def all_states():
    return list(product((0,1), repeat=N))


def z_values(x):
    return tuple(1 - 2*b for b in x)


def pauli_z_coefficients(energy_fn=None):
    """Walsh-Hadamard expansion E(x)=sum_S c_S product_{i in S} Z_i.

    Returns {subset_tuple: coefficient}; empty subset is the global offset.
    This expansion is exact up to floating point tolerance and can contain
    3- and 4-local terms because the step penalty is not a quadratic QUBO.
    """
    if energy_fn is None:
        energy_fn = lambda x: custom_energy(x, mode=OBJECTIVE_MODE)
    states=all_states()
    energies={x:energy_fn(x) for x in states}
    coeffs={}
    for mask in range(1 << N):
        subset=tuple(i for i in range(N) if mask & (1 << i))
        total=0.0
        for x in states:
            z=z_values(x)
            parity=1
            for i in subset:
                parity *= z[i]
            total += energies[x]*parity
        coeffs[subset]=total/(1 << N)
    return coeffs


COEFFS = pauli_z_coefficients()


def pauli_energy(x, coeffs=None):
    coeffs = COEFFS if coeffs is None else coeffs
    z=z_values(x)
    energy=0.0
    for subset, coeff in coeffs.items():
        term=coeff
        for i in subset:
            term *= z[i]
        energy += term
    return energy


def verify_diagonal_expansion():
    for x in all_states():
        if not isclose(custom_energy(x, mode=OBJECTIVE_MODE), pauli_energy(x), abs_tol=1e-8):
            raise AssertionError(f"Diagonal expansion mismatch at {x}: {custom_energy(x, mode=OBJECTIVE_MODE)} vs {pauli_energy(x)}")
    return 2**N


def exact_custom_baseline():
    states=all_states()
    best=min(states, key=custom_energy)
    return len(states), best, custom_energy(best)


def build_qaoa_circuit(gamma=GAMMA, beta=BETA):
    """Four-qubit p=1 QAOA for arbitrary diagonal cost via Z-string expansion."""
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:
        raise RuntimeError("Qiskit is required in the Qollab runtime to build the circuit.") from exc
    qc=QuantumCircuit(N,N)
    qc.h(range(N))
    # e^(-i gamma c_S Z_S): parity CNOT ladder, RZ, undo ladder.
    # Identity term changes only global phase and is omitted from the circuit.
    for subset, coeff in COEFFS.items():
        if not subset or abs(coeff) < 1e-10:
            continue
        target=subset[-1]
        controls=list(subset[:-1])
        for control in controls:
            qc.cx(control,target)
        qc.rz(2.0*gamma*coeff,target)
        for control in reversed(controls):
            qc.cx(control,target)
    for i in range(N):
        qc.rx(2.0*beta,i)
    qc.measure(range(N),range(N))
    return qc


def decode_count_key(bitstring):
    return tuple(int(bit) for bit in bitstring.replace(" ","")[::-1])


def run_qaoa(backend):
    plans=exact_baseline(mode=OBJECTIVE_MODE)
    print("=== SLACK-FREE CARBON GUARD-Q ===")
    print("Objective mode:", OBJECTIVE_MODE)
    print("Nominal shock probability:", SHOCK_WEIGHT, "; robust interval:", SHOCK_PROBABILITY_INTERVAL)
    print("Custom diagonal step penalty; 4 decision qubits; synthetic data only.")
    print("Pauli-Z terms including offset:", len(COEFFS))
    print("Nonzero non-identity Z strings:", sum(1 for s,c in COEFFS.items() if s and abs(c)>1e-10))
    n=verify_diagonal_expansion()
    print(f"Exact diagonal/Pauli-Z energy check passed for {n} states.")
    nstates,bits,energy=exact_custom_baseline()
    print("Exact custom-cost optimum:", bits, "energy=", round(energy,4))
    print("Exact feasible baseline:", plans[0]["x"], "objective=", round(plans[0]["objective"],4))
    print("Best-plan expected objective:", round(plans[0]["expected_objective"],4))
    print("Best-plan worst-case objective:", round(plans[0]["worst_case_objective"],4))
    print("Best-plan interval-robust objective:", round(plans[0]["interval_robust_objective"],4))
    print("\nExact optima by risk model:")
    for mode in ("expected", "worst_case", "interval_robust"):
        p = exact_baseline(mode=mode)[0]
        print(f"  {mode}: x={p['x']}, objective={p['objective']:.3f}")
    circuit=build_qaoa_circuit()
    print(f"Submitting 4-qubit p=1 circuit, {SHOTS} shots, gamma={GAMMA}, beta={BETA}.")
    result=backend.run(circuit,shots=SHOTS).result()
    counts=result.get_counts()
    total=sum(counts.values())
    feasible_shots=0
    optimal_shots=0
    best_sample=None
    best_x=None
    best_obj=None
    for key,count in counts.items():
        x=decode_count_key(key)
        if feasible(x):
            feasible_shots += count
            if x == plans[0]["x"]:
                optimal_shots += count
            val=objective(x, mode=OBJECTIVE_MODE)
            if best_obj is None or val < best_obj:
                best_obj, best_sample, best_x=val, key, x
    print("Top measured states:")
    for key,count in sorted(counts.items(),key=lambda kv:kv[1],reverse=True)[:10]:
        x=decode_count_key(key)
        print(key, "count=",count,"energy=",round(custom_energy(x),4),"feasible=",feasible(x),"actions=",x)
    print("Feasible-shot rate:", f"{feasible_shots/total:.1%}")
    print("Optimal-plan frequency:", f"{optimal_shots/total:.1%}")
    if best_obj is None:
        print("No feasible measured state sampled; tune parameters or increase shots.")
    else:
        print("Best feasible sampled plan:",best_x,"objective=",round(best_obj,4))
        print("Objective gap vs exact feasible optimum:",round(best_obj-plans[0]["objective"],4))
    print("This branch uses a non-quadratic diagonal penalty represented by Z strings; it is not a pure quadratic QUBO.")
    print("No quantum-advantage claim: this 4-bit instance is exactly enumerable classically.")


def main():
    print("CarbonGuard-Q slack-free experiment | synthetic illustrative data")
    try:
        qollab_backend=backend
    except NameError as exc:
        raise RuntimeError("Run in Qollab with its preconfigured `backend`, or call run_qaoa(your_backend).") from exc
    run_qaoa(qollab_backend)

# if __name__ == "__main__":
#     main()
