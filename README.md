# Observability Platform

A DevOps and observability project demonstrating the end-to-end application delivery lifecycle: from provisioning virtual machines on Proxmox, through server configuration and application deployment, to collecting metrics and logs and sending notifications about pipeline and service health.

The platform consists of a sample order management application and a separate observability stack. Infrastructure is defined with Terraform, servers and services are configured with Ansible, and GitHub Actions automates testing, image builds, and deployment.

## Table of Contents

- [Project Goals and Scope](#project-goals-and-scope)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Application](#application)
- [Monitoring, Logs, and Alerts](#monitoring-logs-and-alerts)
- [CI/CD and Discord Notifications](#cicd-and-discord-notifications)
- [Repository Structure](#repository-structure)
- [Run Locally](#run-locally)
- [Tests](#tests)
- [Infrastructure Deployment](#infrastructure-deployment)
- [GitHub Actions Configuration](#github-actions-configuration)
- [Service Access](#service-access)
- [Security Notes](#security-notes)

## Project Goals and Scope

This project simulates deploying a small client application in a server environment. It includes:

- provisioning two virtual machines on Proxmox with Terraform;
- installing Docker and deploying services with Ansible;
- running a Flask application and PostgreSQL database with Docker Compose;
- collecting metrics and checking application availability;
- collecting container logs and sending them to Loki;
- visualizing data and configuring alerts in Grafana;
- automating tests, image builds and publishing, and deployment with GitHub Actions;
- sending Discord notifications about pipeline results and monitoring alerts.

## Architecture

```mermaid
flowchart LR
    Dev[Repository change] --> Actions[GitHub Actions]
    Actions --> Tests[Application tests]
    Tests --> Build[Build Docker image]
    Build --> GHCR[GitHub Container Registry]
    Actions --> Runner[Self-hosted runner]
    Runner --> Ansible[Ansible]
    Ansible --> AppVM[Application VM]
    Ansible --> ObsVM[Observability VM]

    subgraph Proxmox
        AppVM --> App[Flask]
        App --> DB[(PostgreSQL)]
        AppVM --> Alloy[Grafana Alloy]
        ObsVM --> Prometheus[Prometheus]
        ObsVM --> Blackbox[Blackbox Exporter]
        ObsVM --> NodeExporter[Node Exporter]
        ObsVM --> Loki[Loki]
        ObsVM --> Grafana[Grafana]
    end

    GHCR --> App
    Blackbox -->|HTTP probe of application| Prometheus
    NodeExporter -->|Observability VM metrics| Prometheus
    Prometheus --> Grafana
    Alloy -->|Container logs| Loki
    Loki --> Grafana
    Grafana -->|Alerts| Discord[Discord]
    Actions -->|CI/CD result| Discord
```

In the target environment, Terraform creates a dedicated VM for the application and another for monitoring. Ansible installs Docker on the VMs and deploys the corresponding stacks. The application and database run together on the application VM, while observability components run on the observability VM.

## Technology Stack

| Area | Technologies |
|---|---|
| Virtualization | Proxmox VE |
| Infrastructure as Code (IaC) | Terraform, `bpg/proxmox` provider |
| Server configuration and deployment | Ansible, Ansible Vault |
| Application | Python, Flask, Gunicorn |
| Database | PostgreSQL |
| Containerization | Docker, Docker Compose |
| Metrics and alerts | Prometheus, Node Exporter, Blackbox Exporter |
| Logs | Grafana Alloy, Loki |
| Dashboards and visualization | Grafana |
| CI/CD | GitHub Actions, self-hosted runner |
| Container registry | GitHub Container Registry (GHCR) |
| Notifications | Discord Webhook |
| Configuration templates | YAML, Jinja2 (`.yml.j2`) |

## Application

The "Order desk" web application is built with Flask and uses PostgreSQL. It provides:

- **Overview** — counts of all, open, and fulfilled orders, total fulfilled revenue, and the latest orders;
- **Orders** — view and filter orders by status, add and edit orders, mark orders as fulfilled or reopen them, and permanently delete orders;
- **About** — view the Docker image tag, build commit, container hostname, Python and Flask versions, database connection details, database size, and health-check endpoint.

The `/health` endpoint reports the application and database connection status. Docker uses it as a health check; the application's home page availability is also checked by Blackbox Exporter.

### Application Screenshot

![alt text](docs/images/app_panel.png)

## Monitoring, Logs, and Alerts

Ansible deploys the observability stack, which runs in a separate Docker Compose project.

- **Prometheus** scrapes itself, monitors application availability through Blackbox Exporter, and collects Node Exporter metrics from the observability VM. The scrape interval is 15 seconds.
- **Blackbox Exporter** probes the application's home page over HTTP and exposes the result and response time as metrics.
- **Node Exporter** exposes CPU, memory, disk, and network metrics for the observability VM. In the current configuration, it is not installed on the application VM.
- **Grafana Alloy** runs on the application host, reads Docker container log files, and sends them to Loki.
- **Loki** stores logs, which can be explored in Grafana.
- **Grafana** is provisioned with Prometheus and Loki data sources and an "Observability Overview" dashboard.

The dashboard includes observability VM CPU, memory, and disk usage, application availability, HTTP response time, and the number of firing alerts. Alert rules cover unavailable Prometheus targets and an unavailable application. Grafana alerts are routed to the configured Discord contact point.

### Grafana Screenshot

![docs/images/grafana_dashboard.png](docs/images/grafana_dashboard.png)

### Discord Notifications

The project has two types of Discord notifications:

1. **GitHub Actions** sends a message with the test, image build, and deployment results. The notification includes the branch, short commit SHA, and a link to the workflow run.
2. **Grafana** sends configured monitoring alerts to a Discord webhook, for example when the application stops responding.

These are separate integrations and require separate webhook configuration: GitHub Actions reads its webhook URL from a GitHub Actions secret, while Grafana's webhook URL is stored in encrypted Ansible Vault variables.

### Notification Screenshot

![alt text](docs/images/grafana_firing_alert.png)

![alt text](docs/images/grafana_resolved_alert.png)

## CI/CD and Discord Notifications

The CI/CD workflow is defined in `.github/workflows/ci-cd.yml`. It runs for pull requests targeting `dev`, `staging`, or `production`, and for pushes to those branches.

1. **Test** — GitHub Actions starts PostgreSQL 16 as a service, installs Python dependencies, and runs the application tests.
2. **Build and publish** — after tests pass, the application image is built. On pushes to `dev`, `staging`, and `production`, it is published to GHCR with a commit-SHA tag. The `latest` tag is reserved for `production`. Pull requests build the image for validation but do not publish it.
3. **Deploy** — only a push to `production` triggers deployment. The self-hosted runner runs the Ansible playbooks for the application and observability stack, and the application deployment pulls the image tagged with that commit SHA. The job uses the GitHub Actions `production` environment; configure required reviewers there if production deployment should need manual approval.
4. **Notify** — the final job sends the pipeline status to Discord, including when an earlier stage fails. It reports `Deploy: skipped` for non-production branches and pull requests because deployment is intentionally restricted to production.

The deployment job runs on a **self-hosted GitHub Actions runner** rather than a GitHub-hosted runner. This runner is connected to the repository and has network access to the application and observability VMs, allowing it to run Ansible deployments in the local Proxmox environment.

The repository also contains a separate `site-alloy.yml` playbook for deploying the log collector. The current GitHub Actions workflow does not invoke that playbook; run it separately when deploying or updating Alloy.

### Branch Promotion Flow

Use pull requests to promote code through the branches:

```text
feature branch
      |
      v
     dev  -- PR + checks -->  staging  -- PR + checks -->  production
       CI                     CI                         CI + deploy
```

- Create feature branches from `dev` and open a pull request to merge them into `dev`. Review and merge only after the required checks pass.
- Open a pull request from `dev` to `staging`. GitHub Actions reruns the tests and validates the Docker image for the proposed promotion.
- After validating the change, open a pull request from `staging` to `production`. Once merged, GitHub Actions reruns the tests and build, then deploys that exact commit to the production VM.
- In the current repository, `dev` and `staging` are **branch-based validation stages, not separate deployed environments**. There is only one application VM, and it receives changes only from `production`. The workflow does not deploy the running application to a staging VM. To test a deployed staging instance before production, provision a separate VM and configure a separate Ansible inventory and environment.

Create the `dev`, `staging`, and `production` branches in GitHub if they do not exist yet. Configure rulesets or branch protection under **Settings → Rules → Rulesets** to require pull requests and successful workflow checks before merging (protecting `dev` is also recommended). For an additional production approval step, configure required reviewers for the `production` environment under **Settings → Environments**. The workflow declares the environment, but approval is not enforced until reviewers are configured in GitHub.

## Repository Structure

```text
.
├── .github/
│   └── workflows/
│       └── ci-cd.yml                    # CI, image publishing, production deployment, Discord
├── ansible/
│   ├── group_vars/                      # encrypted Ansible Vault variables
│   │   ├── app/
│   │   └── observability/
│   ├── roles/
│   │   ├── alloy_agent/                 # Alloy log collector on the application VM
│   │   ├── app/                         # application Compose deployment and environment
│   │   ├── docker/                      # Docker Engine and Compose installation
│   │   └── observability/               # Prometheus, Loki, Grafana, exporters, alerting
│   ├── inventory.ini                    # application and observability hosts
│   ├── requirements.yml                 # required Ansible collections
│   ├── ansible.cfg
│   ├── site.yml                         # application VM playbook
│   ├── site-alloy.yml                   # Alloy agent playbook
│   └── site-observability.yml           # monitoring VM playbook
├── app/
│   ├── src/
│   │   ├── app.py                       # Flask routes and PostgreSQL operations
│   │   ├── static/style.css             # application styles
│   │   └── templates/                   # Overview, Orders, About, and edit-order pages
│   ├── tests/test_app.py                # application tests
│   ├── Dockerfile
│   ├── docker-compose.yml               # local application and PostgreSQL
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/
│   └── images/                          # application, Grafana, and alert screenshots
├── terraform/
│   ├── app-vm/                          # application VM definition and variables
│   └── observability-vm/                # monitoring VM definition and variables
├── .gitignore
└── README.md
```

Terraform's two VM directories maintain separate configurations and state. Ansible roles use Jinja2 templates, including `.yml.j2` files, to render service configuration on the target hosts. The `docs/images/` directory contains the screenshots embedded in this README.

## Run Locally

To run the application locally, you need Docker with the Docker Compose plugin.

1. Go to the application directory and create `app/.env`:

   ```dotenv
   POSTGRES_PASSWORD=choose-a-password
   ```

   The `.env` file contains the local database password and should not be published.

2. Start the application and PostgreSQL:

   ```bash
   cd app
   docker compose up --build
   ```

3. Open [http://localhost:8080](http://localhost:8080).

Stop the services with:

```bash
docker compose down
```

To also delete the database data stored in the volume, run `docker compose down -v`.

## Tests

The tests require a separate, reachable PostgreSQL database. They use the `TEST_DATABASE_URL` environment variable and clear the `orders` table, so do not point them at a production database or one containing data you want to keep.

Example: start a temporary test database in Docker:

```bash
docker run --rm --name observability-platform-test-db \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=test \
  -p 5432:5432 \
  -d postgres:16-alpine
```

Then install the dependencies and run the tests:

```bash
cd app
pip install -r requirements-dev.txt
TEST_DATABASE_URL='postgresql://test:test@localhost:5432/test' pytest tests
```

Stop the database after testing:

```bash
docker stop observability-platform-test-db
```

## Infrastructure Deployment

Deploying to Proxmox requires configured access to the Proxmox API, Terraform with the `bpg/proxmox` provider, Ansible, the `community.docker` collection, and SSH access to the VMs.

### 1. Configure the Environment

Before deploying, review and adjust:

- VM settings such as Proxmox node names, storage, bridge, IP addresses, gateway, and VM sizes in `terraform/app-vm/variables.tf` and `terraform/observability-vm/variables.tf`;
- host addresses and SSH users in `ansible/inventory.ini`;
- application and Loki addresses in the observability role variables and Alloy templates;
- Proxmox credentials and SSH keys.

The application VM IP address must match the address used by Blackbox Exporter, and the observability VM address must match the destination Alloy uses to send logs. The repository's default values are examples for a specific network and should be adapted to your environment before deployment.

### 2. Create the Virtual Machines

Each VM has its own Terraform directory and local state:

```bash
cd terraform/app-vm
terraform init
terraform plan
terraform apply
```

```bash
cd terraform/observability-vm
terraform init
terraform plan
terraform apply
```

After creating the VMs, verify that they are reachable over SSH at the addresses specified in the Ansible inventory.

### 3. Deploy Services with Ansible

From the `ansible/` directory, install the required collection:

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml
```

The encrypted `group_vars/*/vault.yml` files contain secrets used by the roles. To run the playbooks manually, you need a local Vault password file (`.vault_pass`) — do not commit it to the repository.

After configuring the Vault password, deploy the application and observability stack:

```bash
ansible-playbook site.yml --vault-password-file .vault_pass
ansible-playbook site-observability.yml --vault-password-file .vault_pass
ansible-playbook site-alloy.yml --vault-password-file .vault_pass
```

## GitHub Actions Configuration

The workflow uses GitHub Actions for CI/CD: it tests pull requests and branch updates, builds and publishes Docker images for branch pushes, deploys to the VMs only from `production`, and reports results to Discord. Configure the following repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|---|---|
| `ANSIBLE_VAULT_PASSWORD` | Decrypts Ansible Vault variables during deployment |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL used by the workflow to send CI/CD result notifications |

`DISCORD_WEBHOOK_URL` is a webhook credential (not a Discord bot API token). Keep it in GitHub Secrets and do not write the URL into the workflow file or commit it to the repository.

Create the `dev`, `staging`, and `production` branches in GitHub and set up pull requests to promote changes in that order. Also configure a **self-hosted runner** with the `self-hosted` label, SSH access to the servers, and the required tools, including Ansible and Terraform if it will also run Terraform operations. The workflow automatically installs the Ansible collection specified in `ansible/requirements.yml`.

Provisioning VMs with Terraform also requires valid Proxmox provider credentials. These are not configured by the workflow shown in this repository; configure them securely in the environment where you run Terraform.

Grafana's Discord integration is configured using the `discord_webhook_url` variable when Ansible generates the Grafana contact point. This is a separate webhook credential from `DISCORD_WEBHOOK_URL`; store it in Ansible Vault and do not put an active webhook directly in a template or in this documentation.

## Service Access

Default ports from the observability stack configuration:

| Service | Port | Description |
|---|---:|---|
| Application | `8080` | Application UI and `/health` endpoint |
| Grafana | `3000` | Dashboards, data sources, and alerts |
| Prometheus | `9090` | Metrics and scrape targets |
| Loki | `3100` | Logs API; bound to the observability VM address in Compose |

Grafana is available at `http://<observability-vm-address>:3000`, and the application at `http://<application-vm-address>:8080`. The Grafana administrator password is provided through encrypted Ansible Vault variables and is not stored in plain text in this README.

## Security Notes

- Do not publish `.env` or `.vault_pass` files, Discord webhooks, private keys, or plaintext passwords.
- Keep Ansible Vault files encrypted; provide the Vault password through GitHub secrets or a local file excluded from Git.
- Before using the project on another network, update the example IP addresses and Proxmox settings in Terraform, the Ansible inventory, and the Prometheus and Alloy configuration.
- Terraform stores state locally in the project directories. Protect state files and backups because they may contain infrastructure details.
- This project is intended for demonstration and learning. Before production use, separately assess access control for services, exposed ports, backups, data retention, and secret management.
