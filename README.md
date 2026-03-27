# LiveDrops - Backend API & WebSocket Server

This repository contains the backend infrastructure for the LiveDrops auction platform. It is designed to handle asynchronous database operations, secure identity management, and live WebSocket broadcasting for concurrent bidding.

## Tech Stack

* Framework: FastAPI (Python)
* Language: Python 3.14+
* Database ORM: SQLAlchemy 2.0 (Async)
* Database Driver: asyncpg
* Migrations: Alembic (Async configuration)
* Authentication: SuperTokens (Python Core SDK)
* Deployment: Render
* Database Hosting: PostgreSQL (Neon)

## Key Features

* Asynchronous Architecture: Built entirely on Python's async/await syntax, from the FastAPI route handlers down to the SQLAlchemy database queries via asyncpg.
* Real-Time WebSockets: Dedicated WebSocket routes handle live bid validation, anti-sniping logic, and immediate state broadcasting to all connected clients in a specific auction room.
* Version-Controlled Database: Schema changes are managed strictly through Alembic migrations, chained to the deployment lifecycle to ensure the database is always perfectly synced with the ORM models.
* Automated Data Hygiene: Includes a secure, header-protected cleanup endpoint. A GitHub Action cron job pings this endpoint hourly to safely purge inactive user data and expired auctions, utilizing SQLAlchemy's cascading deletes to prevent orphaned records.

## Local Development Setup

### Prerequisites
* Python 3.14+
* Poetry (Python package manager)
* A local PostgreSQL instance
* A local SuperTokens core instance

### Installation & Execution

1. Install dependencies via Poetry:

```bash
poetry install
```

2. Environment Configuration:

Create a `.env` file based on `.env.example` and populate it with your database credentials and SuperTokens connection URI. The application uses Pydantic Settings for strict environment variable validation.

3. Initialize the Database:

Run the Alembic migrations to build the local database schema.

```bash
poetry run alembic upgrade head
```

4. Start the Server:

```bash
poetry run uvicorn app.main:app --reload --port 8000
```