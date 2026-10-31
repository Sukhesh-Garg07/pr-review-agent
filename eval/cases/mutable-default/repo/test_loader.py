import json

from loader import load_config


def test_load_config_fills_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"timeout": 5}))
    config = load_config(str(path))
    assert config["timeout"] == 5
    assert config["retries"] == 3
