import json
from pathlib import Path

import yaml

ROOT = Path.cwd()
CONFIG = ROOT / "config.yaml"
STATE = ROOT / "form_state.json"


def load_config():
    return yaml.safe_load(CONFIG.read_text())


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n")
