# Alembic Migrations

The migrations folder was missing or empty. To initialize the database migrations, please run the following command inside the `backend` Docker container:

```bash
alembic revision --autogenerate -m "Initial migration"
```

Then apply the migration:

```bash
alembic upgrade head
```

If you are running outside the container, ensure `DATABASE_URL` is set to point to the Postgres instance (e.g. localhost:5432).
