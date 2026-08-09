# Site Information — PhonePe Payment Gateway Onboarding Submission

Prepared for submission to PhonePe (merchant onboarding / go-live).
Project: ZipStore
Date: 08 August 2026 (data verified against the live codebase and deployed config)

---

## 1. Merchant / Business Information

| Field | Value |
|---|---|
| Business / Store name | ZipStore |
| Business type | Online e-commerce store (retail) |
| Business category | E-commerce / Online Retail (general merchandise) |
| Registered address | ZipStore, Pune, Maharashtra, India |
| Website | https://vishalkharat951.github.io/zipstore/ |
| Support e-mail | support@zipstore.in |
| Contact phone | +91 86693 03401 |
| Payment model | UPI via PhonePe Payment Gateway (PG API) |
| Currency | INR (₹) |
| Statement / display name (to appear on payment page & bank statement) | ZipStore |

> Business description: "ZipStore is an Indian online store built to make shopping fast, secure, and enjoyable. From discovering products to paying with UPI in seconds. Curated products with transparent pricing, fast free shipping across India, secure PhonePe UPI payments, order tracking, and responsive support." (from about.html)

---

## 2. Website / Storefront

| Field | Value |
|---|---|
| Storefront URL | https://vishalkharat951.github.io/zipstore/ |
| Hosting | GitHub Pages (HTTPS) |
| Shop / catalog page | https://vishalkharat951.github.io/zipstore/shop.html |
| Product page | https://vishalkharat951.github.io/zipstore/product.html?id=<productId> |
| Cart page | https://vishalkharat951.github.io/zipstore/cart.html |
| Checkout page | https://vishalkharat951.github.io/zipstore/checkout.html |
| Order confirmation / redirect page | https://vishalkharat951.github.io/zipstore/my-orders.html |
| Track order | https://vishalkharat951.github.io/zipstore/track-order.html |
| Login | https://vishalkharat951.github.io/zipstore/login.html |
| Admin panel | https://vishalkharat951.github.io/zipstore/admin.html |

Pages with required policies (all HTTPS):
- Privacy Policy — https://vishalkharat951.github.io/zipstore/privacy-policy.html
- Terms & Conditions — https://vishalkharat951.github.io/zipstore/terms.html
- Refund Policy — https://vishalkharat951.github.io/zipstore/refund-policy.html
- Cancellation Policy — https://vishalkharat951.github.io/zipstore/cancellation-policy.html
- Shipping Policy — https://vishalkharat951.github.io/zipstore/shipping-policy.html
- Contact — https://vishalkharat951.github.io/zipstore/contact.html
- About — https://vishalkharat951.github.io/zipstore/about.html
- FAQ — https://vishalkharat951.github.io/zipstore/faq.html
- Support — https://vishalkharat951.github.io/zipstore/support.html

---

## 3. Backend / API Server

| Field | Value |
|---|---|
| Backend API base URL | https://zip-backend-myp0.onrender.com/api |
| API gateway (current default in `js/config.js`) | https://fbecqsp5leqmdfeg23vts53dom.apigateway.ap-mumbai-1.oci.customer-oci.com/api |
| Hosting | Render (Express + Node.js) / OCI API Gateway |
| Health check | GET https://zip-backend-myp0.onrender.com/api/health |
| HTTPS | Yes (both endpoints) |

> NOTE (verified 08 Aug 2026): the deployed storefront is served from GitHub Pages at the `/zipstore/` path (repo `vishalkharat951/zipstore`). `js/config.js` points to the OCI API gateway, which is **live** (health check returns `{"status":"OK"}`). The Render host (`zip-backend-myp0.onrender.com`) returned `503` during verification (sleeping/unreachable). The PhonePe callback URL is registered on the **Render** host — confirm with the PhonePe team which backend URL is the production API, and keep that host awake before go-live.

---

## 4. PhonePe Payment Gateway — Technical Configuration

### Payment endpoints implemented (backend — verified from `routes/payments.js` and `server.js`)

| Method | Path (relative to API base) | Purpose | Access |
|---|---|---|---|
| POST | /api/payments/phonepe-initiate | Create PhonePe transaction, return `redirectUrl` | logged-in or guest |
| POST | /api/payments/phonepe-retry | Retry a pending transaction | logged-in or guest |
| POST | /api/payments/phonepe-callback | Receive PhonePe webhook/callback, verify X-VERIFY, sync order | webhook (PhonePe → server) |
| GET | /api/payments/phonepe-status/:transactionId | Poll / verify transaction status (transactionId is a **path** parameter) | auth required |
| GET | /api/payments/transaction/:transactionId | Transaction lookup | auth required |
| POST | /api/admin/payments/refund/:transactionId | Initiate refund | admin only |
| GET | /api/payments/config | Client-facing config (`phonepeConfigured`, `phonepeEnv`, `upiId`) | public |
| POST | /api/payments/upi-initiate | Manual UPI link fallback (UPI deep link) | logged-in or guest |

### Callback (webhook) URL to register with PhonePe

```
https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback
```

### Redirect (return) URL to register with PhonePe

```
https://vishalkharat951.github.io/zipstore/my-orders.html
```

### PhonePe API base URLs (used by the backend)

| Environment | Base URL |
|---|---|
| test (UAT) | `https://api-preprod.phonepe.com/apis/hermes` |
| production | `https://api.phonepe.com/apis/hermes` |

