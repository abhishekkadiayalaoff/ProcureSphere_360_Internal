# ProcureSphere 360 - Local Docker Setup Guide

This guide explains how to set up the local development environment using Docker. The architecture consists of 5 containers:
- **db**: PostgreSQL 15 database
- **redis**: Redis message broker & cache
- **web**: Django application (Frontend + Backend APIs)
- **celery_worker**: Background task processor
- **celery_beat**: Scheduled task trigger

## Prerequisites
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ensure the Docker Engine is running).
2. Install [Git](https://git-scm.com/downloads).
3. Ensure WSL 2 is installed and enabled (for Windows users).

## Step 1: Clone the Repository
Clone the project to your local machine and navigate into the project directory:
```bash
git clone https://github.com/VPDTechnologies/ProcureSphere_360_Internal.git
cd ProcureSphere_360_Internal
```

## Step 2: Configure Environment Variables
You need to set up the local `.env` file before booting the containers.

1. Copy the `.env.example` file to create your local `.env`:
   *(Note: A base `.env` might already be present, but if not, create one based on the example)*
   
   **Windows (PowerShell):**
   ```powershell
   Copy-Item .env.example .env
   ```
   **Mac/Linux:**
   ```bash
   cp .env.example .env
   ```

2. Open the `.env` file and ensure the following Docker-specific connections are set:
   ```env
   # Database connection to the docker postgres service
   DB_HOST=db
   DB_PORT=5432

   # Redis connection to the docker redis service
   REDIS_URL=redis://redis:6379/0
   ```

## Step 3: Build and Start the Containers
Run the following command to build the Docker images and start all 5 containers in the background:
```bash
docker compose up --build -d
```
*Note: The first time you run this, it will take a few minutes to download the base images and install the Python dependencies.*

## Step 4: Verify the Setup
Once the command finishes, Docker will automatically execute the database migrations and collect static files via the `entrypoint.sh` script.

1. **Check Container Status:** Open Docker Desktop and navigate to the **Containers** tab. Ensure all 5 containers under the `procuresphere_360_internal` stack are green and running.
2. **Access the Web App:** Open your browser and navigate to:
   [http://localhost:8000](http://localhost:8000)

## Useful Docker Commands for Development

- **View Live Logs:**
  ```bash
  docker compose logs -f
  ```
  *To view logs for a specific container (e.g., the web container):*
  ```bash
  docker compose logs -f web
  ```

- **Stop the Containers:**
  ```bash
  docker compose down
  ```
  *(This stops the containers but preserves your database data in the docker volume)*

- **Run Django Management Commands:**
  To create a superuser or run arbitrary commands inside the web container:
  ```bash
  docker compose exec web python manage.py createsuperuser
  ```

- **Rebuild After Adding Dependencies:**
  If you add a new package to `requirements.txt`, you must rebuild the image:
  ```bash
  docker compose up --build -d
  ```

## Troubleshooting
- **"500 Internal Server Error" / Docker Engine Crash:** If Docker Desktop freezes or crashes (common on Windows), open PowerShell and run `wsl --shutdown`. Then click "Restart" in Docker Desktop.
- **Database Connection Errors:** Ensure the `DB_HOST` in your `.env` is set exactly to `db` and NOT `localhost` or `127.0.0.1`.
