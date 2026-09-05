.PHONY: test validate-corpus build smoke
test:
	cd backend && pytest -q
	cd frontend && npm test
validate-corpus:
	python scripts/validate_problems.py
build:
	docker compose build
smoke:
	docker compose up -d --wait
	docker compose exec -T backend python - < scripts/smoke.py; status=$$?; docker compose down -v; exit $$status
