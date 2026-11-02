CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS usage_log CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS activities CASCADE;
DROP TABLE IF EXISTS destinations CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS ai_services CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    full_name     VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(10)  NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    token_limit   INTEGER      NOT NULL DEFAULT 20000 CHECK (token_limit >= 0),
    tokens_used   INTEGER      NOT NULL DEFAULT 0     CHECK (tokens_used >= 0),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Llaves de solo lectura para consumidores externos (Power BI)
CREATE TABLE api_keys (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    key_hash   VARCHAR(64)  NOT NULL UNIQUE,   -- SHA-256 de la llave
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_services (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(40)  NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE destinations (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    department  VARCHAR(80)  NOT NULL,
    category    VARCHAR(50)  NOT NULL,          -- ciudad, naturaleza, arqueología...
    description TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE activities (
    id             SERIAL PRIMARY KEY,
    destination_id INTEGER      NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name           VARCHAR(150) NOT NULL,
    description    TEXT,
    category       VARCHAR(50)  NOT NULL,       -- cultura, aventura, gastronomía...
    est_cost_gtq   NUMERIC(10,2) NOT NULL DEFAULT 0,
    duration_hours NUMERIC(4,1)  NOT NULL DEFAULT 2,
    latitude       DOUBLE PRECISION,
    longitude      DOUBLE PRECISION
);

-- Fragmentos de texto con su embedding (768 dimensiones, Gemini)
CREATE TABLE document_chunks (
    id             SERIAL PRIMARY KEY,
    destination_id INTEGER REFERENCES destinations(id) ON DELETE CASCADE,
    source_title   VARCHAR(200) NOT NULL,
    content        TEXT         NOT NULL,
    embedding      vector(768)
);
CREATE INDEX idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE conversations (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES ai_services(id),
    title      VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    sources         JSONB,        -- fuentes usadas (RAG)
    steps           JSONB,        -- pasos intermedios del agente
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE usage_log (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_id        INTEGER NOT NULL REFERENCES ai_services(id),
    conversation_id   INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens      INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_user_date    ON usage_log (user_id, created_at);
CREATE INDEX idx_usage_service_date ON usage_log (service_id, created_at);
CREATE INDEX idx_messages_conv      ON messages (conversation_id, created_at);
CREATE INDEX idx_activities_dest    ON activities (destination_id);