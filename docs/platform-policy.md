# Platform policy boundary

The default Scout calls the Remote OK public feed. Every delivered item must name the source and
retain its canonical application URL.

Freelancer.com may only be enabled after express written permission for automated API access has
been obtained and an OAuth token has been issued. Its adapter may search active projects through
the official API only. Cached data must be refreshed at least every 24 hours, encrypted at rest in
production, and retained only to the extent permitted by Freelancer's API terms and the written
permission. Revoking permission requires disabling the adapter and deleting Freelancer API data
as required by those terms.

The system must not:

- automate a browser on a freelance marketplace;
- use session cookies or page HTML as an unofficial API;
- bypass bot detection, CAPTCHAs, rate limits, or access controls;
- submit, boost, or withdraw proposals;
- contact clients or send follow-ups automatically;
- store marketplace data beyond the source's permitted retention period.
- call Freelancer bid, message, award, payment, or account mutation endpoints;

Any new source requires a policy review before its adapter is enabled.
