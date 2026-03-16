# ADR-0011: Authentication & Authorization — Policy Chatbot

> **Status:** Proposed
> **Date:** 2026-03-16
> **Deciders:** Platform Engineering, IT Security
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot serves ~8,000 employees across two channels (Microsoft Teams
and a web chat widget) and includes an admin console for policy administrators.
The system must:

- Authenticate all users via corporate SSO (NFR-007)
- Retrieve employee profile data (name, department, location) for personalized
  responses (FR-011)
- Enforce role-based access control: employees vs. administrators (NFR-010)
- Prevent cross-user conversation history access (NFR-010)
- Integrate with Microsoft Teams bot authentication
- Protect admin console endpoints (FR-031, FR-032, FR-033)

All employees have Microsoft Entra ID credentials and Teams licenses
(Assumption #1).

---

## Decision

> We will use **Microsoft Entra ID** for authentication via MSAL (Microsoft
> Authentication Library) with OAuth 2.0 / OpenID Connect, and implement
> role-based access control using Entra ID App Roles for employee vs.
> administrator authorization.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Authentication | Microsoft Entra ID SSO | Entra ID OIDC | ✅ |
| TLS | 1.2+ required | All auth flows over TLS 1.2+ | ✅ |
| Secrets | Azure Key Vault only | Client secrets in Key Vault | ✅ |
| No public endpoints without API gateway | Security Policy | Azure API Management | ✅ |

Reference: `governance/enterprise-standards.md` — Security Policy

---

## Options Considered

### Option 1: Microsoft Entra ID + MSAL + App Roles ← Chosen

**Description:** Register an Entra ID application with two App Roles
(`Employee` and `Administrator`). Use MSAL Python library for token validation
in FastAPI. Use the Microsoft Teams Bot Framework SSO for Teams channel
authentication.

**Pros:**
- Native integration with the corporate identity provider — every employee
  already has credentials (Assumption #1)
- App Roles provide a clean RBAC model mapped directly to NFR-010
- MSAL Python SDK handles token acquisition, validation, and refresh
- Microsoft Graph API provides employee name, department, location, and manager
  for personalization (FR-011) using the same auth token
- Teams Bot Framework SSO enables seamless authentication in the Teams channel
  without additional login prompts
- Token-based auth works well with the stateless FastAPI architecture

**Cons:**
- App Role assignment requires Entra ID admin action to assign the
  `Administrator` role to policy team members (operational, not technical)

---

### Option 2: Entra ID + custom RBAC in PostgreSQL

**Description:** Use Entra ID for authentication but store role assignments in
a PostgreSQL `user_roles` table.

**Pros:**
- More flexible role management without Entra ID admin involvement

**Cons:**
- Duplicates identity management — role state split between Entra ID and PostgreSQL
- Increases surface area for authorization bugs
- Loses the benefit of Entra ID's built-in App Role assignment and audit trail

---

### Option 3: API key authentication for service-to-service

**Description:** Use static API keys for internal service communication.

**Pros:**
- Simple to implement

**Cons:**
- Does not meet NFR-007 (SSO required for all access)
- API keys cannot represent individual users for RBAC or personalization
- Secret rotation is more complex than token-based auth

---

## Authentication Flows

### Web Chat Widget
```
Employee → Web Widget → Entra ID OIDC Login → Access Token (JWT)
                         → FastAPI validates JWT via MSAL → Authorized
                         → Graph API call for profile data (FR-011)
```

### Microsoft Teams Bot
```
Employee → Teams → Bot Framework → SSO Token Exchange → Entra ID
                    → FastAPI receives validated bot token → Authorized
                    → Graph API call for profile data (FR-011)
```

### Admin Console
```
Admin → Admin UI → Entra ID OIDC Login → Access Token with `Administrator` App Role
                    → FastAPI validates JWT + checks `Administrator` role → Authorized
```

## RBAC Model

| App Role | Permissions | Assigned To |
|----------|-------------|-------------|
| `Employee` | Chat with bot, view own conversation history, provide feedback | All employees (default) |
| `Administrator` | All Employee permissions + upload/retire documents, trigger re-indexing, test queries, view analytics, view coverage report | Policy team members |

---

## Consequences

### Positive
- Single identity provider for all channels (web, Teams, admin)
- App Roles provide auditable, centralized role management
- Graph API integration gives personalization data without a separate user profile store
- No passwords or API keys stored in the application

### Negative / Trade-offs
- Requires Entra ID admin to assign the `Administrator` App Role to policy
  team members — adds an onboarding step
- Graph API calls add ~100ms latency per first request in a session (mitigated:
  cache profile data in Redis for the session duration)

### Risks
- Token expiry during long chat sessions — mitigated by MSAL automatic token
  refresh and a 1-hour session timeout in the web widget
- Graph API throttling under high load — mitigated by caching profile data
  in Azure Cache for Redis

---

## Implementation Notes

- Register one Entra ID application with:
  - Redirect URIs for web widget and admin console
  - API permissions: `User.Read` (Graph API for profile data)
  - App Roles: `Employee`, `Administrator`
- FastAPI middleware: validate JWT on every request using `msal` Python package
- Store Entra ID client secret in Azure Key Vault (referenced via ACA secrets)
- Teams bot: use `botbuilder-core` Python SDK with SSO token exchange
- Profile data caching: store `{user_id: {name, department, location}}` in
  Azure Cache for Redis with 24-hour TTL
- Conversation isolation: all conversation queries filtered by `user_id`
  extracted from the validated JWT

---

## References
- `governance/enterprise-standards.md` — Security Policy
- `docs/adr/ADR-0004-platform-authentication.md` — expense-portal Entra ID precedent
- Related: ADR-0007 (language), ADR-0008 (compute platform)
- Related requirements: FR-007, FR-011, FR-031–FR-033, NFR-007, NFR-010
