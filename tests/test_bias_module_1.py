from pathlib import Path

from acqmss.bias import BiasConfigLoader, BiasGenerator, BiasIO

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
BIAS_CONFIG_PATH = DATA_DIR / "bias-config" / "REAL-FM-7.yaml"
BIAS_JSON_PATH = OUTPUT_DIR / "REAL-FM-7-bias.json"
BIAS_CNF_PATH = OUTPUT_DIR / "REAL-FM-7-bias.cnf"

# 1. Load config
config = BiasConfigLoader.load(str(BIAS_CONFIG_PATH))

# 2. Validate
result = BiasConfigLoader.validate_config(config)
if not result['valid']:
    print(result['errors'])

# 3. Generate bias
generator = BiasGenerator(config)
bias = generator.generate_bias()

# create output directories if they don't exist
BIAS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

# 4. Save
BiasIO.save_to_json(bias, str(BIAS_JSON_PATH))
BiasIO.save_to_cnf(bias, str(BIAS_CNF_PATH))