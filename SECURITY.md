# Security Policy

## Supported Versions

Only the latest released version of `strands-apify` receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in `strands-apify`, please **do not** open a
public GitHub issue. Instead, report it privately so we can investigate and ship a fix
before the details become public.

Preferred channels:

1. **GitHub Security Advisories** - [Report a vulnerability](https://github.com/apify/strands-apify/security/advisories/new)
   (private, only repo maintainers can see it).
2. **Email** - `support@apify.com` with subject prefix `[security] strands-apify:`.

Please include:

- A description of the issue and the impact you anticipate.
- Steps to reproduce, ideally with a minimal proof of concept.
- The affected version of `strands-apify` and your Python version.
- Any suggested mitigation, if you have one.

We will acknowledge your report within **5 business days**, keep you updated as we
investigate, and credit you in the release notes once a fix ships (unless you prefer
to remain anonymous).

## Scope

This policy covers the `strands-apify` package itself. For vulnerabilities in:

- the underlying **Apify platform / Actors** - report to Apify per
  <https://apify.com/security>;
- the **Strands Agents SDK** - report upstream at
  <https://github.com/strands-agents/sdk-python>.
