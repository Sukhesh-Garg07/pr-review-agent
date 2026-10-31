"""Configuration loading helpers."""

import json

DEFAULTS = {"retries": 3, "timeout": 30, "debug": False}


def load_config(path):
    """Load a JSON config file and fill in defaults."""
    with open(path) as fh:
        user = json.load(fh)
    merged = dict(DEFAULTS)
    merged.update(user)
    return merged


def config_summary(config):
    return ", ".join(f"{k}={v}" for k, v in sorted(config.items()))
