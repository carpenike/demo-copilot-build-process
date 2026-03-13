# ADR-0006: Authentication & Authorization for Expense Portal

> **Status:** Proposed
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, IT Security, Finance Systems Team
> **Project:** expense-portal (FIN-EXP-2026)

---

## Context

The Expense Portal requires:
- SSO authentication via Microsoft Entra ID (NFR-007)
- Role-based access control with data isolation: employees see only their own reports, managers see only direct reports' submissions (NFR-008)
- Segregation of duties: submitters cannot approve their own reports (NFR-015)
- Email action links for approvals must be secure against CSRF and replay (GF-007)
- Audit logging of all approval actions with actor, timestamp, and IP address (NFR-011)
- ~2,400 users with 3 roles: Employee, Manager (also an Employee), Finance Administrator

Related requirements: NFR-007, NFR-008, NFR-011, NFR-015, FR-008, FR-010, FR-024.

---

## Decision

> We will use **Microsoft Entra ID (OAuth2 / OIDC)** for authentication, with **application-level RBAC** enforced by the FastAPI backend, because all users already have Entra ID credentials and the role/data-scoping rules are specific to this application.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Authentication | SSO via corporate IdP | Microsoft Entra ID OIDC | ✅ |
| TLS | 1.2+ for all communication | OIDC flows over TLS 1.2+ | ✅ |
| API gateway | Azure API Management for public endpoints | Portal behind APIM | ✅ |
| Secrets | Azure Key Vault | Client secret / cert in Key Vault | ✅ |

---

## Options Considered

### Option 1: Entra ID OIDC + Application-Level RBAC ← Chosen

**Description:** Users authenticate via Entra ID using the Authorization Code flow (PKCE). The FastAPI backend validates ID tokens and maintains a local roles table (synced from Workday) to enforce row-level data access.

**Pros:**
- Leverages existing corporate identity — no user provisioning needed
- Application-level RBAC allows fine-grained rules (e.g., "manager can only see direct reports") that Entra ID groups cannot express
- Workday sync (FR-016) already provides manager hierarchy — RBAC derives from this data
- Standard OIDC — well-supported by Python libraries (`authlib`, `python-jose`)

**Cons:**
- Role assignments are maintained in the application database (derived from Workday sync), not centrally in Entra ID
- Requires careful implementation to prevent privilege escalation

---

### Option 2: Entra ID with App Roles + Groups

**Description:** Define roles (Employee, Manager, Finance Admin) as Entra ID App Roles and assign users via Entra ID groups.

**Pros:**
- Centralized role management in Entra ID

**Cons:**
- Cannot express data-level scoping ("manager X can only see reports from employees A, B, C") — this requires manager hierarchy from Workday
- Group membership changes would need to be synchronized with Workday hierarchy changes — adds a second sync dependency
- Finance Admin role is fine for group-based assignment, but manager-to-employee mapping must still come from Workday

---

## Consequences

### Positive
- Single sign-on experience — users authenticate with existing corporate credentials
- Data-level access control derived from authoritative HR data (Workday)
- Audit trail captures Entra ID subject (OID), not just a username

### Negative / Trade-offs
- Application must validate tokens and enforce all access rules — no delegation to infrastructure
- If Workday sync fails, role/hierarchy data could become stale (mitigated by sync failure alerting in US-010)

### Risks
- Token theft via email action links. **Mitigation:** Email approval links use single-use, time-bounded tokens (30-minute expiry) stored in the database — not session tokens. Tokens are invalidated after first use. Links require the user to be authenticated via SSO before the action is executed.

---

## Implementation Notes

### Roles

| Role | Source | Permissions |
|------|--------|-------------|
| Employee | All authenticated users | Create/view/edit own reports; view own dashboard |
| Manager | Derived from Workday hierarchy (has direct reports) | All Employee permissions + approve/reject direct reports' submissions; view team dashboard |
| Finance Reviewer | Assigned via admin panel | All Employee permissions + review high-value reports; view finance dashboard; export reports |
| Finance Administrator | Assigned via admin panel | All Finance Reviewer permissions + manage policy rules, categories, thresholds |

### Auth Flow
1. User navigates to portal → redirected to Entra ID login (Authorization Code + PKCE)
2. Entra ID returns authorization code → backend exchanges for ID token + access token
3. Backend validates ID token (signature, issuer, audience, expiry)
4. Backend looks up user in local DB (matched by Entra ID OID) → loads roles + hierarchy
5. Session established (server-side session with secure, HttpOnly, SameSite cookie)

### Email Action Links
1. When an approval notification is sent, a single-use token is generated (cryptographically random, 256-bit)
2. Token is stored in DB with: report_id, action (approve/reject), expiry (30 minutes), used (boolean)
3. Link format: `https://expenses.acme.com/v1/actions/{token}`
4. When clicked: validate token exists, not expired, not used → require SSO authentication → execute action → mark token used

### Key Libraries
- `authlib` for OIDC client
- `python-jose` for JWT validation
- FastAPI dependency injection for auth middleware

---

## References
- [Microsoft Entra ID OIDC documentation](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc)
- Related ADRs: ADR-0004 (language), ADR-0005 (data storage)
- Related requirements: NFR-007, NFR-008, NFR-011, NFR-015, FR-008, FR-010
