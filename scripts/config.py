import os
from pathlib import Path

import yaml

DEFAULT_DATA_DIR = "~/Documents/data/vmm-coverage"
DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_ENV_PATH = ".env"


def load_env(path: str = DEFAULT_ENV_PATH) -> None:
    """Load KEY=VALUE lines from .env into os.environ. Real env vars always win."""
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)).expanduser()
