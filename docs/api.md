# PayNexus REST API Specification

All endpoints are versioned under `/api/v1` and generate interactive OpenAPI specifications at `/docs` and `/redoc`.

## 1. Authentication
PayNexus implements JWT Bearer authentication and machine API-Key authentication.

### Obtaining a JWT Token
`POST /api/v1/auth/token` (OAuth2 Password flow)
- Request: `username=admin@paynexus.io&password=Demo@PayNexus2026!`
- Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Machine API Key Authentication
Pass header: `X-API-Key: paynexus_live_...`

---

## 2. Payments API

### Create Payment
`POST /api/v1/payments/`
- Header: `Idempotency-Key: <unique-string>`
- Body:
```json
{
  "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "amount_minor": 150000,
  "currency": "INR",
  "urgency": "INSTANT",
  "description": "Invoice payment"
}
```
- Response: `201 Created`

### Idempotency Behavior
1. Sending the same `Idempotency-Key` and identical body returns the original payload with response header: `Idempotent-Replayed: true`.
2. Sending the same key with different body payload returns `422 Conflict`.

---

## 3. Compliance & Sanctions
- `GET /api/v1/compliance/screening-queue`: View flagged payments
- `POST /api/v1/compliance/approvals/{id}`: Four-Eyes maker-checker decision
- `PATCH /api/v1/compliance/fraud-rules/{id}/toggle`: Enable/disable rule at runtime

---

## 4. Message Translation
`POST /api/v1/messages/translate`
- Body:
```json
{
  "format_type": "AUTO",
  "content": "<Document xmlns=...pain.001...>...</Document>"
}
```
- Returns canonical ISO 20022 internal model and schema validation errors.

---

## 5. Audit Chain Verification
- `POST /api/v1/audit/verify`: Recomputes SHA-256 chain from genesis
- `POST /api/v1/audit/tamper-demo`: Deliberately mutates a row in database to demonstrate cryptographic tamper detection.
