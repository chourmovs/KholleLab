from pathlib import Path


def test_production_compose_uses_image_content_corpus():
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text()
    assert "./problems:/problems" not in compose
    assert "./resources:/resources" not in compose


def test_worker_has_real_healthcheck_and_distinct_log_role():
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text()
    assert '["CMD", "python", "-m", "app.worker_healthcheck"]' in compose
    assert "LOG_PROCESS_ROLE: api" in compose
    assert "LOG_PROCESS_ROLE: worker" in compose


def test_backend_and_frontend_images_publish_health_metadata():
    root=Path(__file__).resolve().parents[2]
    assert "HEALTHCHECK" in (root/"backend/Dockerfile").read_text()
    assert "HEALTHCHECK" in (root/"frontend/Dockerfile").read_text()
