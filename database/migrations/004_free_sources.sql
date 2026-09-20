INSERT INTO platforms (slug, name, source_kind, base_url, attribution_required, policy_notes)
VALUES
  (
    'jobicy',
    'Jobicy',
    'public_json_api',
    'https://jobicy.com',
    true,
    'Use the public API, preserve the Jobicy listing URL, and credit Jobicy in delivery.'
  ),
  (
    'remotive',
    'Remotive',
    'public_json_api',
    'https://remotive.com',
    true,
    'Use the public API, preserve the Remotive URL, and mention Remotive as the source.'
  ),
  (
    'github',
    'GitHub',
    'public_rest_api',
    'https://github.com',
    true,
    'Search public issues only. Require an explicit paid-task or bounty signal and manually verify compensation.'
  )
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  source_kind = EXCLUDED.source_kind,
  base_url = EXCLUDED.base_url,
  attribution_required = EXCLUDED.attribution_required,
  policy_notes = EXCLUDED.policy_notes,
  enabled = true;
