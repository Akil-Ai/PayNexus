-- PayNexus PostgreSQL initialization script

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Audit log sequence for strictly sequential deterministic ordering
CREATE SEQUENCE IF NOT EXISTS audit_log_seq START WITH 1 INCREMENT BY 1;

-- Immutability enforcement trigger function for audit_log table
CREATE OR REPLACE FUNCTION enforce_audit_log_immutability()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'PayNexus Audit Log Violation: UPDATE and DELETE operations are strictly prohibited on the audit_log table. Immutability is cryptographically and operationally enforced.';
END;
$$ LANGUAGE plpgsql;
