# Security policy

## Supported version

Security fixes are applied to the latest version on the default branch.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities, exposed credentials, or personal data. Use the
repository's private GitHub security-advisory form instead:

`Security` → `Advisories` → `Report a vulnerability`

Include the affected component, reproduction steps, likely impact, and any suggested mitigation.
Do not include live API keys, access tokens, passwords, private email contents, or personal data.

## If a secret is exposed

1. Revoke or rotate the secret at its provider immediately.
2. Stop affected services and review provider and application logs.
3. Remove the secret from Git history, forks, artifacts, logs, and cached workflow exports.
4. Replace local credentials and restart the affected services.
5. Document the incident without reproducing the secret.

Git history rewriting does not invalidate a credential. Rotation is mandatory.

## Security boundary

FREELY drafts opportunities and proposals for human review. It must not submit bids, message
clients, bypass platform controls, or use marketplace session cookies. Keep production secrets in
the local `.env` file or a dedicated secret manager and never in source-controlled workflow JSON.
