-- ============================================================
-- UNMASKED — Autonomous UPI Fraud Investigation System
-- PostgreSQL Schema (requires pgvector extension)
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;           -- pgvector for RAG embeddings
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS pg_trgm;          -- trigram similarity for fuzzy VPA matching

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Cases: one row per fraud investigation
CREATE TABLE cases (
    case_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    victim_vpa          VARCHAR(100) NOT NULL,
    fraud_vpa           VARCHAR(100) NOT NULL,
    amount              DECIMAL(12,2) NOT NULL,
    transaction_ref     VARCHAR(100) UNIQUE NOT NULL,
    status              VARCHAR(20) DEFAULT 'queued'
                        CHECK (status IN ('queued','processing','complete','failed')),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    -- Metadata
    source_channel      VARCHAR(50) DEFAULT 'web',   -- web | api | bulk_upload
    priority            INTEGER DEFAULT 0             -- 0=normal, 1=high (amount > 1L)
);

-- Transaction hops — each row is one hop in the money trail
CREATE TABLE transactions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID REFERENCES cases(case_id) ON DELETE CASCADE,
    sender_vpa          VARCHAR(100) NOT NULL,
    receiver_vpa        VARCHAR(100) NOT NULL,
    amount              DECIMAL(12,2) NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL,
    transaction_ref     VARCHAR(100),
    hop_number          INTEGER NOT NULL,
    time_delta_seconds  INTEGER,          -- NULL for hop 0; < 600 = mule signal
    amount_drop_pct     DECIMAL(5,2),     -- % drop from previous hop; < 10% = cash-out
    is_cash_out         BOOLEAN DEFAULT FALSE,
    receiver_bank       VARCHAR(50)       -- derived from VPA suffix
);

-- VPA Registry — THE DATA MOAT. Risk compounds with every case processed.
CREATE TABLE vpa_registry (
    vpa                 VARCHAR(100) PRIMARY KEY,
    registrar_bank      VARCHAR(50),
    first_seen_at       TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ DEFAULT NOW(),
    total_cases_involved INTEGER DEFAULT 1,
    risk_score          DECIMAL(3,2) DEFAULT 0.00
                        CHECK (risk_score >= 0 AND risk_score <= 1),
    flags               TEXT[] DEFAULT '{}',
    account_age_days    INTEGER,
    is_confirmed_fraud  BOOLEAN DEFAULT FALSE,
    -- New fields for richer intelligence
    vpa_type            VARCHAR(20) DEFAULT 'personal'
                        CHECK (vpa_type IN ('personal','merchant','phone','random')),
    naming_pattern      VARCHAR(100),     -- extracted prefix for fuzzy clustering
    total_volume_in     DECIMAL(14,2) DEFAULT 0,
    total_volume_out    DECIMAL(14,2) DEFAULT 0,
    unique_counterparties INTEGER DEFAULT 0
);

