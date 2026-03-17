# ADR-0011: Policy Chatbot — Authentication & Bot Integration

> **Status:** Proposed
> **Date:** 2026-03-17
> **Deciders:** Platform Engineering
> **Project:** policy-chatbot

---

## Context

The policy chatbot requires two client interfaces (FR-007):
1. **Microsoft Teams bot** — primary channel for most employees
2. **Web chat widget** — embedded in the corporate intranet

Both channels must authenticate via corporate SSO (NFR-007, Microsoft Entra ID)
and support role-based access control (NFR-010: employee vs. administrator).

Additionally, the admin console requires authenticated access restricted to users
with the "PolicyAdmin" role.

The system must retrieve employee profile data (name, department, location, role)
from Microsoft Entra ID / Microsoft Graph API for personalization (FR-011).

---

## Decision

> We will use **Azure Bot Service** with the **Microsoft Bot Framework SDK for
> Python** to handle Teams and web chat channels, with **Microsoft Entra ID
> (OAuth 2.0 / OIDC)** for authentication across all interfaces.

### Channel Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  MS Teams   │────▶│  Azure Bot       │────▶│  Policy Chatbot  │
│  Client     │     │  Service         │     │  API (FastAPI)   │
└─────────────┘     │  (Bot Framework) │     │                  │
                    └──────────────────┘     │  /api/messages   │
                                             │  /api/v1/...     │
┌─────────────┐     ┌──────────────────┐     │  /api/admin/...  │
│  Intranet   │────▶│  Web Chat        │────▶│                  │
│  Widget     │     │  (Direct Line)   │     └──────────────────┘
└─────────────┘     └──────────────────┘

┌─────────────┐
│  Admin SPA  │──── Entra ID OIDC ────▶ /api/admin/...
│  (intranet) │
└─────────────┘
```

### Authentication Flows

| Interface | Auth Method | Token Audience |
|-----------|-------------|----------------|
| Teams bot | Bot Framework SSO (Entra ID token exchange) | Bot app registration |
| Web chat widget | Entra ID OIDC via Direct Line token | Bot app registration |
| Admin console API | Entra ID OAuth 2.0 Bearer token | API app registration |
| Service-to-service | Managed Identity | Azure resource-specific |

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Authentication | Microsoft Entra ID | Entra ID OIDC / OAuth 2.0 | ✅ |
| RBAC | Role-based access | Entra ID app roles (Employee, PolicyAdmin) | ✅ |
| TLS | TLS 1.2+ | Azure Bot Service enforces TLS 1.2+ | ✅ |
| Secrets | Azure Key Vault | Bot credentials in Key Vault | ✅ |
| CORS | Explicit origins only | Intranet domain only | ✅ |

---

## Options Considered

### Bot Framework

#### Option 1: Azure Bot Service + Bot Framework SDK (Python) ← Chosen

**Description:** Use the Microsoft Bot Framework SDK for Python to implement a
bot that handles both Teams and web chat via Azure Bot Service's channel
abstraction.

**Pros:**
- Microsoft first-party — consistent with Azure PaaS-first policy
- Single bot implementation serves both Teams and web chat channels
- Built-in Teams SSO support (token exchange flow)
- Direct Line API for web chat widget integration
- Handles Teams-specific features (adaptive cards, message extensions)
- Python SDK available (`botbuilder-core`, `botbuilder-integration-aiohttp`)

**Cons:**
- Bot Framework SDK adds a dependency layer over raw REST APIs
- Python SDK is less actively maintained than the C# version (but stable)

#### Option 2: Custom Teams webhook + Web API

**Description:** Build a custom Teams incoming/outgoing webhook and a separate
web chat API without Bot Framework.

**Pros:**
- No Bot Framework dependency

**Cons:**
- Must implement Teams message protocol handling manually
- Two separate channel implementations to maintain
- No built-in SSO token exchange for Teams
- Significantly more custom code for equivalent functionality

### Admin Console Authentication

#### Option A: Entra ID app roles ← Chosen

**Description:** Define "PolicyAdmin" as an Entra ID app role. The FastAPI admin
endpoints validate the role claim in the JWT token.

**Pros:**
- Centralized role management in Entra ID
- No custom auth database — inherits enterprise identity management
- Standard JWT validation in FastAPI middleware

**Cons:**
- Role assignment requires Entra ID admin action

#### Option B: Custom RBAC in PostgreSQL

**Pros:**
- Full control over role definitions

**Cons:**
- Duplicates identity management outside Entra ID
- Must sync with enterprise directory
- Violates principle of using Entra ID as the identity source of truth

---

## Consequences

### Positive
- Single bot serves both channels — reduced code duplication
- Authentication leverages existing enterprise Entra ID — no custom identity system
- Admin RBAC via Entra ID app roles — consistent with enterprise identity governance
- Managed Identity for service-to-service auth — no credentials in config

### Negative / Trade-offs
- Bot Framework SDK adds a framework dependency (mitigated by using stable v4 SDK)
- Bot Framework Python SDK has a slower release cadence than C# (acceptable — v4 is stable)

### Risks
- Teams SSO token exchange requires correct app registration configuration —
  must be validated during Development Sprint 2
- Mitigation: document app registration steps in deployment prerequisites

---

## Implementation Notes

### App Registrations (Entra ID)
1. **Bot registration** — for Azure Bot Service (Teams + Direct Line channels)
   - Redirect URIs for Teams SSO
   - API permissions: `User.Read` (Microsoft Graph) for profile data
2. **API registration** — for admin console endpoints
   - App roles: `Employee`, `PolicyAdmin`
   - Expose API with scope `access_as_user`

### FastAPI Integration
- Bot Framework messages handled at `/api/messages` endpoint
- Admin API endpoints at `/api/admin/...` with JWT Bearer auth middleware
- Chat API endpoints at `/api/v1/chat/...` with user context from bot auth

### Employee Profile Retrieval (FR-011)
- Use Microsoft Graph API (`/me` or `/users/{id}`) to retrieve:
  - `displayName`, `givenName` (greeting)
  - `department`, `jobTitle` (role-aware responses)
  - `officeLocation` (campus-specific policies, wayfinding)
- Cache profile data in Redis with 1-hour TTL

### Web Chat Widget
- Direct Line channel via Azure Bot Service
- Embed via iframe or Web Chat SDK (`botframework-webchat`)
- Token server endpoint to issue Direct Line tokens (avoids exposing secret in client)

---

## References
- ADR-0004: Platform Authentication (Entra ID standard)
- Governance: `governance/enterprise-standards.md` § Security Policy
- Requirements: FR-007, FR-011, FR-025–FR-026, NFR-007, NFR-010
