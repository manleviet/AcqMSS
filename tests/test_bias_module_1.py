from acqmss.bias import ConfigLoader, BiasGenerator, BiasIO

# 1. Load config
config = ConfigLoader.load("./data/bias-config/REAL-FM-7.yaml")

# 2. Validate
result = ConfigLoader.validate_config(config)
if not result['valid']:
    print(result['errors'])

# 3. Generate bias
generator = BiasGenerator(config)
bias = generator.generate_bias()

# 4. Save
BiasIO.save_to_json(bias, "./data/bias/REAL-FM-7-bias.json")
BiasIO.save_to_cnf(bias, "./data/bias/REAL-FM-7-bias.cnf")