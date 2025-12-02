#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec -t dev-db pg_dump -U admin mydb > devdb_backup_$DATE.sql