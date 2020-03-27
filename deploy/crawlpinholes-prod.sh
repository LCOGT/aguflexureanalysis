#!/bin/bash

ndays=4
NCPU=1

# PostgreSQL Database Configuration using the LCO standard for database
# connection configuration in containerized projects.
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-aguflexureanalysis}"
DB_USER="${DB_USER:-aguflexureanalysis}"
DB_PASS="${DB_PASS:-undefined}"

# SQLAlchemy database connection string
DATABASE="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"


agupinholesearch --ndays ${ndays} --ncpu ${NCPU} --loglevel INFO --database ${DATABASE} --useaws
aguanalysis --database ${DATABASE}
