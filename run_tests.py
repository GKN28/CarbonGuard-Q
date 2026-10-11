from itertools import product
import main

assert main.verify_formulations() == 128
plans = main.exact_baseline()
assert len(plans) == 5
assert plans[0]["x"] == (1, 0, 1, 0)
assert abs(plans[0]["objective"] - 10.9) < 1e-9
count, bits, energy = main.exact_qubo_baseline()
assert count == 128
assert bits == (1, 0, 1, 0, 1, 0, 0)
assert abs(energy - 10.9) < 1e-9
assert len(list(product((0, 1), repeat=4))) == 16
print("PASS: QUBO and Ising energies match on 128 states; exact optimum verified.")
