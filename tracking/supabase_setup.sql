-- ============================================================
-- Supabase schema for inflation report tracking
-- Run this in the Supabase SQL Editor after creating a project.
-- ============================================================

-- Create the tracking table
CREATE TABLE report_events (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('opened', 'heartbeat', 'downloaded')),
    report_month TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    duration_seconds INTEGER,
    user_agent TEXT,
    metadata JSONB
);

-- Index for fast lookups by token
CREATE INDEX idx_report_events_token ON report_events(token);

-- Index for queries by report month
CREATE INDEX idx_report_events_month ON report_events(report_month);

-- Row Level Security: allow anonymous inserts only, no reads
ALTER TABLE report_events ENABLE ROW LEVEL SECURITY;

-- Policy: anyone can insert (tracking events from the viewer page)
CREATE POLICY "Allow anonymous inserts"
    ON report_events
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- No SELECT policy for anon = no one can read via the public API.
-- Use the service role key (locally) or the Supabase dashboard to read data.
