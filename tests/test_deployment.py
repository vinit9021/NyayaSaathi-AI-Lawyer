from pathlib import Path

import pytest


pytestmark = pytest.mark.offline
ROOT = Path(__file__).resolve().parents[1]


def test_container_and_space_metadata_are_production_ready():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    metadata = (ROOT / "deployment" / "README.md").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "COPY sources ./sources" in dockerfile
    assert "GEMINI_API_KEY" not in dockerfile
    assert "GROQ_API_KEY" not in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "--server.port=7860" in dockerfile
    assert "sdk: docker" in metadata
    assert "app_port: 7860" in metadata
    assert "sources/catalogue.json" in metadata
    assert ".env" in dockerignore
    assert "credentials/" in dockerignore
    assert ".venv/" in dockerignore
    assert "evaluation/raw_outputs/" in dockerignore
    assert "app.py.backup" in dockerignore


def test_required_runtime_catalogue_files_are_not_ignored():
    catalogue = ROOT / "sources" / "catalogue.json"
    source_readme = ROOT / "sources" / "README.md"
    assert catalogue.is_file() and catalogue.stat().st_size > 0
    assert source_readme.is_file()
    assert "sources/" not in (ROOT / ".dockerignore").read_text(encoding="utf-8")
