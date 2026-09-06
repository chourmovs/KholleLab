import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("RESOURCES_DIR", str(Path(__file__).resolve().parents[2] / "resources"))
