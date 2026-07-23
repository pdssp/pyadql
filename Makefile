.DEFAULT_GOAL := init
.PHONY: init prepare-dev install-dev tests coverage coverage_xml lint tox doc doc-pdf visu-doc-pdf visu-doc release version \
        add_major_version add_minor_version add_patch_version \
        add_premajor_alpha_version add_preminor_alpha_version add_prepatch_alpha_version \
        add_premajor_beta_version add_preminor_beta_version add_prepatch_beta_version \
        add_premajor_dev_version add_preminor_dev_version add_prepatch_dev_version \
        add_prerelease_version add_stable_version \
        add_req_prod add_req_dev \
        check_update update_latest_dev update_latest_main show_deps_main show_deps_dev show_obsolete \
        pyclean licences help

CURRENT_VERSION := $(shell grep 'version = ' pyproject.toml | cut -d '"' -f 2)
UV_INDEX_URL := "https://${PDSSP_PROD_USERNAME}:${PDSSP_PROD_TOKEN}@${UL_ARTIFACTORY_HOST}/artifactory/api/pypi/pypi/simple"
UV_INDEX_EXTRA_URL := "${ARTIFACTORY_REPO_URL}"

define PROJECT_HELP_MSG

Usage:\n
	\n
    make help\t\t\t             show this message\n
	\n
	-------------------------------------------------------------------------\n
	\t\tInstallation\n
	-------------------------------------------------------------------------\n
	make\t\t\t\t                Install production dependencies\n
	make prepare-dev\t\t 		Prepare Development environment\n
	make install-dev\t\t 		Install all dependecies\n

	\n
	-------------------------------------------------------------------------\n
	\t\tDevelopment\n
	-------------------------------------------------------------------------\n
	make tests\t\t\t            Run units and integration tests\n
	make coverage\t\t\t 		Coverage\n
	make coverage_xml\t\t   	Coverage\n
	make lint\t\t\t				Lint\n
	make tox\t\t\t 				Run all tests\n

	\n
	-------------------------------------------------------------------------\n
	\t\tDocumentation\n
	-------------------------------------------------------------------------\n
	make doc\t\t\t 				Generate the documentation\n
	make doc-pdf\t\t\t 			Generate the documentation as PDF\n
	make visu-doc-pdf\t\t 		View the generated PDF\n
	make visu-doc\t\t\t			View the generated documentation\n

	\n
	-------------------------------------------------------------------------\n
	\t\tVersion Management\n
	-------------------------------------------------------------------------\n
    make version\t\t\t		                      Display current version\n
    make add_major_version\t\t                    Bump major version\n
    make add_minor_version\t\t                    Bump minor version\n
    make add_patch_version\t\t                    Bump patch version\n
    make add_premajor_alpha_version               Bump to pre-major alpha version\n
    make add_preminor_alpha_version               Bump to pre-minor alpha version\n
    make add_prepatch_alpha_version               Bump to pre-patch alpha version\n
    make add_premajor_beta_version\t              Bump to pre-major beta version\n
    make add_preminor_beta_version\t              Bump to pre-minor beta version\n
    make add_prepatch_beta_version\t              Bump to pre-patch beta version\n
    make add_premajor_dev_version\t               Bump to pre-major dev version\n
    make add_preminor_dev_version\t               Bump to pre-minor dev version\n
    make add_prepatch_dev_version\t               Bump to pre-patch dev version\n
    make add_prerelease_minor_version\t           Bump to minor release candidate version\n
	make add_prerelease_major_version\t           Bump to major release candidate version\n
    make add_stable_version\t                     Bump to stable version\n
	make release\t\t\t 							  Release the package as tar.gz\n
	\n
	-------------------------------------------------------------------------\n
	\t\tDependencies\n
	-------------------------------------------------------------------------\n
	make add_req_prod pkg=<name>\t Add the package in the dependencies of .toml\n
	make add_req_dev pkg=<name>\t Add the package in the DEV dependencies of .toml\n
	make check_update\t\t 		Check the COTS update\n
	make update_latest_dev\t\t	Update to the latest version for development\n
	make update_latest_main\t 	Update to the latest version for production\n
	make show_deps_main\t\t 	Show main COTS for production\n
	make show_deps_dev\t\t 		Show main COTS for development\n
	make show_obsolete\t\t		Show obsolete COTS\n
	\n
	-------------------------------------------------------------------------\n
	\t\tMaintenance (use make install-dev before using these tasks)\n
	-------------------------------------------------------------------------\n
	make pyclean\t\t\t			Clean .pyc and __pycache__ files\n
    make licences\t\t\t           Display licenses of dependencies\n
	\n

endef
export PROJECT_HELP_MSG


#Show help
#---------
help:
	echo $$PROJECT_HELP_MSG


################################################################################
# INSTALLATION
################################################################################

init:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom index URL: ${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		uv sync --no-dev --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		echo "Using default index"; \
		uv sync --no-dev; \
	fi


################################################################################
# DEVELOPMENT ENVIRONMENT
################################################################################

prepare-dev:
	git config --global init.defaultBranch main
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom CA certificate: $$CNES_CERTIFICATE"; \
		git config --global http.sslCAInfo "$$CNES_CERTIFICATE"; \
	else \
		echo "No CNES certificate set"; \
	fi
	git init
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom index URL: ${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		uv venv --seed .venv --prompt pyadql --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		echo "Using default index"; \
		uv venv --seed .venv --prompt pyadql; \
	fi

install-dev:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using SSL certificate: $$CNES_CERTIFICATE"; \
		export SSL_CERT_FILE="$$CNES_CERTIFICATE"; \
		export GIT_SSL_CAINFO="$$CNES_CERTIFICATE"; \
	else \
		echo "No CNES certificate set"; \
	fi

	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom index URL: ${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		uv sync --all-groups --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		echo "Using default index"; \
		uv sync --all-groups; \
	fi
	uv run pre-commit install
	uv run pre-commit autoupdate



################################################################################
# TESTING / LINT / COVERAGE
################################################################################

tests:
	uv run pytest -s -vv --log-cli-level=INFO

coverage:
	uv run coverage erase
	uv run coverage run -m pytest
	uv run coverage report -m

coverage_xml:
	uv run coverage xml

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .

tox:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		export CNES_CERTIFICATE="${CNES_CERTIFICATE}"; \
		export PDSSP_PROD_USERNAME="${PDSSP_PROD_USERNAME}"; \
		export PDSSP_PROD_TOKEN="${PDSSP_PROD_TOKEN}"; \
		export UL_ARTIFACTORY_HOST="${UL_ARTIFACTORY_HOST}"; \
		uv run tox -c tox.private.ini; \
	else \
		uv run tox -c tox.public.ini; \
	fi


################################################################################
# DOCUMENTATION
################################################################################

doc:
	make licences
	rm -rf docs/source/_static/coverage
	uv run pytest --html=docs/report.html
	uv run coverage erase
	uv run coverage run -m pytest
	uv run coverage html -d docs/_static/coverage
	PYTHONPATH=. uv run mkdocs build

doc-pdf:
	make licences
	rm -rf docs/source/_static/coverage
	uv run pytest --html=docs/report.html
	uv run coverage erase
	uv run coverage run -m pytest
	uv run coverage html -d docs/_static/coverage
	PYTHONPATH=. uv run mkdocs build

visu-doc-pdf:
	xdg-open site/docs/*.pdf

visu-doc:
	PYTHONPATH=. uv run mkdocs serve


################################################################################
# VERSION / RELEASE
################################################################################

release:
	uv build

version:
	uv version

add_major_version:
	uv version --bump major

add_minor_version:
	uv version --bump minor

add_patch_version:
	uv version --bump patch

# --------------------------
# Pré-versions (alpha)
# --------------------------

define add_alpha_preversion
	@if echo "$(CURRENT_VERSION)" | grep -q "a"; then \
		uv version --bump alpha; \
	else \
		uv version --bump $(1) --bump alpha; \
	fi
endef

add_premajor_alpha_version:
	$(call add_alpha_preversion,major)

add_preminor_alpha_version:
	$(call add_alpha_preversion,minor)

add_prepatch_alpha_version:
	$(call add_alpha_preversion,patch)

# --------------------------
# Pré-versions (beta)
# --------------------------

define add_beta_preversion
	@if echo "$(CURRENT_VERSION)" | grep -q "b"; then \
		uv version --bump beta; \
	else \
		uv version --bump $(1) --bump beta; \
	fi
endef

add_premajor_beta_version:
	$(call add_beta_preversion,major)
add_preminor_beta_version:
	$(call add_beta_preversion,minor)
add_prepatch_beta_version:
	$(call add_beta_preversion,patch)

# --------------------------
# Pré-versions (dev)
# --------------------------

define add_dev_preversion
	@if echo "$(CURRENT_VERSION)" | grep -q "dev"; then \
		uv version --bump dev; \
	else \
		uv version --bump $(1) --bump dev; \
	fi
endef

add_premajor_dev_version:
	$(call add_dev_preversion,major)
add_preminor_dev_version:
	$(call add_dev_preversion,minor)
add_prepatch_dev_version:
	$(call add_dev_preversion,patch)


# --------------------------
# Pré-versions (RC et stable)
# --------------------------
add_prerelease_minor_version:
	uv version --bump minor --bump rc

add_prerelease_major_version:
	uv version --bump major --bump rc

add_stable_version:
	uv version --bump stable


################################################################################
# DEPENDENCIES
################################################################################

add_req_prod:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom index URL: ${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		uv add --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}" --bounds=exact "$(pkg)"; \
	else \
		echo "Using default index"; \
		uv add --bounds=exact "$(pkg)"; \
	fi

add_req_dev:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom index URL: ${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		uv add --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}" --group dev --bounds=exact "$(pkg)"; \
	else \
		echo "Using default index"; \
		uv add --group dev --bounds=exact "$(pkg)"; \
	fi

licences:
	uv run python scripts/license.py

check_update:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		echo "Using custom index URL: ${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		pip list --outdated --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		echo "Using default index"; \
		pip list --outdated; \
	fi

update_latest_dev:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		uv lock --upgrade --index-url "${UV_INDEX_URL} and ${UV_INDEX_EXTRA_URL}"; \
		uv sync --group dev --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		uv lock --upgrade; \
		uv sync --group dev; \
	fi


update_latest_main:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		uv lock --upgrade --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
		uv sync --no-dev --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		uv lock --upgrade; \
		uv sync --no-dev; \
	fi


show_deps_main:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		uv tree --depth 1 --no-dev --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		uv tree --depth 1 --no-dev; \
	fi

show_deps_dev:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		uv tree --depth 1 --group dev --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		uv tree --depth 1 --group dev; \
	fi

show_obsolete:
	@if [ -n "$$CNES_CERTIFICATE" ]; then \
		uv tree --depth 1 --outdated --index-url "${UV_INDEX_URL}" --extra-index-url "${UV_INDEX_EXTRA_URL}"; \
	else \
		uv tree --depth 1 --outdated; \
	fi


################################################################################
# CLEAN
################################################################################

pyclean:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
