INSERT INTO capabilities (slug, name, proficiency, evidence, limitations) VALUES
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
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  proficiency = EXCLUDED.proficiency,
  evidence = EXCLUDED.evidence,
  limitations = EXCLUDED.limitations,
  active = true;
