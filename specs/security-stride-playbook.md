# Security & Hardening Playbook — STRIDE Threat Model

**Product:** ObserveCo (and all future software projects)
**Status:** Living — update as lessons accumulate
**Version:** 1.0 — 2026-06-12
**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 1.0 | 2026-06-12 | Initial creation — adapted from Addy Osmani's agent-skills security-and-hardening pattern + OWASP LLM Top 10 2025 |

**Source:** Real risk — ObserveCo handles authentication, payment data, PII, and LLM agent outputs. A systematic security framework prevents ad-hoc coverage gaps.

This playbook sits **alongside** coding-fidelity-playbook.md. It catches the class of problem where the code works perfectly but is insecure.

---

## 1. Thesis

**Treat every external input as hostile, every secret as sacred.** Security is not a post-launch add-on — it's a design constraint that must be present from Phase 1 (SPECIFY).

The STRIDE threat model provides systematic coverage. The 3-tier boundary system removes ambiguity about what agents can decide autonomously.

---

## 2. STRIDE Threat Model

Run STRIDE on every feature that handles user input, auth, data storage, external integrations, or LLM output.

| # | Threat | What it means | Prevention |
|---|--------|--------------|------------|
| S | **Spoofing** | Impersonating a user or system | Authentication, signature verification, mTLS |
| T | **Tampering** | Modifying data in transit or at rest | Integrity checks, parameterized queries, HTTPS |
| R | **Repudiation** | Denying actions | Audit logging, immutable logs |
| I | **Information Disclosure** | Leaking sensitive data | Encryption, field allowlists, generic errors |
| D | **Denial of Service** | Overwhelming the system | Rate limiting, input size caps, timeouts |
| E | **Elevation of Privilege** | Doing things you shouldn't | Authorization checks, least privilege |

### How to Apply STRIDE

For every new feature:

1. **Map trust boundaries** — Where does untrusted data enter?
   - HTTP requests, forms, file uploads, webhooks
   - Third-party APIs, message queues
   - **LLM output** (always untrusted)

2. **Name the assets** — What's worth stealing?
   - Credentials, PII, payment data
   - Admin actions, API keys
   - Session tokens, JWT secrets

3. **Write abuse cases next to use cases**
   ```
   USE CASE: User submits feedback
   ABUSE CASE: User submits feedback with SQL injection payload
   ABUSE CASE: User submits 10GB feedback to exhaust storage
   ABUSE CASE: User submits feedback impersonating another user
   ```

4. **Apply STRIDE per element** — For each trust boundary, check all 6 threats

---

## 3. The 3-Tier Boundary System

### Always Do (8 items)
1. Validate all external input at boundaries
2. Parameterize all database queries (never string concatenation)
3. Encode output (XSS prevention)
4. Use HTTPS everywhere
5. Hash passwords with bcrypt/scrypt/argon2 (salt rounds ≥ 12)
6. Set security headers (CSP, X-Frame-Options, etc.)
7. Use httpOnly + secure + sameSite cookies
8. Run `npm audit` / `pip-audit` before every release

### Ask First (7 items)
1. New authentication flows
2. New sensitive data categories
3. New external integrations
4. Changing CORS configuration
5. File upload handlers
6. Modifying rate limiting
7. Granting elevated permissions

### Never Do (7 items)
1. Never commit secrets or credentials
2. Never log sensitive data (passwords, tokens, PII)
3. Never trust client-side validation alone
4. Never disable security headers
5. Never use `eval()` or `innerHTML` with user data
6. Never store sessions in localStorage
7. Never expose stack traces to users

---

## 4. OWASP Prevention Patterns

### Injection
- Parameterized queries **always**
- Never string concatenation for SQL
- Validate and sanitise all input before processing

### Broken Authentication
- bcrypt with salt rounds ≥ 12
- Secure session cookies (httpOnly, secure, sameSite)
- Implement account lockout after failed attempts
- Use MFA for sensitive operations

