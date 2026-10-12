"""Streamlit demo for CarbonGuard-Q. Synthetic data; no quantum advantage claim."""
import streamlit as st
from qiskit_aer import AerSimulator
import slack_free as sf

st.set_page_config(page_title="CarbonGuard-Q", page_icon="🌿", layout="wide")
st.title("🌿 CarbonGuard-Q")
st.subheader("Carbon-aware, scenario-robust supply-chain recovery")
st.write("Choose two recovery actions while balancing scaled cost and emissions. All data are synthetic and illustrative.")

mode = st.selectbox(
    "Risk objective",
    ["interval_robust", "expected", "worst_case"],
    format_func=lambda v: {
        "interval_robust": "Interval robust (shock probability 20%–60%)",
        "expected": "Expected value (nominal 60% normal / 40% shock)",
        "worst_case": "Worst-case emissions scenario",
    }[v],
)
shots = st.slider("QAOA simulator shots", min_value=256, max_value=8192, value=2048, step=256)

names = ["Regional alternative supplier", "Backup plant", "Lower-carbon ground freight", "Air-freight expediting"]

if st.button("Run QAOA simulation", type="primary"):
    with st.spinner("Building and simulating the QAOA circuit..."):
        sf.OBJECTIVE_MODE = mode
        sf.COEFFS = sf.pauli_z_coefficients(lambda x: sf.custom_energy(x, mode=mode))
        circuit = sf.build_qaoa_circuit()
        backend = AerSimulator()
        result = backend.run(circuit, shots=shots).result()
        counts = result.get_counts()
        plans = sf.exact_baseline(mode=mode)
        exact = plans[0]
        total = sum(counts.values())
        feasible_shots = 0
        optimal_shots = 0
        best_sample = None
        best_objective = None
        for key, count in counts.items():
            x = sf.decode_count_key(key)
            if sf.feasible(x):
                feasible_shots += count
                if x == exact["x"]:
                    optimal_shots += count
                value = sf.objective(x, mode=mode)
                if best_objective is None or value < best_objective:
                    best_objective, best_sample = value, x
        st.session_state["result"] = {
            "mode": mode, "shots": shots, "counts": counts, "exact": exact,
            "total": total, "feasible": feasible_shots, "optimal": optimal_shots,
            "best_sample": best_sample, "best_objective": best_objective,
        }

if "result" in st.session_state:
    r = st.session_state["result"]
    if r["mode"] != mode or r["shots"] != shots:
        st.info("Change your settings and click **Run QAOA simulation** to refresh the results.")
    else:
        exact = r["exact"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Exact classical optimum", f'{exact["objective"]:.2f}')
        c2.metric("Feasible measured shots", f'{r["feasible"] / r["total"]:.1%}')
        c3.metric("Optimal-plan frequency", f'{r["optimal"] / r["total"]:.1%}')
        st.markdown("### Exact classical recommendation")
        selected = [names[i] for i, bit in enumerate(exact["x"]) if bit]
        st.write(" + ".join(selected))
        st.write(f'Capacity: {exact["capacity"]} | Cost: {exact["cost"]} units | Normal emissions: {exact["normal_emissions"]} units | Shock emissions: {exact["shock_emissions"]} units')
        st.markdown("### Most frequent measured bitstrings")
        rows = []
        for bitstring, count in sorted(r["counts"].items(), key=lambda kv: kv[1], reverse=True)[:10]:
            x = sf.decode_count_key(bitstring)
            rows.append({"Bitstring": bitstring, "Shots": count, "Actions": ", ".join(names[i] for i,b in enumerate(x) if b) or "None", "Feasible": sf.feasible(x), "Objective if feasible": round(sf.objective(x, mode=mode), 3) if sf.feasible(x) else "—"})
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("This is a local Qiskit Aer simulation, not a run on IonQ hardware. This small instance is classically enumerable; no quantum advantage is claimed.")
else:
    st.info("Choose a risk objective and click **Run QAOA simulation** to compare QAOA samples with the exact classical baseline.")

st.markdown("---")
st.markdown("**Required attribution:** This effort is supported by Qollab & IonQ.")

