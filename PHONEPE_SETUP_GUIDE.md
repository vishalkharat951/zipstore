# PhonePe Payment Gateway — Setup Guide

**Project:** ZipStore (Express backend)
**Last updated:** 08 August 2026

This guide covers setting up the PhonePe PG integration end to end: environment variables, running locally in UAT, registering URLs with PhonePe, and going live.

---

## 1. Prerequisites

- Node.js 18+ and npm (backend: `zipstore-backend/`)
- A MongoDB instance (local, Atlas, or the hosted one already configured)
- PhonePe **UAT credentials** (already embedded as defaults in `services/phonepe.js` for testing only)
- PhonePe **production credentials** (issued after onboarding — see `PHONEPE_ONBOARDING_REPORT.md`)

## 2. Environment Variables

Copy the template and fill it in:

```bash
cd zipstore-backend
cp .env.example .env
```

### Backend variables (`zipstore-backend/.env`)

| Variable | Required | Purpose |
|---|---|---|
| `PORT` | yes | API port (default `5000`) |
| `MONGODB_URI` | yes | MongoDB connection string |
| `JWT_SECRET` | yes | Token signing secret (use a long random string) |
| `ALLOWED_ORIGINS` | yes | Comma-separated origins, or `*` for all |
| `PHONEPE_MERCHANT_ID` | live only | Production merchant ID (UAT default is built in) |
| `PHONEPE_SALT_KEY` | live only | Production salt key (UAT default is built in) |
| `PHONEPE_SALT_INDEX` | no | Salt index (default `1`) |
| `PHONEPE_ENV` | no | `test` or `production` (default `test`) |
| `PHONEPE_CALLBACK_URL` | yes | Webhook URL PhonePe will call |
| `PHONEPE_REDIRECT_URL` | yes | Where the user is sent after payment |
| `PHONEPE_WEBHOOK_SECRET` | optional | Extra webhook signature check (recommended) |
| `UPI_ID` | no | Merchant UPI ID shown for manual UPI (`8669303401@ybl` default) |
| `MERCHANT_NAME` | no | Display name (`ZipStore` default) |

> **Important:** The UAT salt key (`96434309-...`) is embedded as a **default only** in `services/phonepe.js` and is used solely when `PHONEPE_ENV` is `test`. The service **refuses** to use it in `production`. Do not put production keys in `.env` in the repo — set them on the hosting platform.

### Frontend (`js/config.js` / `js/cart.js`)

- `js/config.js` — `__API_BASE__` must point to the backend root. Current default: the OCI API gateway (`https://fbecqsp5leqmdfeg23vts53dom.apigateway.ap-mumbai-1.oci.customer-oci.com/api`). `js/cart.js` / `js/admin.js` use `https://zip-backend-myp0.onrender.com/api`. Pick one canonical production API base and keep it consistent.
- No secrets live on the frontend.

## 3. Running Locally (UAT)

```bash
cd zipstore-backend
npm install
npm run dev        # or: node server.js
```

The API starts on `http://localhost:5000`.

Verify:

```bash
curl http://localhost:5000/api/health
# {"status":"OK",...}

curl http://localhost:5000/api/payments/config
# {"phonepeConfigured":true,"phonepeEnv":"test","upiId":"8669303401@ybl"}
```

### UAT test transaction flow

1. Open the storefront (`index.html` or via a local server on the allowed origin).
2. Add a product, go to checkout, choose **PhonePe**, place the order.
3. The app calls `/api/payments/phonepe-initiate` → PhonePe returns a `redirectUrl` → the browser is redirected to PhonePe's **sandbox payment page**.
4. Pay with the sandbox UPI app / test card.
5. PhonePe calls the **callback URL**; the order is marked paid when the callback is verified.

## 4. Callback and Redirect URL Registration

PhonePe must know where to send webhook callbacks and where to redirect users:

- **Callback URL:** `https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback`
- **Redirect URL:** `https://vishalkharat951.github.io/zipstore/my-orders.html`

> The callback is **server-side only** and must be reachable from PhonePe (not behind an IP-restricted firewall). If using Render free tier, note that the app can sleep — use a persistent plan or the OCI deployment for production.

## 5. Signature Verification (X-VERIFY)

Every PhonePe call is signed with the current checksum format (verified in `services/phonepe.js`):

```
X-VERIFY = SHA256(<base64-payload> + <endpoint> + <salt_key>) + "###" + <salt_index>
```

- **Initiate** (`/pg/v1/pay`): `SHA256(base64(payload) + "/pg/v1/pay" + saltKey) ### saltIndex` sent in the `X-VERIFY` header.
- **Status** (`/pg/v1/status/{merchantId}/{merchantTransactionId}`): computed over the endpoint string; the request also sends `X-MERCHANT-ID`.
- **Callback:** the incoming `X-VERIFY` header is recomputed from the raw base64 `response` string + status endpoint + salt key and compared using a timing-safe compare; requests that fail verification are rejected.
- An optional extra `PHONEPE_WEBHOOK_SECRET` header check can be enabled.

Implementation: `zipstore-backend/services/phonepe.js` → `buildXVerify` / `verifyCallbackSignature`.

## 6. Going Live

1. Complete PhonePe onboarding (see `PHONEPE_ONBOARDING_REPORT.md` §4).
2. Set production env vars on Render/OCI:
   - `PHONEPE_MERCHANT_ID`, `PHONEPE_SALT_KEY`, `PHONEPE_SALT_INDEX`
   - `PHONEPE_ENV=production`
   - `PHONEPE_CALLBACK_URL`, `PHONEPE_REDIRECT_URL`
   - `PHONEPE_WEBHOOK_SECRET`
3. Restart the backend and confirm `/api/payments/config` reports `phonepeConfigured: true` and `phonepeEnv: production`.
4. Run a real ₹1 test transaction, verify:
   - Payment page is the production PhonePe page.
   - Callback received → `PaymentTransaction` state `SUCCESS`, order `paymentStatus: paid`.
   - Order status flow: `pending → confirmed` on payment success; `failed` on payment error.
5. Monitor `PaymentTransaction` records and webhook logs.

## 7. Status Reconciliation

If a callback is missed, orders stay `pending`. The `/api/payments/phonepe-status/:transactionId` endpoint (path parameter, requires a bearer token) lets the frontend poll the real status; `services/phonepe.js` reconciles the order when the fetched state is `COMPLETED` (`PAYMENT_SUCCESS`). A retry endpoint (`/api/payments/phonepe-retry`) re-attempts pending transactions. Transaction lookup is available at `/api/payments/transaction/:transactionId`.

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `phonepeConfigured: false` | Missing merchant ID / salt key in env | Set `PHONEPE_MERCHANT_ID` + `PHONEPE_SALT_KEY` |
| Initiate returns UAT error | Salt key used with `PHONEPE_ENV=production` | Set `PHONEPE_ENV=test` during UAT |
| Callback rejected | Signature mismatch | Confirm exact raw body, salt key, salt index |
| CORS 403 from browser | Origin not in `ALLOWED_ORIGINS` | Add the frontend origin or use `*` |
| Order stuck `pending` | Callback missed | Poll `/api/payments/phonepe-status` or use retry |

## 9. Reference

- Payment flow files: `services/phonepe.js`, `controllers/paymentController.js`, `routes/payments.js`, `models/PaymentTransaction.js`
- Order dedupe: `clientOrderId` on `models/Order.js`
- Checkout UI: `checkout.html` (payment method "PhonePe"), `my-orders.html` (status display)
- Live readiness: `PROJECT_READINESS_REPORT.md`
