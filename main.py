"""CarbonGuard-Q: carbon-aware, scenario-robust supply-chain recovery.

Qollab entry point: this script expects Qollab to provide a preconfigured
Qiskit-compatible `backend` object. It never creates credentials or selects a
provider. All input data are synthetic and intended for a small demonstration.
"""
from itertools import product
from math import isclose


# --------------------------- Synthetic problem data ------------------------
# x1: activate regional alternative supplier
# x2: shift production to backup plant
# x3: use lower-carbon ground freight
# x4: use air-freight expediting
# s0,s1,s2: binary slack for recovered_capacity - 4
N_DECISIONS = 4
N_BITS = 7
CAPACITY = (3, 3, 2, 2)
COST = (5.0, 6.0, 3.0, 7.0)  # cost units: $100 each
NORMAL_EMISSIONS = (4.0, 3.0, 1.0, 8.0)  # emissions units: 100 kg CO2e
SHOCK_EMISSIONS = (5.0, 7.0, 2.0, 10.0)
NORMAL_WEIGHT = 0.60
SHOCK_WEIGHT = 0.40
CARBON_WEIGHT = 0.50
PENALTY = 50.0
SHOTS = 2048
GAMMA = 0.02
BETA = 0.35

ACTION_NAMES = (
    "regional alternative supplier",
    "backup plant",
    "lower-carbon ground freight",
    "air-freight expediting",
)


def expected_emissions(x):
    """Expected emissions in 100 kg CO2e units under the two toy scenarios."""
    return sum(
        x[i] * (NORMAL_WEIGHT * NORMAL_EMISSIONS[i]
                + SHOCK_WEIGHT * SHOCK_EMISSIONS[i])
        for i in range(N_DECISIONS)
    )


def objective(x):
    """Unpenalized objective: cost units + weighted expected emissions units."""
    total_cost = sum(x[i] * COST[i] for i in range(N_DECISIONS))
    return total_cost + CARBON_WEIGHT * expected_emissions(x)


def capacity_of(x):
    return sum(x[i] * CAPACITY[i] for i in range(N_DECISIONS))


def operationally_feasible(x):
    return (
        sum(x) == 2
        and capacity_of(x) >= 4
        and not (x[2] and x[3])
    )


def direct_qubo_energy(bits):
    """Evaluate the penalized QUBO directly from its defining constraints."""
    x = tuple(bits[:N_DECISIONS])
    s0, s1, s2 = bits[4:]
    slack = s0 + 2 * s1 + 4 * s2
    service_residual = capacity_of(x) - 4 - slack
    return (
        objective(x)
        + PENALTY * (sum(x) - 2) ** 2
        + PENALTY * service_residual ** 2
        + PENALTY * x[2] * x[3]
    )


# ------------------------- Build polynomial QUBO ---------------------------
# Q(x) = constant + sum_i a_i*x_i + sum_(i<j) b_ij*x_i*x_j.
# Indices 0..3 are operational decisions; 4..6 are slack bits.

