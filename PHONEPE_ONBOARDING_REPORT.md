# PhonePe Payment Gateway — Onboarding Report

**Project:** ZipStore (Express + MongoDB backend, static frontend)
**Date:** 08 August 2026 (data verified against the live codebase)
**Status:** UAT (sandbox) integration complete; production onboarding pending

---

## 1. Summary

The ZipStore checkout flow is fully wired to the **PhonePe PG API** (UPI transactions). The integration is code-complete and verified in UAT mode. This report documents what PhonePe requires to go live, what the app already provides, and the exact steps and credentials still needed from the merchant.

## 2. Integration Architecture

```
Static frontend (GitHub Pages)
        │  place-order → /api/orders  (creates order, clientOrderId dedupe)
        │  payment → /api/payments/phonepe-initiate
        ▼
Express API (zipstore-backend, Render)
        │  builds payload + X-VERIFY (SHA256 base64, salt index)
        ▼
PhonePe PG API
        │  payment page → user pays via UPI app
        │  callback → /api/payments/phonepe-callback  (X-VERIFY verified)
        │  status check → /api/payments/phonepe-status  (reconciliation)
        ▼
Express API updates PaymentTransaction + Order (paymentStatus / orderStatus)
```

### Endpoints implemented (Express backend — verified from `routes/payments.js`, `server.js`)

| Method | Path | Purpose | Access |
|---|---|---|---|
| POST | `/api/payments/phonepe-initiate` | Create PhonePe transaction, return `redirectUrl` | logged-in or guest |
| POST | `/api/payments/phonepe-retry` | Retry a pending transaction | logged-in or guest |
| POST | `/api/payments/phonepe-callback` | Receive PhonePe webhook/callback, verify signature, sync order | webhook (PhonePe → server) |
| GET | `/api/payments/phonepe-status/:transactionId` | Poll/verify transaction status (path param) | auth required |
| GET | `/api/payments/transaction/:transactionId` | Transaction lookup | auth required |
| POST | `/api/admin/payments/refund/:transactionId` | Initiate refund | admin only |
| GET | `/api/payments/config` | Client-facing config (`phonepeConfigured`, `phonepeEnv`, `upiId`) | public |
| POST | `/api/payments/upi-initiate` | Manual UPI link fallback (UPI deep link) | logged-in or guest |

> Status, transaction lookup and refund endpoints use **path** parameters (not query strings), and require a bearer token (admin for refunds).

### Key source files

- `zipstore-backend/services/phonepe.js` — checksum, initiate, status, webhook processing, retry, refund, env guard
- `zipstore-backend/controllers/paymentController.js` — all payment endpoints
- `zipstore-backend/routes/payments.js` — routing + rate limiting + validation
- `zipstore-backend/models/PaymentTransaction.js` — transaction ledger
- `zipstore-backend/server.js` — mounts payment routes, config endpoint, error handlers

## 3. Current Configuration (UAT / Sandbox)

| Setting | Value |
|---|---|
| Environment | `test` (UAT) |
| Merchant ID | `MERCHANTUAT` |
| Salt Key | `96434309-7796-489d-8924-ab56988a6076` |
| Salt Index | `1` |
| UAT API base | `https://api-preprod.phonepe.com/apis/hermes` |
| Redirect URL (frontend) | `https://vishalkharat951.github.io/zipstore/my-orders.html` |
| Callback URL (backend) | `https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback` |
| Backend host | `https://zip-backend-myp0.onrender.com` |

> **Security guard:** `services/phonepe.js` refuses to run the **UAT salt key in a non-test environment** (`getConfig` validation). The app will not initiate live transactions until production credentials are supplied.

### Signature scheme (X-VERIFY)

```
X-VERIFY = SHA256(<base64-payload> + <endpoint> + <salt_key>) + "###" + <salt_index>
```

