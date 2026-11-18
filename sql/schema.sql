CREATE TABLE IF NOT EXISTS migration_runs (
    run_id               SERIAL PRIMARY KEY,
    source_file          TEXT        NOT NULL,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at          TIMESTAMPTZ,
    status               TEXT        NOT NULL DEFAULT 'RUNNING',
    rows_read            INTEGER,
    rows_valid           INTEGER,
    rows_rejected        INTEGER,
    rows_loaded          INTEGER,
    rows_already_present INTEGER,
    error_message        TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    account_no    TEXT PRIMARY KEY,
    customer_name TEXT,
    branch_code   TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id          TEXT PRIMARY KEY,
    account_no      TEXT          NOT NULL REFERENCES accounts (account_no),
    txn_date        DATE          NOT NULL,
    txn_type        TEXT          NOT NULL CHECK (txn_type IN ('CREDIT', 'DEBIT')),
    amount          NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency        TEXT          NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    migrated_run_id INTEGER       REFERENCES migration_runs (run_id)
);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions (account_no);

CREATE TABLE IF NOT EXISTS rejected_records (
    id         SERIAL PRIMARY KEY,
    run_id     INTEGER NOT NULL REFERENCES migration_runs (run_id),
    source_row INTEGER NOT NULL,
    txn_id     TEXT,
    rules      TEXT[]  NOT NULL,
    details    TEXT,
    raw_record JSONB   NOT NULL
);