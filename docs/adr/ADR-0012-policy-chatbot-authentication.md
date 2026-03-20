# ADR-0012: Policy Chatbot — Authentication and Authorization

> **Status:** Accepted
> **Date:** 2026-03-20
> **Deciders:** Platform Engineering, IT Security, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot serves ~8,000 employees and a small set of policy
administrators. All access must require SSO via Microsoft Entra ID (NFR-007).
Role-based access control must enforce: employees see published policy content,
administrators manage documents and view analytics, and no user can access
another user's conversation history (NFR-010).

The system must also retrieve employee profile data (name, department, location,
manager) from the corporate directory for personalized responses (FR-011).

---

## Decision

> We will use **Microsoft Entra ID** for SSO authentication with **OAuth 2.0 /
> OIDC** token-based authorization, because it is the corporate identity
> provider and provides native integration with Microsoft Teams, the intranet,
> and Azure PaaS services.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Authentication | SSO via corporate IdP (NFR-007) | Microsoft Entra ID / OIDC | ✅ |
| Authorization | RBAC (NFR-010) | Entra ID app roles | ✅ |
| TLS | TLS 1.2+ (NFR-011) | Enforced by ACA ingress | ✅ |
| Secrets | Azure Key Vault | Client secret in Key Vault; Managed Identity for service-to-service | ✅ |

---

## Options Considered

### Option 1: Microsoft Entra ID (OAuth 2.0 / OIDC) ← Chosen

**Description:** Register an Entra ID application with two app roles (`Employee`,
`Admin`). Web chat and Teams bot authenticate via OIDC. The FastAPI backend
validates JWT bearer tokens issued by Entra ID and extracts roles from the
token claims. Microsoft Graph API provides employee profile data.

**Pros:**
- Native corporate SSO — single sign-on for all 8,000 employees via existing
  Entra ID accounts
- App roles in the JWT token enable role-based access without a separate
  authorization database
- Microsoft Teams bot authentication is built on Entra ID — seamless integration
- Microsoft Graph API provides employee profile data (name, department, location,
  manager) for FR-011
- Token-based auth is stateless — scales horizontally across ACA replicas without
  shared session state for auth

**Cons:**
- Requires Entra ID app registration with admin consent for Graph API permissions
- JWT validation adds ~1–2ms per request (negligible)

---

### Option 2: Entra ID + Custom RBAC Database

**Description:** Use Entra ID for authentication only, with a custom
authorization layer backed by a `user_roles` table in PostgreSQL.

**Pros:**
- More granular permission model — can define custom roles beyond Employee/Admin
- Roles can be managed without Entra ID admin access

**Cons:**
- Duplicates work already provided by Entra ID app roles
- Additional database table and management API to maintain
- Roles would be out of sync with Entra ID group memberships
- Over-engineered for two roles (Employee, Admin)

---

### Option 3: API Key Authentication

**Description:** Issue API keys to clients; validate keys server-side.

**Pros:**
- Simple implementation

**Cons:**
- Not SSO — violates NFR-007
- No integration with corporate identity
- Key management burden across 8,000 employees
- No user identity for personalization (FR-011)
- Not a viable option for this use case

---

## Authentication Flow

### Web Chat Widget
```
Employee Browser ──── Entra ID OIDC ────▶ Entra ID
       │                                      │
       │◀──── ID Token + Access Token ────────┘
       │
       │──── API Call + Bearer Token ─────▶ FastAPI
       │                                      │
       │                                      ├── Validate JWT signature
       │                                      ├── Check audience/issuer
       │                                      ├── Extract roles claim
       │                                      └── Allow/deny based on role
```

### Microsoft Teams Bot
```
Teams Client ──── Bot Framework ────▶ Azure Bot Service
       │                                    │
       │                                    ├── Entra ID token validation
       │                                    └── Forward to FastAPI with
       │                                        user context (UPN, name, etc.)
       │
       │◀──── Bot response ────────────────┘
```

### Service-to-Service (Backend → Azure Services)
```
FastAPI (ACA) ──── Managed Identity ────▶ Azure OpenAI
                                         Azure AI Search
                                         Azure Blob Storage
                                         Azure PostgreSQL
                                         Azure Cache for Redis
                                         Azure Key Vault
```

## RBAC Model

| Role | Source | Permissions |
|------|--------|-------------|
| `Employee` | Entra ID app role (default) | Chat API, feedback, own conversation history |
| `Admin` | Entra ID app role (assigned) | All employee permissions + document management, re-indexing, analytics, test queries, coverage reports |

### Endpoint Authorization Matrix

| Endpoint Group | Employee | Admin |
|----------------|----------|-------|
| `POST /v1/chat` | ✅ | ✅ |
| `GET /v1/conversations/*` | ✅ (own only) | ✅ (own only) |
| `POST /v1/feedback` | ✅ | ✅ |
| `GET /v1/admin/documents/*` | ❌ | ✅ |
| `POST /v1/admin/documents` | ❌ | ✅ |
| `POST /v1/admin/reindex` | ❌ | ✅ |
| `GET /v1/admin/analytics/*` | ❌ | ✅ |
| `POST /v1/admin/test-query` | ❌ | ✅ |
| `GET /v1/admin/coverage` | ❌ | ✅ |
| `GET /health`, `GET /ready` | Public | Public |

---

## Consequences

### Positive
- Zero password management — leverages existing corporate SSO
- Consistent identity across web chat, Teams, and admin console
- Managed Identity for service-to-service eliminates all secrets for Azure
  resource access
- Graph API integration provides personalization data without a separate
  user directory

### Negative / Trade-offs
- Depends on Entra ID availability — if Entra ID is down, no authentication
  is possible (acceptable given corporate dependency on Entra ID for all systems)
- App registration requires IT admin involvement for initial setup and consent

### Risks
- Graph API permission scope may require admin consent — mitigated by requesting
  only `User.Read` (delegated) for user profile data
- Token expiry handling — mitigated by standard OIDC token refresh flow in the
  web client and Teams SDK

---

## Implementation Notes

- **Entra ID app registration:** one registration with redirect URIs for web
  chat and implicit flow disabled (authorization code flow with PKCE)
- **App roles:** define `Employee` and `Admin` in the app manifest
- **FastAPI dependency:** create a `get_current_user` dependency that validates
  JWT, extracts UPN, name, roles, and department from token claims
- **Graph API client:** `msgraph-sdk` or direct HTTP calls to
  `https://graph.microsoft.com/v1.0/me` for profile enrichment
- **Admin guard:** FastAPI dependency `require_admin` checks for `Admin` role
  in token claims
- **SDKs:** `azure-identity` (DefaultAzureCredential for Managed Identity),
  `PyJWT` or `python-jose` for JWT validation, `msal` for OIDC flows in
  integration tests

---

## References
- [Microsoft Entra ID app registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)
- [FastAPI OAuth2 with Entra ID](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-web-api-aspnet-core)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/overview)
- Related requirements: FR-011, NFR-007, NFR-010, NFR-011
- Related ADRs: ADR-0007 (language/framework), ADR-0008 (compute)
