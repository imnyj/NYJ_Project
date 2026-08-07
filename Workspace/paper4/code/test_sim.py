from sim_engine import SimulationRunner
runner = SimulationRunner(scenario="urban_grid", n_vehicles=30, seed=42, method="ReactDCC", duration_steps=100)
runner.run()
print(runner.run())
