#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -p 5434 -U postgres -d proddb > proddb_backup_$DATE.sql