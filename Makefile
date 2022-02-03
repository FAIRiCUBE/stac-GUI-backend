# build is docker-compose build
all:
	docker-compose run open-science-catalog-backend bash -c "pytest && flake8 && mypy ."

build:
	docker-compose build

test:
	docker-compose run open-science-catalog-backend pytest -s

test-watch:
	docker-compose run open-science-catalog-backend ptw

lint:
	docker-compose run open-science-catalog-backend bash -c "flake8 && mypy ."

lint-watch:
	docker-compose run open-science-catalog-backend bash -c "watch -n1  bash -c \"flake8 && mypy .\""

upgrade-packages:
	docker-compose run --user 0 open-science-catalog-backend bash -c "python3 -m pip install pip-upgrader && pip-upgrade --skip-package-installation"

bash:
	docker-compose run --user `id -u` open-science-catalog-backend bash
