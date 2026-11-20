"""Loads config.toml from the project folder."""

import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_DIR / "config.toml"
MODELS_DIR = PROJECT_DIR / "models"
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def load():
    with open(CONFIG_FILE, "rb") as f:
        config = tomllib.load(f)
    folder = Path(config["sessions"]["folder"]).expanduser()
    config["sessions"]["folder"] = folder if folder.is_absolute() else PROJECT_DIR / folder
    return config
