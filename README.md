# Observability Platform

End-to-end DevOps project: a containerized order dashboard deployed on Proxmox with Terraform and Ansible, built and released via GitHub Actions, and monitored with Prometheus, Grafana and Loki.

## Overview

The project simulates a client who already runs a small web application in Docker and asks for infrastructure as code, a CI/CD pipeline and monitoring.

The application ("Order desk") is a Flask app backed by PostgreSQL with three tabs:

- **Overview** - open and fulfilled order counts, revenue and the latest orders
- **Orders** - add orders, filter by All / Open / Fulfilled, mark orders as fulfilled
- **About** - app version, host and database information

The app also exposes `/health` for health checks and monitoring.

## Repository structure

| Path | Contents |
|---|---|
| `app/` | Application code, tests, Dockerfile and docker-compose.yml |
| `terraform/` | Infrastructure definitions (planned) |
| `ansible/` | Server configuration (planned) |
| `.github/workflows/` | CI/CD pipeline (planned) |
| `docs/` | Architecture and documentation (planned) |

## Run locally

Requirements: Docker with the Compose plugin.

1. Create the file `app/.env` (it is not part of the repository because it contains a secret) with a database password of your choice, using letters and digits only:

   ```
   POSTGRES_PASSWORD=your-password-here
   ```

2. Start the application and the database from the `app/` directory:

   ```bash
   cd app
   docker compose up --build
   ```

3. Open <http://localhost:8080>.

To stop everything use `docker compose down`. Add `-v` to also delete the database volume.

## Tests

Tests need a PostgreSQL database. Point `TEST_DATABASE_URL` at an empty database and run pytest:

```bash
cd app
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/test_db pytest tests
```

Without `TEST_DATABASE_URL` the tests are skipped.

## Roadmap

- [x] Containerized application with PostgreSQL
- [ ] Infrastructure as code: Terraform (VM on Proxmox) and Ansible (Docker, application)
- [ ] CI/CD: build and publish image on every commit, deploy from `main`, notifications
- [ ] Monitoring and logging: Prometheus, Loki, Grafana
- [ ] Architecture documentation and limitations