def build_qubo():
    constant = 0.0
    linear = [0.0] * N_BITS
    quadratic = {}

    for i in range(N_DECISIONS):
        linear[i] += COST[i] + CARBON_WEIGHT * (
            NORMAL_WEIGHT * NORMAL_EMISSIONS[i]
            + SHOCK_WEIGHT * SHOCK_EMISSIONS[i]
        )

    def add_pair(i, j, value):
        if i == j:
            # x_i^2 = x_i for binary variables.
            linear[i] += value
        else:
            key = (min(i, j), max(i, j))
            quadratic[key] = quadratic.get(key, 0.0) + value

    def add_square_of_linear_form(offset, coefficients, penalty):
        """Add penalty*(offset + sum_i coefficients[i]*x_i)^2."""
        nonlocal constant
        constant += penalty * offset * offset
        active = [(i, a) for i, a in enumerate(coefficients) if a != 0]
        for i, a in active:
            linear[i] += penalty * (a * a + 2 * offset * a)
        for pos, (i, a) in enumerate(active):
            for j, b in active[pos + 1:]:
                add_pair(i, j, penalty * 2 * a * b)

    # Exactly two recovery actions: (sum x_i - 2)^2.
    count_coefficients = [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
    add_square_of_linear_form(-2.0, count_coefficients, PENALTY)

    # Capacity >= 4, represented as capacity - 4 - (s0 + 2*s1 + 4*s2) = 0.
    service_coefficients = [3.0, 3.0, 2.0, 2.0, -1.0, -2.0, -4.0]
    add_square_of_linear_form(-4.0, service_coefficients, PENALTY)

    # Ground freight and air expediting are mutually exclusive.
    add_pair(2, 3, PENALTY)

    return constant, linear, quadratic


Q_CONST, Q_LINEAR, Q_QUADRATIC = build_qubo()


def coefficient_qubo_energy(bits):
    energy = Q_CONST + sum(Q_LINEAR[i] * bits[i] for i in range(N_BITS))
    energy += sum(value * bits[i] * bits[j]
                  for (i, j), value in Q_QUADRATIC.items())
    return energy


# --------------------- QUBO -> Ising conversion ----------------------------
# x_i = (1 - Z_i)/2, so E = offset + sum_i h_i Z_i + sum_ij J_ij Z_i Z_j.
# Circuit phases use RZ(2*gamma*h_i) and RZZ(2*gamma*J_ij).

def qubo_to_ising(constant, linear, quadratic):
    offset = constant + sum(a / 2.0 for a in linear)
    h = [-a / 2.0 for a in linear]
    J = {}
    for (i, j), b in quadratic.items():
        offset += b / 4.0
        h[i] -= b / 4.0
        h[j] -= b / 4.0
        J[(i, j)] = b / 4.0
    return offset, h, J


ISING_OFFSET, ISING_H, ISING_J = qubo_to_ising(
    Q_CONST, Q_LINEAR, Q_QUADRATIC
)


def ising_energy(bits):
    z = [1 - 2 * bit for bit in bits]
    energy = ISING_OFFSET + sum(ISING_H[i] * z[i] for i in range(N_BITS))
    energy += sum(value * z[i] * z[j]
                  for (i, j), value in ISING_J.items())
    return energy


def verify_formulations():
    """Check direct QUBO, expanded polynomial and Ising energies on 128 states."""
    for bits in product((0, 1), repeat=N_BITS):
        direct = direct_qubo_energy(bits)
        expanded = coefficient_qubo_energy(bits)
        ising = ising_energy(bits)
        if not (isclose(direct, expanded, abs_tol=1e-7)
                and isclose(direct, ising, abs_tol=1e-7)):
            raise AssertionError(
                f"Energy mismatch at {bits}: direct={direct}, "
                f"expanded={expanded}, Ising={ising}"
            )
    return 2 ** N_BITS


# ------------------------ Exact classical baseline -------------------------
def exact_baseline():
    feasible = []
    for x in product((0, 1), repeat=N_DECISIONS):
        if operationally_feasible(x):
            feasible.append({
                "x": x,
                "capacity": capacity_of(x),
                "cost": sum(x[i] * COST[i] for i in range(N_DECISIONS)),
                "normal_emissions": sum(
                    x[i] * NORMAL_EMISSIONS[i] for i in range(N_DECISIONS)
                ),
                "shock_emissions": sum(
                    x[i] * SHOCK_EMISSIONS[i] for i in range(N_DECISIONS)
                ),
                "expected_emissions": expected_emissions(x),
                "objective": objective(x),
            })
    feasible.sort(key=lambda row: row["objective"])
    if not feasible:
        raise RuntimeError("No feasible operational plan exists.")
    return feasible


def exact_qubo_baseline():
    states = list(product((0, 1), repeat=N_BITS))
    best = min(states, key=direct_qubo_energy)
    return len(states), best, direct_qubo_energy(best)


# ---------------------------- QAOA circuit ---------------------------------
def build_qaoa_circuit(gamma=GAMMA, beta=BETA):
    """Build a one-layer QAOA circuit; Qollab supplies the backend separately."""
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:
        raise RuntimeError("Qiskit is available in the Qollab runtime but is not installed in this local Python environment.") from exc
    qc = QuantumCircuit(N_BITS, N_BITS)
    qc.h(range(N_BITS))

    # Cost unitary exp(-i*gamma*H_C); global Ising offset is irrelevant to counts.
    for i, h_i in enumerate(ISING_H):
        if abs(h_i) > 1e-12:
            qc.rz(2.0 * gamma * h_i, i)
    for (i, j), coupling in ISING_J.items():
        if abs(coupling) > 1e-12:
            qc.rzz(2.0 * gamma * coupling, i, j)

    # Standard X mixer.
    for i in range(N_BITS):
        qc.rx(2.0 * beta, i)

    qc.measure(range(N_BITS), range(N_BITS))
    return qc


def decode_count_key(bitstring):
    """Qiskit displays classical bit c6..c0; reverse to recover q0..q6 order."""
    compact = bitstring.replace(" ", "")
    return tuple(int(bit) for bit in compact[::-1])


def state_is_feasible(bits):
    x = tuple(bits[:N_DECISIONS])
    s0, s1, s2 = bits[4:]
    slack = s0 + 2 * s1 + 4 * s2
    return (
        operationally_feasible(x)
        and capacity_of(x) - 4 == slack
    )


def print_classical_baseline(plans):
    print("\n=== EXACT CLASSICAL BASELINE (16 action combinations) ===")
    print("Feasible plans:", len(plans))
    print("Plan | capacity | cost units | normal emissions | shock emissions | objective")
    labels = "ABCD"
    for row in plans:
        plan_name = "".join(labels[i] for i, bit in enumerate(row["x"]) if bit)
        print(
            f"{plan_name:>4} | {row['capacity']:>8} | {row['cost']:>10.1f} | "
            f"{row['normal_emissions']:>16.1f} | {row['shock_emissions']:>15.1f} | "
            f"{row['objective']:>9.2f}"
        )
    best = plans[0]
    print("Best plan:", best["x"], "objective:", f"{best['objective']:.2f}")
    return best


def run_qaoa(backend):
    plans = exact_baseline()
    classical_best = print_classical_baseline(plans)

    n_states = verify_formulations()
    print(f"\nQUBO/Ising verification passed for all {n_states} bitstrings.")
    n_qubo_states, best_bits, best_energy = exact_qubo_baseline()
    print(f"Exact 7-bit QUBO minimum: {best_bits}, energy={best_energy:.2f}")
    if tuple(best_bits[:N_DECISIONS]) != tuple(classical_best["x"]):
        raise AssertionError("QUBO optimum does not match the exact classical baseline.")

    circuit = build_qaoa_circuit()
    print(f"\nSubmitting p=1 QAOA circuit: {N_BITS} qubits, {SHOTS} shots.")
    print(f"Fixed illustrative parameters: gamma={GAMMA}, beta={BETA}.")
    result = backend.run(circuit, shots=SHOTS).result()
    counts = result.get_counts()

    total_shots = sum(counts.values())
    feasible_shots = 0
    optimal_shots = 0
    best_sampled = None
    best_sampled_bits = None
    # Compute metrics over every observed bitstring, not just the displayed top ten.
    for bitstring, count in counts.items():
        bits = decode_count_key(bitstring)
        x = tuple(bits[:N_DECISIONS])
        if state_is_feasible(bits):
            feasible_shots += count
            if x == tuple(classical_best["x"]):
                optimal_shots += count
            value = objective(x)
            if best_sampled is None or value < best_sampled:
                best_sampled = value
                best_sampled_bits = bits

    print("\n=== TOP MEASURED BITSTRINGS ===")
    for bitstring, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]:
        bits = decode_count_key(bitstring)
        x = tuple(bits[:N_DECISIONS])
        print(
            f"{bitstring}: count={count}, QUBO={direct_qubo_energy(bits):.2f}, "
            f"feasible={state_is_feasible(bits)}, actions={x}"
        )

    print("\n=== QAOA VS EXACT BASELINE ===")
    print(f"Total shots: {total_shots}")
    print(f"Feasible-shot rate: {feasible_shots / total_shots:.1%}")
    print(f"Optimal-action-plan frequency: {optimal_shots / total_shots:.1%}")
    if best_sampled is None:
        print("No feasible measured state was sampled. Try different QAOA parameters or more shots.")
    else:
        print("Best feasible sampled state:", best_sampled_bits)
        print(f"Best feasible sampled objective: {best_sampled:.2f}")
        print(f"Exact classical optimum: {classical_best['objective']:.2f}")
        print(f"Objective gap: {best_sampled - classical_best['objective']:.2f}")

    print("\nInterpretation: this tiny instance is exactly solvable classically. "
          "These results test the QAOA workflow; they do not demonstrate quantum advantage.")


def main():
    print("CarbonGuard-Q | synthetic scenario-aware recovery prototype")
    print("Cost unit = $100; emissions unit = 100 kg CO2e; illustrative data only.")
    # The Qollab runtime is expected to inject a configured `backend` variable.
    try:
        qollab_backend = backend  # noqa: F821 - provided by the Qollab environment
    except NameError as exc:
        raise RuntimeError(
            "No Qollab `backend` was found. Run this script in a Qollab project "
            "with its preconfigured backend, or call run_qaoa(your_backend) locally."
        ) from exc
    run_qaoa(qollab_backend)


if __name__ == "__main__":
    main()
