"""Validation for configuration dictionaries."""

REQUIRED_KEYS = {"retries", "timeout"}


def validate_config(config):
    missing = REQUIRED_KEYS - set(config)
    if missing:
        raise ValueError(f"missing config keys: {sorted(missing)}")
    if config["retries"] < 0:
        raise ValueError("retries must be non-negative")
    return True
