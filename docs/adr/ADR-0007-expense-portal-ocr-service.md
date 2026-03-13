# ADR-0007: OCR Service for Receipt Processing

> **Status:** Proposed
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, Finance Systems Team
> **Project:** expense-portal (FIN-EXP-2026)

---

## Context

The Expense Portal must apply OCR to uploaded receipt images (JPEG, PNG, PDF) and pre-populate expense line item fields (amount, vendor, date) when extraction confidence exceeds 85% (FR-004). OCR processing must complete within 10 seconds for files under 5 MB (NFR-002).

The system handles ~2,400 employees. Assuming an average of 2 expense reports per employee per month with 4 receipts each, peak OCR volume is approximately 19,200 receipts/month (~640/day, ~80/hour during business hours). This is low-to-moderate volume.

Related requirements: FR-003, FR-004, NFR-002.

---

## Decision

> We will use **Azure AI Document Intelligence (formerly Form Recognizer)** with the prebuilt receipt model because it provides receipt-specific extraction (amount, vendor, date) with confidence scores, runs in the Azure ecosystem, and requires no model training.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Infrastructure | Azure ecosystem | Azure AI Document Intelligence | ✅ |
| Secrets | Azure Key Vault | API key stored in Key Vault | ✅ |
| TLS | 1.2+ | Azure service endpoints enforce TLS 1.2 | ✅ |
| Language | Python | Azure SDK for Python (`azure-ai-documentintelligence`) | ✅ |

---

## Options Considered

### Option 1: Azure AI Document Intelligence — Prebuilt Receipt Model ← Chosen

**Description:** Azure's managed OCR/document extraction service with a prebuilt model specifically trained on receipts. Returns structured fields (merchant name, transaction date, total, line items) with per-field confidence scores.

**Pros:**
- Receipt-specific model — returns structured fields (amount, vendor, date) directly, not raw text
- Per-field confidence scores map directly to the 85% threshold requirement (FR-004)
- No model training or maintenance required
- Azure-native — private endpoint access from AKS VNet, managed scaling
- Processes JPEG, PNG, and PDF (all required formats)
- Well within 10-second SLA for files under 5 MB

**Cons:**
- Per-page pricing (~$0.01/page for prebuilt receipts) — at ~19,200 receipts/month, cost is ~$192/month (negligible)
- Vendor lock-in to Azure AI services

---

### Option 2: Tesseract OCR (self-hosted)

**Description:** Open-source OCR engine deployed as a sidecar or separate service in AKS.

**Pros:**
- No per-transaction cost
- No external service dependency

**Cons:**
- Returns raw text, not structured fields — requires custom NLP/regex to extract amount, vendor, date
- No built-in confidence scores per field — would need custom confidence estimation
- Lower accuracy on receipt images (varied fonts, layouts, backgrounds) without fine-tuning
- Operational burden: container management, scaling, model updates
- Significantly more development effort to match Azure Document Intelligence's accuracy

---

### Option 3: Google Cloud Document AI

**Description:** Google's managed document processing service.

**Pros:**
- High accuracy receipt extraction
- Structured field output with confidence scores

**Cons:**
- Not in the Azure ecosystem — adds cross-cloud network dependency
- Data egress to Google Cloud raises security and compliance concerns
- Additional credential management outside Azure Key Vault

---

## Consequences

### Positive
- Structured receipt data with confidence scores — minimal post-processing code needed
- No ML/NLP expertise required on the team
- Predictable per-transaction pricing at low cost for expected volume

### Negative / Trade-offs
- External service dependency — OCR fails if Azure AI Document Intelligence is unavailable
- Vendor lock-in — switching OCR providers would require adapter changes

### Risks
- Azure AI Document Intelligence regional outage. **Mitigation:** OCR is processed asynchronously via Celery. If the service is unavailable, the task retries with exponential backoff. Receipt upload succeeds immediately; OCR pre-fill is best-effort. Users can always enter fields manually.
- Confidence threshold may need tuning. **Mitigation:** The 85% threshold is configurable in the policy engine. If extraction quality varies by receipt type, the threshold can be adjusted without code changes.

---

## Implementation Notes

- **SDK:** `azure-ai-documentintelligence` Python package
- **Processing flow:**
  1. User uploads receipt → file saved to Azure Blob Storage (ADR-0005)
  2. Celery task queued for OCR processing (ADR-0008)
  3. Celery worker calls Document Intelligence `analyze_document` with the prebuilt-receipt model
  4. Worker extracts amount, vendor, date from response; checks confidence scores
  5. Fields with confidence ≥ 85% are saved as pre-filled values on the line item
  6. Frontend polls or receives WebSocket push to display pre-filled fields
- **API endpoint:** The receipt is uploaded to the backend; the backend submits it to Document Intelligence (the user's browser never calls Azure AI directly)
- **Timeout:** 10-second timeout on the Document Intelligence API call; if exceeded, mark OCR as failed and let the user enter fields manually

---

## References
- [Azure AI Document Intelligence — Receipt model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/receipt)
- Related ADRs: ADR-0004 (language), ADR-0005 (blob storage), ADR-0008 (async processing)
- Related requirements: FR-003, FR-004, NFR-002
