import pytest
import json
import tempfile
import os
from src.config import load_config, validate_config, _deep_merge


def test_default_config_loads():
    config = load_config()
    assert "source_subvolume" in config
    assert "snapshot_dir" in config
    assert "retention" in config


def test_user_config_overrides_defaults(tmp_path):
    user = {
        "source_subvolume": "/data",
        "snapshot_prefix": "mybackup"
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(user))

    config = load_config(str(cfg_file))
    assert config["source_subvolume"] == "/data"
    assert config["snapshot_prefix"] == "mybackup"
    assert config["snapshot_dir"] is not None


def test_deep_merge_preserves_nested():
    base = {"retention": {"keep_hourly": 24, "keep_daily": 7}}
    override = {"retention": {"keep_hourly": 12}}
    result = _deep_merge(base, override)
    assert result["retention"]["keep_hourly"] == 12
    assert result["retention"]["keep_daily"] == 7


def test_validate_config_raises_on_missing_host():
    config = {
        "source_subvolume": "/",
        "snapshot_dir": "/mnt/snaps",
        "transfer": {"enabled": True},
        "remote": {"host": "", "user": "backup"}
    }
    with pytest.raises(ValueError, match="remote.host"):
        validate_config(config)


def test_validate_config_passes_when_transfer_disabled():
    config = {
        "source_subvolume": "/",
        "snapshot_dir": "/mnt/snaps",
        "transfer": {"enabled": False},
        "remote": {"host": "", "user": ""}
    }
    assert validate_config(config) is True
