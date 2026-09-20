INSERT INTO platforms (slug, name, source_kind, base_url, attribution_required, policy_notes)
VALUES (
  'freelancer_alert',
  'Freelancer.com Alerts',
  'official_email_alert',
  'https://www.freelancer.com',
  true,
  'Ingest only official user-requested job alert emails. Do not crawl pages or submit bids.'
)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  source_kind = EXCLUDED.source_kind,
  base_url = EXCLUDED.base_url,
  attribution_required = EXCLUDED.attribution_required,
  policy_notes = EXCLUDED.policy_notes,
  enabled = true;
