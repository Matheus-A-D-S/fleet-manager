.PHONY: up down seed simulate test lint format migrations logs prod-up

up:
	docker compose up --build
down:
	docker compose down
seed:
	docker compose exec backend python manage.py seed_demo
simulate:
	docker compose exec backend python manage.py simulate_gps --speeding
test:
	docker compose exec backend pytest --cov --cov-report=term-missing
lint:
	docker compose exec backend ruff check .
format:
	docker compose exec backend ruff format .
migrations:
	docker compose exec backend python manage.py makemigrations accounts fleet logistics alerts audit
logs:
	docker compose logs -f backend worker
prod-up:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
