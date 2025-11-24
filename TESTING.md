# Running Tests for ckanext-udc

This document explains how to run the automated tests for `ckanext-udc`, either in an existing CKAN development environment or via the provided Docker Compose stack.

## Prerequisites
> Follow the instructions in [DEV.md](./DEV.md) to set up a CKAN development environment if you don't have one already.
- A CKAN 2.11 (or newer) source checkout available at `/usr/lib/ckan/default/src/ckan` or another working tree referenced from `test.ini`.
- Python virtual environment used by CKAN activated (`. /usr/lib/ckan/default/bin/activate`).
- This extension installed in editable mode (`pip install -e .`) and development dependencies installed (`pip install -r requirements.txt -r dev-requirements.txt`).
- PostgreSQL, Solr, and Redis instances configured the same way as the CKAN development environment (or started via Docker as described below).

## Local host workflow
1. Activate the CKAN virtualenv and change into the extension root:
   ```bash
   . /usr/lib/ckan/default/bin/activate
   cd /usr/lib/ckan/default/src/ckanext-udc
   ```
2. Ensure the test configuration points at your CKAN source tree (`use = config:../ckan/test-core.ini` by default). Adjust the relative path inside `test.ini` if your layout differs.
3. (First run only) Initialize the test database and extension tables:
   ```bash
   ckan -c test.ini db init
   ckan -c test.ini udc initdb
   ```
4. Run the full test suite:
   ```bash
   pytest --ckan-ini=test.ini --cov=ckanext.udc --disable-warnings ckanext/udc
   ```
5. Run a single test module or test case by appending its dotted path:
   ```bash
   pytest --ckan-ini=test.ini ckanext/udc/tests/test_solr_config.py::test_get_udc_langs_includes_default_and_dedupes
   ```

### Tips
- `pytest-ckan` automatically provisions CKAN fixtures such as `app`, `clean_db`, and `sysadmin`.
- Re-run `ckan -c test.ini udc initdb` whenever migrations for the extension change.
- To speed up local iteration, use `pytest -k <keyword> --maxfail=1 --ff`.

## Docker Compose workflow
The repository ships with `docker-compose.yml` that provisions CKAN + dependencies for development and testing.

1. From the `ckanext-udc` root, bootstrap the environment (installs CKAN, dependencies, and this extension):
   ```bash
   docker compose up ckan-install
   ```
2. Run the test service, which automatically wires `test.ini`, initializes the database, and executes pytest with coverage:
   ```bash
   docker compose run --rm ckan-test
   ```
   The command executed in the container is:
   ```bash
   pytest --ckan-ini=/tmp/test.ini.<XXXX> --cov=ckanext.udc --disable-warnings ckanext/udc
   ```
3. Inspect `.coverage` artifacts under `/tmp/.coverage` inside the container or mount a host volume if you need HTML reports.

### Troubleshooting
- If tests fail because Solr or the database is unavailable, ensure the dependent containers (`db`, `solr`, `redis`) are healthy: `docker compose ps`.
- To rebuild dependencies after updating `requirements.txt`, remove the `.venv` directory mounted into the container or run `docker compose run --rm ckan-install` again.
- When running locally, confirm `CKAN_SQLALCHEMY_URL`, `CKAN_SOLR_URL`, and related settings in `test.ini` match your services.

## Continuous Integration parity
GitHub Actions (`.github/workflows/test.yml`) runs the same command used above. Keeping local runs aligned with CI ensures deterministic failures:
```bash
pytest --ckan-ini=test.ini --cov=ckanext.udc --disable-warnings ckanext/udc
```
