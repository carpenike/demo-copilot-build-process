# ADR-0004: Platform Authentication & Authorization Strategy

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, IT Security
> **Scope:** All projects

---

## Context

All services on the platform require authentication and authorization. Rather
than each project selecting its own identity provider and auth pattern, this ADR
establishes **Microsoft Entra ID (OAuth 2.0 / OIDC)** as the standard identity
provider and defines the common auth patterns that all services must follow.

Project-level ADRs may extend this with application-specific role definitions
and data-scoping rules, but the identity provider and auth flow are fixed.

Key platform requirements:
- SSO authentication via Microsoft Entra ID (corporate identity)
- Role-based access control (RBAC) enforced at the application level
- Audit logging of all authenticated actions with actor, timestamp, and IP
- TLS 1.2+ on all auth flows
- API gateway (Azure API Management) in front of all public endpoints

---

## Decision

> All services MUST authenticate users via **Microsoft Entra ID (OAuth 2.0 / OIDC)**
> using the Authorization Code flow with PKCE. Application-level RBAC is enforced
> by each service's backend, with roles derived from authoritative data sources
> (e.g., Workday, HR systems) or assigned via admin panels.

Project-level ADRs define the specific roles, data-scoping rules, and any
extended auth patterns (e.g., email action tokens) for their service.

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

**Description:** Users authenticate via Entra ID using the Authorization Code flow (PKCE). Each service's backend validates ID tokens and maintains its own roles/permissions model to enforce access rules.

**Pros:**
- Leverages existing corporate identity — no user provisioning needed
- Application-level RBAC allows fine-grained rules that Entra ID groups cannot express
- Standard OIDC — well-supported by Python (`authlib`, `python-jose`) and Go libraries
- Consistent auth pattern across all services

**Cons:**
- Each service must implement token validation and RBAC enforcement
- Role assignments are maintained per-service, not centrally in Entra ID

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

### Standard Auth Flow (all services)
1. User navigates to service → redirected to Entra ID login (Authorization Code + PKCE)
2. Entra ID returns authorization code → backend exchanges for ID token + access token
3. Backend validates ID token (signature, issuer, audience, expiry)
4. Backend looks up user in local DB (matched by Entra ID OID) → loads roles
5. Session established (server-side session with secure, HttpOnly, SameSite cookie)

### Key Libraries
- **Python:** `authlib` for OIDC client, `python-jose` for JWT validation, FastAPI dependency injection for auth middleware
- **Go:** `coreos/go-oidc` for OIDC client, `golang-jwt/jwt` for JWT validation

---

## References
- [Microsoft Entra ID OIDC documentation](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc)
- `governance/enterprise-standards.md` — Security Policy
- Related: ADR-0001 (language), ADR-0002 (data storage)
