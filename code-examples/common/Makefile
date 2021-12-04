.DEFAULT_GOAL = shell

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

makemigrations:
	docker compose run api ./manage.py makemigrations

migratedb:
	docker compose run api ./manage.py migrate

pipcompile:
	docker compose run api pip-compile

pipcompileupgrade:
	docker compose run api pip-compile --upgrade