- Initiate: computed over `base64(payload)` + `/pg/v1/pay` + salt key; sent in the `X-VERIFY` header.
- Status: computed over `/pg/v1/status/{merchantId}/{merchantTransactionId}`; the request also sends `X-MERCHANT-ID`.
- Callback: recomputed from the raw base64 `response` string + status endpoint + salt key and compared with the incoming `X-VERIFY` header using a timing-safe compare (forged callbacks rejected).

## 4. PhonePe Onboarding Checklist

PhonePe requires the merchant to complete the following before live keys are issued:

- [x] Merchant application submitted (account/entity in place)
- [ ] **KYC documents** — PAN, GST certificate, bank account (settlement), address proof
- [ ] **Business details** — website URL, business category, settlement bank details
- [ ] **Webhook/callback URL** approved and registered — `https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback`
- [ ] **Redirect URL** approved — `https://vishalkharat951.github.io/zipstore/my-orders.html`
- [ ] **UAT testing sign-off** — at least one successful UAT transaction verified via the dashboard
- [ ] **Production credentials issued** — production Merchant ID, Salt Key, Salt Index
- [ ] HTTPS enabled on callback + redirect URLs (already the case — both are HTTPS)
- [ ] Merchant display name finalised (appears on the payment page / bank statement)

## 5. Credentials Still Required from Merchant (production)

Set these in the deployment environment (Render env vars or OCI config). **Never commit them to git.**

| Variable | Description | Example |
|---|---|---|
| `PHONEPE_MERCHANT_ID` | Production merchant ID | `ZIPSTOREMERCHANT` |
| `PHONEPE_SALT_KEY` | Production salt key (32-char) | `...` (issued by PhonePe) |
| `PHONEPE_SALT_INDEX` | Salt key index (usually `1`) | `1` |
| `PHONEPE_ENV` | `test` or `production` | `production` |
| `PHONEPE_CALLBACK_URL` | Webhook URL (must be HTTPS) | `https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback` |
| `PHONEPE_REDIRECT_URL` | Post-payment redirect | `https://vishalkharat951.github.io/zipstore/my-orders.html` |
| `PHONEPE_WEBHOOK_SECRET` | Optional extra webhook signature check | any long random string |

## 6. Verification Status

| Test | Result |
|---|---|
| Backend boots with payment routes mounted | ✅ |
| `/api/payments/config` returns `phonepeConfigured: true` in UAT | ✅ |
| X-VERIFY checksum generation/verification logic | ✅ (unit-verified in `services/phonepe.js`) |
| Callback signature verification (rejects forged callbacks) | ✅ |
| Order sync on `PAYMENT_SUCCESS` (paymentStatus → `paid`, orderStatus → `confirmed`) | ✅ |
| Duplicate-order prevention (`clientOrderId` → 409) | ✅ |
| Security headers + CSP on API responses | ✅ |
| Auth endpoint rate limiting (429 after threshold) | ✅ |
| CORS allowlist (wildcard `*` supported) | ✅ |

**Not yet verified in UAT:** an end-to-end live UAT transaction (initiate → pay in sandbox → callback received → order marked paid). This requires the PhonePe UAT dashboard and the callback URL reachable from PhonePe.

## 7. Risks / Notes

1. **UAT credentials in `.env`** — `zipstore-backend/.env` currently holds only dev values (`MONGODB_URI`, dev `JWT_SECRET`, `ALLOWED_ORIGINS=*`). The UAT PhonePe credentials referenced in this report should live in the hosting platform's env vars, not in the repo.
2. **`ALLOWED_ORIGINS=*`** — permissive. Replace with the explicit allowlist in production:
   `ALLOWED_ORIGINS=https://vishalkharat951.github.io`
3. **Callback reachability** — the PhonePe UAT callback uses the Render URL. Confirm Render free-tier sleeping doesn't miss callbacks (consider a paid/persistent plan or the OCI deployment).
4. **Private keys tracked in git** (`ca.key`, `key.pem`, `cert.pem`, `ca.crt`) — remove from tracking before going live (see Phase 12 readiness report).
5. **Production amount checks** — amount is derived server-side from the order; do not trust client-sent amounts (already enforced: server re-reads order `totalAmount`).
