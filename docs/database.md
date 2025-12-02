The project currently uses a postgres database with pgvector exentension for embeddings and the langgraph checkpointer.


## Tests
A sqlite database is used for the unit tests.

As not all fields are compatible (JSONB), we use testcontainers for integration tests.


## Schema Versioning
We use alembic for schema versioning, for more details see `database/alembic/env.py`

To create a new revision:
```
alembic revision --autogenerate -m "create users table"
```

To modify the database
```
alembic upgrade head
```

## Dev vs. Prod

Docker compose defines different volumes, and the two databases use different ports.


start with
`docker compose --profile dev up -d`

or 
`docker compose --profile prod up -d`

## Backup

see `database/backup`

Go to the directory where you want to store the backups.
`storage/backups/` for exampl.

Execute the backup scripts.

### Restoring Backups

```bash
psql -h localhost -p 5434 -U postgres -d proddb < backups/proddb_backup_xxx.sql
```


## DATA

For simplicity all binary data is stored in ./storage


we store 

- sql database dumps in ./storage/backups
- ai models in /.storage/models

User data is stored in ./storage/dev or ./storage/prod, for dev and prod respectively.

To share data between dev and prod, copy the data from one directory to the another.

The architecture is made modular, so you can easily replace the storage backend with a S3 bucket.



