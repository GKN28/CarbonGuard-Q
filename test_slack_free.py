import slack_free as sf

assert sf.verify_diagonal_expansion() == 16
count, best, energy = sf.exact_custom_baseline()
assert count == 16
assert best == (1,0,1,0)
assert abs(energy - 11.1) < 1e-8
plans=sf.exact_baseline()
assert len(plans)==5
assert plans[0]["x"]==(1,0,1,0)
# Check each supported risk objective and its exact optimum.
for mode in ("expected", "worst_case", "interval_robust"):
    mode_plans=sf.exact_baseline(mode=mode)
    assert len(mode_plans)==5
    assert mode_plans[0]["x"]==(1,0,1,0), (mode, mode_plans[0])
    coeffs=sf.pauli_z_coefficients(lambda x, m=mode: sf.custom_energy(x, mode=m))
    for x in sf.all_states():
        assert abs(sf.custom_energy(x, mode=mode)-sf.pauli_energy(x, coeffs)) < 1e-8
# Every infeasible state gets the custom step penalty; every feasible state does not.
for x in sf.all_states():
    if sf.feasible(x):
        assert abs(sf.custom_energy(x)-sf.objective(x, mode=sf.OBJECTIVE_MODE)) < 1e-9
    else:
        assert sf.custom_energy(x) >= sf.PENALTY
print("PASS: all 16 states match the Pauli-Z expansion for expected, worst-case, and interval-robust objectives; exact optima verified.")
