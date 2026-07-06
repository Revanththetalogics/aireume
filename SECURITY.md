# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.0.x   | ✅         |
| < 2.0   | ❌         |

## Reporting a Vulnerability

We take the security of ARIA seriously. If you believe you have found a security
vulnerability, please report it to us responsibly.

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email **security@thetalogics.com** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept if possible)
- Affected version(s) and environment details
- Any suggested remediation

### What to expect

- **Acknowledgement** within 3 business days.
- **Initial assessment** and severity classification within 7 business days.
- **Status updates** at least every 10 business days until resolution.
- **Coordinated disclosure**: we will agree on a disclosure timeline with you,
  typically within 90 days of the report.

### Scope

In scope:
- The ARIA backend API (`app/backend`)
- The ARIA frontend (`app/frontend`)
- The voice agent (`app/voice_agent`)
- Deployment/configuration in this repository

Out of scope:
- Denial-of-service via volumetric attacks
- Findings from automated scanners without a demonstrated exploit
- Social engineering of ThetaLogics staff or customers

## Safe Harbor

We will not pursue legal action against researchers who:
- Make a good-faith effort to avoid privacy violations, data destruction, and
  service disruption.
- Report vulnerabilities promptly and do not exploit them beyond what is
  necessary to demonstrate the issue.
- Do not disclose the issue publicly before we have had a chance to remediate.

Thank you for helping keep ARIA and its users safe.
