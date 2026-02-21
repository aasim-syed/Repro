
## 3) `SECURITY.md`
```md
# Security Policy

## Reporting a Vulnerability
Please open a GitHub Security Advisory or email the maintainer.

## Trace safety / secrets
AgentReplay records inputs/outputs. Do NOT record secrets.
Use redaction hooks and avoid storing:
- API keys/tokens
- passwords
- authorization headers
- private files/content

If you suspect secrets were recorded:
1) delete the DB / exported artifacts
2) rotate the secrets