-- Completed investigation reports
CREATE TABLE case_reports (
    case_id             UUID PRIMARY KEY REFERENCES cases(case_id) ON DELETE CASCADE,
    report_markdown     TEXT,
    confidence_overall  DECIMAL(3,2),
    scam_pattern        VARCHAR(100),
    matched_advisory    VARCHAR(200),
    network_size        INTEGER,
    trail_status        VARCHAR(50),
    graph_json          JSONB,           -- full Cytoscape.js node/edge data
    evidence_facts      JSONB,           -- numbered facts F1, F2, ... for audit
    it_act_sections     TEXT[],          -- applicable IT Act sections
    generated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- RAG Knowledge Base — fraud advisories, scam patterns, legal references
CREATE TABLE knowledge_base (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source              VARCHAR(200),     -- "RBI Advisory 2023-47"
    content             TEXT NOT NULL,
    embedding           vector(1536),     -- text-embedding-3-small
    metadata            JSONB,            -- {pattern_name, evidence_points[], severity}
    category            VARCHAR(50),      -- advisory | scam_pattern | legal | case_study
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- IVFFlat for fast approximate nearest-neighbor search (Agent 3)
CREATE INDEX kb_embedding_idx ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Transaction lookups (Agent 1 & 4 traverse by sender/receiver)
CREATE INDEX idx_tx_sender ON transactions(sender_vpa);
CREATE INDEX idx_tx_receiver ON transactions(receiver_vpa);
CREATE INDEX idx_tx_case ON transactions(case_id);
CREATE INDEX idx_tx_timestamp ON transactions(timestamp);

-- Case status polling
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_fraud_vpa ON cases(fraud_vpa);
CREATE INDEX idx_cases_created ON cases(created_at DESC);

-- VPA registry lookups
CREATE INDEX idx_vpa_risk ON vpa_registry(risk_score DESC);
CREATE INDEX idx_vpa_bank ON vpa_registry(registrar_bank);
CREATE INDEX idx_vpa_confirmed ON vpa_registry(is_confirmed_fraud) WHERE is_confirmed_fraud = TRUE;

-- Trigram index for fuzzy VPA matching (Agent 2)
CREATE INDEX idx_vpa_trgm ON vpa_registry USING gin (vpa gin_trgm_ops);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- AGENT 4: BFS over fraud network via recursive CTE
-- Usage: SELECT * FROM fraud_network_bfs('fraud123@ybl', 3);
CREATE OR REPLACE FUNCTION fraud_network_bfs(
    start_vpa VARCHAR,
    max_depth INT DEFAULT 3
)
RETURNS TABLE (
    vpa             VARCHAR,
    depth           INT,
    connected_from  VARCHAR,
    amount          DECIMAL,
    time_delta_seconds INT,
    registrar_bank  VARCHAR,
    risk_score      DECIMAL,
    flags           TEXT[]
) AS $$
WITH RECURSIVE fraud_network AS (
    -- Base case: direct receivers from the starting VPA
    SELECT
        t.receiver_vpa AS vpa,
        1 AS depth,
        t.sender_vpa AS connected_from,
        t.amount,
        t.time_delta_seconds
    FROM transactions t
    WHERE t.sender_vpa = start_vpa

    UNION ALL

    -- Recursive case: follow the money chain
    SELECT
        t.receiver_vpa,
        fn.depth + 1,
        fn.vpa,
        t.amount,
        t.time_delta_seconds
    FROM transactions t
    JOIN fraud_network fn ON t.sender_vpa = fn.vpa
    WHERE fn.depth < max_depth
      AND t.receiver_vpa != start_vpa  -- prevent cycles back to start
)
SELECT
    fn.vpa,
    fn.depth,
    fn.connected_from,
    fn.amount,
    fn.time_delta_seconds,
    COALESCE(v.registrar_bank, 'unknown'),
    COALESCE(v.risk_score, 0.0),
    COALESCE(v.flags, '{}')
FROM fraud_network fn
LEFT JOIN vpa_registry v ON fn.vpa = v.vpa
ORDER BY fn.depth, fn.amount DESC;
$$ LANGUAGE sql;


-- AGENT 1: Trace transaction chain from a specific case
CREATE OR REPLACE FUNCTION trace_transaction_chain(
    p_case_id UUID
)
RETURNS TABLE (
    hop             INTEGER,
    sender          VARCHAR,
    receiver        VARCHAR,
    amount          DECIMAL,
    ts              TIMESTAMPTZ,
    time_delta      INTEGER,
    drop_pct        DECIMAL,
    is_cashout      BOOLEAN
) AS $$
    SELECT
        hop_number,
        sender_vpa,
        receiver_vpa,
        amount,
        timestamp,
        time_delta_seconds,
        amount_drop_pct,
        is_cash_out
    FROM transactions
    WHERE case_id = p_case_id
    ORDER BY hop_number ASC;
$$ LANGUAGE sql;


-- AGENT 2: Find VPAs with similar naming patterns (same operator/syndicate)
CREATE OR REPLACE FUNCTION find_similar_vpas(
    target_vpa VARCHAR,
    similarity_threshold DECIMAL DEFAULT 0.3
)
RETURNS TABLE (
    vpa             VARCHAR,
    similarity      REAL,
    risk_score      DECIMAL,
    total_cases     INTEGER,
    flags           TEXT[]
) AS $$
    SELECT
        v.vpa,
        similarity(v.vpa, target_vpa) AS sim,
        v.risk_score,
        v.total_cases_involved,
        v.flags
    FROM vpa_registry v
    WHERE v.vpa != target_vpa
      AND similarity(v.vpa, target_vpa) > similarity_threshold
    ORDER BY sim DESC
    LIMIT 20;
$$ LANGUAGE sql;


-- Utility: Update VPA registry risk score (called after each investigation)
CREATE OR REPLACE FUNCTION upsert_vpa_risk(
    p_vpa VARCHAR,
    p_bank VARCHAR,
    p_account_age INTEGER,
    p_flags TEXT[]
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO vpa_registry (vpa, registrar_bank, account_age_days, flags, total_cases_involved)
    VALUES (p_vpa, p_bank, p_account_age, p_flags, 1)
    ON CONFLICT (vpa) DO UPDATE SET
        last_seen_at = NOW(),
        total_cases_involved = vpa_registry.total_cases_involved + 1,
        flags = ARRAY(SELECT DISTINCT unnest(vpa_registry.flags || p_flags)),
        account_age_days = COALESCE(p_account_age, vpa_registry.account_age_days);
END;
$$ LANGUAGE plpgsql;
