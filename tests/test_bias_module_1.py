from bias import SimplifiedConfigLoader, SimplifiedBiasGenerator, BiasIO

# 1. Load config
config = SimplifiedConfigLoader.load("./data/bias-config/REAL-FM-7.yaml")

# 2. Validate
result = SimplifiedConfigLoader.validate_config(config)
if not result['valid']:
    print(result['errors'])

# 3. Generate bias
generator = SimplifiedBiasGenerator(config)
bias = generator.generate_bias()

# 4. Save
BiasIO.save_to_json(bias, "./data/bias/REAL-FM-7-bias.json")
BiasIO.save_to_cnf(bias, "./data/bias/REAL-FM-7-bias.cnf")