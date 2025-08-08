# Univera No-Code Backend

This repository contains a FastAPI-based backend that powers a multi-tenant no-code platform. Tenants can define custom entities and fields which are stored in PostgreSQL JSONB columns, and the application generates CRUD APIs at runtime.

## Features
- Dynamic entity and field creation per tenant
- JSONB storage of schemas and records
- JWT authentication with admin/user roles
- Automatic CRUD router generation per entity
- File upload storage on local disk (S3-ready)
- OpenAPI documentation available at `/docs`

## Requirements
- Python 3.10+
- PostgreSQL 13+

## Installation
1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up a PostgreSQL database and update the `DATABASE_URL` via environment variable or `.env` file. Example `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/univera
   SECRET_KEY=change_me
   ```

## Running the Server
1. Start PostgreSQL and create the database.
2. Run the API:
   ```bash
   uvicorn app.main:app --reload
   ```
3. The app creates tables on startup and loads any saved entity schemas.

## Authentication
1. Create an admin user directly in the database or via `/auth/users` using an existing admin.
2. Obtain a token with username and password:
   ```bash
   curl -X POST http://localhost:8000/auth/token -d 'username=admin&password=secret'
   ```
3. Use the returned token in the `Authorization: Bearer <token>` header for subsequent requests.

## Defining Schemas
Admins can create entity schemas:
```bash
curl -X POST http://localhost:8000/schemas/ \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "entity_name": "student",
    "fields": [
      {"name": "name", "type": "string"},
      {"name": "age", "type": "integer"}
    ]
  }'
```
This registers `/student` CRUD endpoints.

## Working with Records
Create a record:
```bash
curl -X POST http://localhost:8000/student/ \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Alice", "age": 20}'
```
List records:
```bash
curl -H 'Authorization: Bearer <token>' http://localhost:8000/student/
```

## File Uploads
Upload files for a tenant:
```bash
curl -X POST http://localhost:8000/files/upload \
  -H 'Authorization: Bearer <token>' \
  -F 'file=@/path/to/file.pdf'
```
The response contains a URL pointing to the stored file.

## Testing
Run basic syntax checks and tests:
```bash
python -m py_compile $(find app -name '*.py')
pytest
```

## Directory Structure
```
app/
  auth.py           # Authentication and user management
  config.py         # Settings
  crud_router.py    # Dynamic CRUD router generator
  database.py       # DB session setup
  main.py           # FastAPI application
  models.py         # SQLAlchemy models
  routers/
    files.py        # File upload endpoints
    schemas.py      # Schema management
  schemas.py        # Pydantic models
requirements.txt
```

## OpenAPI Docs
Visit `http://localhost:8000/docs` for interactive API documentation.
