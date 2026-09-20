INSERT INTO platforms (slug, name, source_kind, base_url, attribution_required, policy_notes)
VALUES (
  'freelancer',
  'Freelancer.com',
  'official_oauth_api',
  'https://www.freelancer.com',
  true,
  'Disabled by default. Enable only with Freelancer express written permission and an OAuth token. Search projects only; never place bids automatically.'
)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  source_kind = EXCLUDED.source_kind,
  base_url = EXCLUDED.base_url,
  attribution_required = EXCLUDED.attribution_required,
  policy_notes = EXCLUDED.policy_notes;
