CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  CREATE TYPE opportunity_status AS ENUM (
    'DISCOVERED',
    'REJECTED',
    'QUALIFIED',
    'PROPOSAL_READY',
    'SUBMITTED',
    'CLIENT_REPLIED',
    'INTERVIEW',
    'WON',
    'LOST'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS platforms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  source_kind text NOT NULL,
  base_url text NOT NULL,
  attribution_required boolean NOT NULL DEFAULT false,
  policy_notes text,
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_id uuid NOT NULL REFERENCES platforms(id),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status text NOT NULL DEFAULT 'RUNNING',
  fetched_count integer NOT NULL DEFAULT 0,
  new_count integer NOT NULL DEFAULT 0,
  duplicate_count integer NOT NULL DEFAULT 0,
  rejected_count integer NOT NULL DEFAULT 0,
  error text
);

CREATE TABLE IF NOT EXISTS raw_opportunities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_id uuid NOT NULL REFERENCES platforms(id),
  source_run_id uuid REFERENCES source_runs(id),
  external_id text NOT NULL,
  payload jsonb NOT NULL,
  payload_sha256 text NOT NULL,
  fetched_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(platform_id, external_id, payload_sha256)
);

CREATE TABLE IF NOT EXISTS clients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_id uuid NOT NULL REFERENCES platforms(id),
  external_id text,
  display_name text,
  profile_url text,
  raw_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS clients_platform_external_id_idx
  ON clients(platform_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS opportunities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_id uuid NOT NULL REFERENCES platforms(id),
  raw_opportunity_id uuid REFERENCES raw_opportunities(id),
  client_id uuid REFERENCES clients(id),
  external_id text NOT NULL,
  canonical_url text NOT NULL,
  title text NOT NULL,
  description_clean text NOT NULL,
  location text,
  required_skills jsonb NOT NULL DEFAULT '[]'::jsonb,
  budget_min numeric,
  budget_max numeric,
  currency text,
  budget_type text,
  posted_at timestamptz,
  discovered_at timestamptz NOT NULL DEFAULT now(),
  source_updated_at timestamptz,
  content_hash text NOT NULL,
  status opportunity_status NOT NULL DEFAULT 'DISCOVERED',
  rejection_reason text,
  prefilter jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(platform_id, external_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS opportunities_canonical_url_idx
  ON opportunities(canonical_url);
CREATE INDEX IF NOT EXISTS opportunities_status_idx ON opportunities(status);
CREATE INDEX IF NOT EXISTS opportunities_posted_at_idx ON opportunities(posted_at DESC);

CREATE TABLE IF NOT EXISTS capabilities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  proficiency smallint NOT NULL CHECK (proficiency BETWEEN 0 AND 5),
  evidence text,
  limitations text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approved_claims (
  id text PRIMARY KEY,
  claim_text text NOT NULL,
  evidence text NOT NULL,
  allowed_contexts jsonb NOT NULL DEFAULT '["proposal"]'::jsonb,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fit_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid NOT NULL REFERENCES opportunities(id),
  score smallint NOT NULL CHECK (score BETWEEN 0 AND 100),
  recommendation text NOT NULL,
  fatal_risk boolean NOT NULL,
  result jsonb NOT NULL,
  prompt_version text NOT NULL,
  model text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fit_assessments_opportunity_idx
  ON fit_assessments(opportunity_id, created_at DESC);

CREATE TABLE IF NOT EXISTS research_solution_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid NOT NULL REFERENCES opportunities(id),
  feasible boolean NOT NULL,
  result jsonb NOT NULL,
  prompt_version text NOT NULL,
  model text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proposal_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid NOT NULL REFERENCES opportunities(id),
  version integer NOT NULL,
  stage text NOT NULL,
  proposal_text text NOT NULL,
  suggested_bid numeric,
  currency text,
  estimated_hours_min numeric,
  estimated_hours_max numeric,
  claims_used jsonb NOT NULL DEFAULT '[]'::jsonb,
  critic_result jsonb,
  prompt_version text NOT NULL,
  model text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(opportunity_id, version)
);

CREATE TABLE IF NOT EXISTS applications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid NOT NULL UNIQUE REFERENCES opportunities(id),
  actual_bid numeric,
  currency text,
  submitted_at timestamptz,
  client_replied_at timestamptz,
  interview_at timestamptz,
  final_project_value numeric,
  outcome_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS status_history (
  id bigserial PRIMARY KEY,
  opportunity_id uuid NOT NULL REFERENCES opportunities(id),
  from_status opportunity_status,
  to_status opportunity_status NOT NULL,
  reason text,
  actor text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid REFERENCES opportunities(id),
  agent_name text NOT NULL,
  prompt_version text NOT NULL,
  model text NOT NULL,
  status text NOT NULL,
  input_hash text NOT NULL,
  output jsonb,
  usage jsonb,
  error text,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS deliveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid NOT NULL REFERENCES opportunities(id),
  channel text NOT NULL,
  status text NOT NULL DEFAULT 'PENDING',
  payload jsonb NOT NULL,
  external_message_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  attempts integer NOT NULL DEFAULT 0,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  delivered_at timestamptz
);

INSERT INTO platforms (slug, name, source_kind, base_url, attribution_required, policy_notes)
VALUES (
  'remoteok',
  'Remote OK',
  'public_json_api',
  'https://remoteok.com',
  true,
  'Use the documented public feed. Mention Remote OK and preserve the original follow link.'
)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO capabilities (slug, name, proficiency, evidence, limitations) VALUES
  ('n8n', 'n8n', 4, 'User-declared core capability', NULL),
  ('rest-apis', 'REST APIs', 4, 'User-declared core capability', NULL),
  ('webhooks', 'Webhooks', 4, 'User-declared core capability', NULL),
  ('openai-api', 'OpenAI API', 4, 'User-declared core capability', NULL),
  ('gemini-api', 'Gemini API', 3, 'User-declared capability', NULL),
  ('telegram-bots', 'Telegram bots', 4, 'User-declared core capability', NULL),
  ('google-sheets', 'Google Sheets', 4, 'User-declared core capability', NULL),
  ('gmail-automation', 'Gmail automation', 4, 'User-declared core capability', NULL),
  ('data-extraction', 'Data extraction', 3, 'User-declared capability', 'Do not imply bypassing platform restrictions'),
  ('ai-agents', 'AI agents', 4, 'User-declared core capability', NULL),
  ('lead-pipelines', 'Lead pipelines', 4, 'User-declared core capability', NULL),
  ('workflow-automation', 'Workflow automation', 4, 'User-declared core capability', NULL),
  ('python', 'Python', 2, 'User described this as basic Python', 'Do not claim advanced Python engineering'),
  ('automation-architecture', 'Automation architecture', 4, 'User-declared core capability', NULL),
  ('data-entry-cleanup', 'Data entry and cleanup', 3, 'Approved beginner service scope', 'Prefer bounded spreadsheet and dataset tasks'),
  ('web-research', 'Web and competitor research', 3, 'Approved beginner service scope', 'Use public sources and cite uncertainty'),
  ('virtual-assistance', 'Virtual assistance', 3, 'Approved beginner service scope', 'No account impersonation or autonomous external communication'),
  ('ai-content-assistance', 'AI-assisted content preparation', 3, 'Approved beginner service scope', 'Drafting, rewriting, and formatting only; do not claim specialist authorship'),
  ('document-formatting', 'Resume and document formatting', 3, 'Approved beginner service scope', 'Formatting and editing, not fabricated credentials'),
  ('public-web-scraping', 'Basic public web scraping', 3, 'Approved beginner service scope', 'Public pages only; no login, CAPTCHA, or access-control bypass'),
  ('make-zapier', 'Make.com and Zapier workflows', 2, 'Transferable automation capability', 'Prefer small workflows and disclose limited platform-specific experience'),
  ('crm-airtable', 'CRM and Airtable automation', 2, 'Transferable automation capability', 'Prefer standard integrations and bounded schemas'),
  ('chatbot-setup', 'FAQ and support chatbot setup', 3, 'Approved beginner service scope', 'Existing APIs and bounded knowledge only'),
  ('reporting-dashboards', 'Spreadsheet reports and basic dashboards', 3, 'Approved beginner service scope', 'No advanced BI claims'),
  ('recruitment-automation', 'Job and recruitment automation', 4, 'Pathly portfolio relevance', 'Human review required; no autonomous applications'),
  ('prompt-workflows', 'Prompt and AI workflow development', 3, 'Approved beginner service scope', 'Sell tested workflows, not unsupported outcome claims'),
  ('document-ai', 'Document extraction and structured output', 3, 'Approved beginner service scope', 'Require validation for sensitive or high-stakes data'),
  ('simple-websites', 'Simple website setup and maintenance', 2, 'Approved adjacent service scope', 'Landing pages and maintenance only; reject large custom applications'),
  ('automation-troubleshooting', 'Automation troubleshooting', 3, 'Approved beginner service scope', 'Prefer reproducible n8n, API, and webhook issues'),
  ('admin-python', 'Basic Python administrative scripts', 2, 'Approved beginner service scope', 'File, CSV, and data-conversion utilities only')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO approved_claims (id, claim_text, evidence, allowed_contexts)
VALUES (
  'pathly.summary.v1',
  'I built Pathly, an AI-assisted workflow that discovers opportunities, evaluates relevance, generates application materials, and routes them through an automated review process.',
  'Project description supplied by the user. No client, revenue, performance, or outcome claims are approved.',
  '["proposal", "profile"]'::jsonb
)
ON CONFLICT (id) DO NOTHING;