### Cross-Site Scripting (XSS)
- Framework auto-escaping (React, Jinja2, etc.)
- Sanitise with DOMPurify if you must render HTML
- Content Security Policy headers
- Never use `innerHTML` with user input

### Broken Access Control
- Check authorization (not just authentication) on every endpoint
- Ownership verification: `task.ownerId !== req.user.id`
- Deny by default — explicit allow lists
- Log all access control failures

### Security Misconfiguration
- Restrictive CSP headers
- CORS restricted to known origins
- Disable directory listing
- Remove default credentials

### Sensitive Data Exposure
- Sanitise API responses (remove `passwordHash`, `resetToken`)
- Environment variables for secrets
- `.env.example` committed, `.env` never committed
- Encrypt sensitive data at rest

### SSRF
- Allowlist scheme + host
- Resolve all DNS records; reject if ANY resolved IP is private
- Forbid redirects
- Note TOCTOU gap with short-TTL DNS rebinding

---

## 5. OWASP LLM Top 10 (2025)

For ObserveCo's agent ecosystem — LLM output is **untrusted input**.

| # | Threat | Prevention |
|---|--------|------------|
| LLM01 | **Prompt Injection** | Enforce permissions in code, not system prompt. Never trust LLM to enforce its own rules. |
| LLM02 | **Sensitive Information Disclosure** | Keep secrets and other users' data out of prompts. Audit what enters the context window. |
| LLM05 | **Improper Output Handling** | Treat model output as untrusted input — never pass into eval/SQL/shell/innerHTML without validation. |
| LLM06 | **Excessive Agency** | Constrain tool/agent permissions. Require confirmation for destructive actions. Least privilege. |
| LLM08 | **Vector Store Weakness** | Partition vector store per tenant. Validate documents before indexing. |
| LLM10 | **Unbounded Consumption** | Cap tokens, request rate, loop depth. Implement circuit breakers. |

### Agent-Specific Rules
- Agent output that touches the database **must** be validated before execution
- Agent output that sends messages **must** be reviewed before delivery
- Agent output that modifies files **must** produce a diff for human review
- No agent can modify its own permissions or other agents' permissions

---

## 6. npm Audit / pip-audit Decision Tree

| Severity | Reachable? | Action |
|----------|-----------|--------|
| Critical/High | Yes | Fix immediately — block release |
| Critical/High | No (dev-only) | Fix soon, not a blocker |
| Moderate | Yes | Next release cycle |
| Low | Any | Track for regular updates |

---

## 7. Verification Checklist

- [ ] STRIDE run on all new features handling external input
- [ ] Abuse cases written next to use cases
- [ ] All external input validated at boundaries
- [ ] All database queries parameterized
- [ ] No secrets in code or git history
- [ ] Security headers present and restrictive
- [ ] Auth checks on every protected endpoint
- [ ] No internal details in error responses
- [ ] Rate limiting on auth endpoints
- [ ] No SSRF vectors
- [ ] LLM output validated before use
- [ ] `npm audit` / `pip-audit` clean before release
- [ ] `.env` never committed, `.env.example` committed

---

## 8. Integration with Existing Playbooks

| Playbook | How this integrates |
|----------|-------------------|
| spec-gated-workflow-playbook.md | STRIDE runs during Phase 1 (SPECIFY). Abuse cases written in the spec. |
| coding-fidelity-playbook.md | 3-tier boundaries checked during code review |
| agent-governance-playbook.md | LLM-specific rules enforced via agent permissions |
| system-design-testing-playbook.md | Security tests added to system design verification |
| master-fidelity-gate.md | Security checks integrated into the master gate's Layer A (Requirements) and Layer D (System Design) |
| ux-testing-playbook.md | Security warnings (C4 accessibility, data privacy) feed into UX perception checks |
| orchestration-anti-patterns-playbook.md | Multi-agent communication channels are STRIDE-threat-mapped |
| ui-testing-playbook.md | UI-level security concerns (XSS in rendered output, CSP headers) verified in ui-testing |
