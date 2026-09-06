from pathlib import Path


def test_production_compose_uses_image_content_corpus():
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text()
    assert "./problems:/problems" not in compose
    assert "./resources:/resources" not in compose
