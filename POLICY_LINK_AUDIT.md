# Policy & Information Pages — Launch Audit

Audit of every public ZipStore page: internal links, authoritative content, and responsive layout readiness.

- **Audit date:** 09 August 2026
- **Scope:** root-level pages of `ecom/` (deployed at `https://vishalkharat951.github.io/zipstore/`)
- **Result:** 20 pages, 628 internal `.html` links, 0 broken links.

## Link Audit

| PAGE | URL | EXISTS | CONTENT | LINK | MOBILE | DESKTOP | STATUS |
|---|---|---|---|---|---|---|---|
| Home | `index.html` | YES | Products load from API | YES (full nav + footer) | Responsive | Responsive | OK |
| Shop | `shop.html` | YES | All products, filters, search | YES | Responsive | Responsive | OK |
| Product | `product.html` | YES | Loads from `?id=` | YES | Responsive | Responsive | OK |
| Cart | `cart.html` | YES | Cart from localStorage | YES | Responsive | Responsive | OK |
| Checkout | `checkout.html` | YES | UPI + PhonePe only (no mock) | YES | Responsive | Responsive | OK |
| Track Order | `track-order.html` | YES | Order status by order ID | YES | Responsive | Responsive | OK |
| My Orders | `my-orders.html` | YES | Orders by email/login | YES | Responsive | Responsive | OK |
| Login | `login.html` | YES | Special layout, kept intact | YES (`index.html`) | Responsive | Responsive | OK |
| Admin | `admin.html` | YES | Special layout, kept intact | YES (`index.html`) | Responsive | Responsive | OK |
| Offline (PWA) | `offline.html` | YES | Minimal inline-styled fallback | YES (`index.html`) | Responsive | Responsive | OK |
| About Us | `about.html` | YES | Authoritative description only | YES (full nav + footer) | Responsive | Responsive | OK |
| Privacy Policy | `privacy-policy.html` | YES | Existing content, new design | YES | Responsive | Responsive | OK |
| Terms & Conditions | `terms.html` | YES | Existing content, new design | YES | Responsive | Responsive | OK |
| Return Policy | `return-policy.html` | YES | **New page** — 7-day rule | YES | Responsive | Responsive | OK |
| Refund Policy | `refund-policy.html` | YES | 7-day credit rule; invented content removed | YES | Responsive | Responsive | OK |
| Cancellation Policy | `cancellation-policy.html` | YES | Existing content, new design | YES | Responsive | Responsive | OK |
| Shipping Policy | `shipping-policy.html` | YES | Authoritative sections; invented table removed | YES | Responsive | Responsive | OK |
| FAQ | `faq.html` | YES | Accordion; invented delivery/replacement claims removed | YES | Responsive | Responsive | OK |
| Contact Us | `contact.html` | YES | Contact cards + honest mailto form (no fake success) | YES | Responsive | Responsive | OK |
| Support | `support.html` | YES | Email/phone + policy links; no fake live chat | YES | Responsive | Responsive | OK |

## Verification Notes

- All 628 internal `href="*.html"` links across the 20 pages resolve to an existing file (0 broken).
- No root-domain/placeholder URLs (e.g. `./page.html` or `/page.html` that would 404 on GitHub Pages) remain.
- Every public page has the shared navbar (with Policies dropdown) and the extended footer (Shop / Company / Policies / Get in Touch), with correct per-page active states.
- `login.html`, `admin.html`, and `offline.html` intentionally keep special/minimal layouts.

## Content Accuracy Notes

- Business info is limited to owner-supplied data: ZipStore, Pune (Maharashtra, India), `support@zipstore.in`, `+91 86693 03401`, 7-day returns, 7-day refund credit, courier/Speed Post shipping, 7-day delivery subject to courier/post norms.
- Invented claims removed: refund-policy conditions (packaging/defective/replacement labels), shipping delivery-time table + "deliver across India" + "free shipping at present" claims, FAQ metro/other delivery times and replacement/refund guarantee.
- Contact form does not fake a sent message; it opens the visitor's email app with a pre-filled `mailto:` to `support@zipstore.in`.
- FAQ "Shipping" answer and Shipping Policy avoid a hard "free shipping" promise; the FAQ states no shipping charge is added at checkout (consistent with cart/backend behavior).

## Design System

- `css/policies.css` — shared design for all policy/info pages: navbar Policies dropdown, extended footer, page hero, section cards, key-rule, refund timeline, contact cards, link tiles, FAQ accordion, notice cards, focus states.
- Service worker (`sw.js`, cache `zipstore-v8`) now precaches `css/policies.css` and the new `return-policy.html`.
