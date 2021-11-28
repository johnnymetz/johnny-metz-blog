.DEFAULT_GOAL = shell

setup:
	pre-commit install

updateprecommit:
	pre-commit autoupdate
	pre-commit run --all-files

# BACKEND

shell:
	docker compose run api bash

pyshell:
	docker compose run api ./manage.py shell_plus

pytest:
	docker compose run api pytest

logs:
	docker compose logs -f --no-log-prefix api

migratedb:
	docker compose run api ./manage.py migrate

seeddb:
	docker compose run api ./manage.py shell < choices/seed_db.py

pipcompile:
	docker compose run api pip-compile

pipcompileupgrade:
	docker compose run api pip-compile --upgrade

clear-silk:
	docker compose run api ./manage.py silk_clear_request_log
