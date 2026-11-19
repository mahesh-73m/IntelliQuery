#!/bin/bash
# Creates the two runtime roles. Runs automatically on first start of the Docker
# Postgres container (docker-entrypoint-initdb.d). For a manual install run:
#   IQ_APP_PASSWORD=... IQ_RO_PASSWORD=... POSTGRES_USER=postgres POSTGRES_DB=intelliquery bash database/00_roles.sh
set -euo pipefail
: "${IQ_APP_PASSWORD:?IQ_APP_PASSWORD is required}"
: "${IQ_RO_PASSWORD:?IQ_RO_PASSWORD is required}"
psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-postgres}" --dbname "${POSTGRES_DB:-intelliquery}" \
     -v app_pw="$IQ_APP_PASSWORD" -v ro_pw="$IQ_RO_PASSWORD" <<'SQL'
-- Application role: owns app state (users, conversations, history...). Cannot touch business data.
CREATE ROLE iq_app LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
-- Read-only role: executes AI-generated SQL. SELECT on business.* only.
CREATE ROLE iq_readonly LOGIN PASSWORD :'ro_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;

ALTER ROLE iq_readonly SET default_transaction_read_only = on;
ALTER ROLE iq_readonly SET statement_timeout = '5s';
ALTER ROLE iq_readonly SET search_path = business;
ALTER ROLE iq_readonly CONNECTION LIMIT 20;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL
