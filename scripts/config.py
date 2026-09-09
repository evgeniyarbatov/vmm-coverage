import os
from pathlib import Path

import yaml

DEFAULT_DATA_DIR = "~/Documents/data/vmm-coverage"
DEFAULT_CONFIG_PATH = "config.yaml"


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)).expanduser()
