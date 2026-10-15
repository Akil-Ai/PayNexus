# PayNexus Threat Model & Compliance Mapping

## 1. STRIDE Analysis Summary

| Threat Category | Description | PayNexus Countermeasure |
|---|---|---|
| **Spoofing** | Attacker impersonates legitimate user or machine client | JWT tokens signed with HS256/RS256, secure hashed API keys with `paynexus_live_` prefix and SHA-256 validation. |
| **Tampering** | Malicious insider modifies transaction amounts or ledger entries | Append-only double-entry ledger where entries are immutable; cryptographic SHA-256 hash chain on `audit_log` with database triggers blocking UPDATE/DELETE. |
| **Repudiation** | Customer denies authorizing a high-value transfer | Full correlation ID tracking, IP & user-agent logging, four-eyes maker-checker approval audit records. |
| **Information Disclosure** | Leakage of account numbers, card PANs, or PII | Field-level Fernet / AES-128-CBC encryption on account and card data; automated masking (`XXXX-XXXX-1234`) across all logs, APIs, and UI drawers. |
| **Denial of Service** | Flooding duplicate payments or crashing rails | Redis token-bucket rate limiting per client; circuit breaker per rail adapter to prevent cascade resource exhaustion. |
| **Elevation of Privilege** | Merchant accesses compliance queue or audit tamper controls | Strict Role-Based Access Control (RBAC) dependency factory enforcing ADMIN, COMPLIANCE_OFFICER, OPERATIONS, AUDITOR, and MERCHANT boundaries. |

---

## 2. PCI-DSS v4.0 Control Mapping

- **Requirement 3 (Protect Account Data)**: Account numbers and PANs are encrypted at rest using Fernet encryption keys injected via environment variables. Masked display enforced in API and UI.
- **Requirement 7 & 8 (Access Control & Identification)**: Passwords hashed with Argon2id; JWT access tokens short-lived (60 min); strict RBAC.
- **Requirement 10 (Log and Monitor All Access)**: Append-only cryptographic audit logging of all state transitions, approvals, and configuration changes with automated tamper detection.

---

## 3. OWASP API Security Top 10 (2023) Alignment

- **API1:2023 Broken Object Level Authorization**: Ownership verification on customer and account records.
- **API2:2023 Broken Authentication**: OAuth2 password flow with refresh token rotation and argon2 password verification.
- **API4:2023 Unrestricted Resource Consumption**: Redis-backed rate limiting per IP and API client key.
- **API8:2023 Security Misconfiguration**: CORS restricted to configured domains, security headers enforced, RFC 7807 problem+json error masking.