### Signature / checksum (current PhonePe spec — verified in `services/phonepe.js`)

- Format: `X-VERIFY = SHA256(<base64-payload> + <endpoint> + <salt_key>) + "###" + <salt_index>` (i.e. `<hash>###<saltIndex>`).
- **Initiate** (`/pg/v1/pay`): `SHA256(base64(payload) + "/pg/v1/pay" + saltKey) ### saltIndex` sent in the `X-VERIFY` header.
- **Status** (`/pg/v1/status/{merchantId}/{merchantTransactionId}`): computed over the endpoint string; also sends `X-MERCHANT-ID`.
- **Callback**: the backend recomputes the checksum from the raw base64 `response` string + status endpoint + salt key and compares it with the incoming `X-VERIFY` header using a timing-safe comparison. Forged callbacks are rejected.
- UAT salt key is embedded as a default in code for sandbox only; the app **refuses** to use the UAT key in a production environment (`getConfig` guard).

### Payment flow

1. Customer checks out → frontend calls `/api/payments/phonepe-initiate`.
2. Backend builds the payload (amount taken from the order server-side), computes X-VERIFY, calls PhonePe PG API (`/pg/v1/pay`).
3. PhonePe returns `redirectUrl` → customer is redirected to the PhonePe payment page (UPI).
4. PhonePe calls the callback URL; backend verifies X-VERIFY and marks the order `paid` / `confirmed` on `PAYMENT_SUCCESS`.
5. Frontend can poll `/api/payments/phonepe-status/:transactionId` to reconcile if a callback is missed; `/api/payments/phonepe-retry` re-attempts pending transactions.

### Environment & credentials

| Setting | Current value | For production (to be issued by PhonePe) |
|---|---|---|
| Environment | test (UAT sandbox) | production |
| Merchant ID | MERCHANTUAT | <production merchant ID> |
| Salt Key | (UAT key in code defaults) | <production salt key — 32 chars> |
| Salt Index | 1 | <as provided> |
| UPI ID (manual UPI display) | 8669303401@ybl | <merchant settlement UPI/VPA> |
| Merchant display name | ZipStore | ZipStore |

Production credentials are set as environment variables on the hosting platform (never in git):
`PHONEPE_MERCHANT_ID`, `PHONEPE_SALT_KEY`, `PHONEPE_SALT_INDEX`, `PHONEPE_ENV`, `PHONEPE_CALLBACK_URL`, `PHONEPE_REDIRECT_URL`, `PHONEPE_WEBHOOK_SECRET`, plus `UPI_ID`, `MERCHANT_NAME`, `ALLOWED_ORIGINS`, `API_URL`, `FRONTEND_URL`.

---

## 5. Product Catalog (current data — from `products_export.json`)

| Category | Products (SKU, price / discount, stock) |
|---|---|
| Baby Products | Anti-Snoring Lips Strip (ASLS-001, ₹50 / ₹40, stock 149) |
| | Earpick Flashlight Ear Cleaner (EPEC-001, ₹18 / ₹15, stock 199) |
| | Smile Baby Knee Pad (SBKP-001, ₹25 / ₹23, stock 118) |
| | V-Shape Baby Safety Protection (VBSP-001, ₹12 / ₹10, stock 200) |
| Health & Beauty | (empty — category created, pk 1) |

- Prices in INR. Discounted pricing supported (`price` vs `discount_price`).
- Product data source: `products_export.json` (Django fixture) / MongoDB product collection.

---

## 6. Security

- HTTPS on all storefront, policy, and API URLs.
- X-VERIFY signature verification on all PhonePe callbacks (forged callbacks rejected via timing-safe compare).
- Duplicate-order protection via `clientOrderId` (prevents double charging on retry).
- Amount is always derived server-side from the order — never trusted from the client.
- Status, transaction lookup and refund endpoints require authentication (admin-only for refund); webhook and payment routes are rate-limited.
- Optional extra `PHONEPE_WEBHOOK_SECRET` header check supported.
- CORS allowlist enforced (`https://vishalkharat951.github.io` and localhost dev origins).

---

## 7. Onboarding status (as of this document)

| Item | Status |
|---|---|
| Code integration (initiate / retry / callback / status / refund) | Done (UAT verified) |
| UAT (sandbox) credentials in place | Done |
| End-to-end UAT transaction signed off | Pending (needs PhonePe UAT dashboard) |
| Production credentials issued | Pending — awaiting PhonePe |
| Callback + redirect URL registration | Pending PhonePe approval |
| KYC documents (PAN, GST, bank, address proof) | To be provided by merchant |
| Settlement bank details | To be provided by merchant |

---

## 8. Actions still required from merchant to complete PhonePe onboarding

1. Submit KYC: PAN, GST certificate, settlement bank account details, address proof.
2. Confirm final business display name and business category.
3. Confirm production backend host (Render vs OCI) so the callback URL is final.
4. Register and get approval for:
   - Callback URL: `https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback`
   - Redirect URL: `https://vishalkharat951.github.io/zipstore/my-orders.html`
5. Complete one successful UAT transaction in the PhonePe sandbox dashboard.
6. Receive production Merchant ID + Salt Key and set them as env vars on the hosting platform.
7. Switch `PHONEPE_ENV=production` and run a ₹1 live test.

---

*End of document.*
