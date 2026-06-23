-- AI Agent Platform – initial schema
-- This file is executed automatically by the postgres container on first boot.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Agents ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,
    config      JSONB NOT NULL DEFAULT '{}',
    status      VARCHAR(32) NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive', 'error')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Tasks ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agents(id) ON DELETE SET NULL,
    workflow_id     VARCHAR(256),
    run_id          VARCHAR(256),
    input_text      TEXT NOT NULL,
    output_text     TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- ─── Tool Calls ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tool_calls (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID REFERENCES tasks(id) ON DELETE CASCADE,
    tool_name   VARCHAR(128) NOT NULL,
    arguments   JSONB NOT NULL DEFAULT '{}',
    result      JSONB,
    duration_ms INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id    ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status      ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at  ON tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_calls_task   ON tool_calls(task_id);

-- ─── updated_at trigger ──────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER set_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER set_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ─── Seed demo agents ────────────────────────────────────────────────────────
INSERT INTO agents (name, description, config) VALUES
  ('research-agent',
   'Searches the web and synthesizes information on any topic.',
   '{"model":"gpt-4o","max_steps":10,"tools":["web_search","summarise"]}'),
  ('code-agent',
   'Generates, reviews and explains code in any language.',
   '{"model":"gpt-4o","max_steps":8,"tools":["execute_code","lint_code"]}'),
  ('data-agent',
   'Analyses structured data and produces charts and insights.',
   '{"model":"gpt-4o","max_steps":12,"tools":["analyse_data","plot_chart"]}')
ON CONFLICT (name) DO NOTHING;
