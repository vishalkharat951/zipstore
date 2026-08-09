const crypto = require('crypto');

const buckets = new Map();
const MAX_BUCKETS = 10000;

function evictExpired() {
  if (buckets.size < MAX_BUCKETS) return;
  const now = Date.now();
  for (const [key, bucket] of buckets) {
    if (now - bucket.startedAt > bucket.windowMs) buckets.delete(key);
  }
}

function createRateLimiter({ windowMs = 60 * 1000, max = 60, message = 'Too many requests. Please try again later.' } = {}) {
  return function rateLimit(req, res, next) {
    const ip =
      (req.headers['x-forwarded-for'] || '').split(',')[0].trim() ||
      req.socket.remoteAddress ||
      'unknown';
    const key = ip + ':' + req.path;
    const now = Date.now();

    evictExpired();

    let bucket = buckets.get(key);
    if (!bucket || now - bucket.startedAt > bucket.windowMs) {
      bucket = { startedAt: now, count: 0, windowMs };
      buckets.set(key, bucket);
    }

    bucket.count += 1;

    res.setHeader('X-RateLimit-Limit', String(max));
    res.setHeader('X-RateLimit-Remaining', String(Math.max(0, max - bucket.count)));

    if (bucket.count > max) {
      return res.status(429).json({ error: message });
    }

    next();
  };
}

function applySecurityHeaders(req, res, next) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  res.setHeader('X-Permitted-Cross-Domain-Policies', 'none');
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  res.setHeader('Cross-Origin-Resource-Policy', 'same-site');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Pragma', 'no-cache');

  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data: https:",
    "connect-src 'self' https:",
    "frame-src https:",
    "media-src 'self' https: blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self' https:",
    "frame-ancestors 'none'",
  ];

  res.setHeader('Content-Security-Policy', csp.join('; '));
  next();
}

function sanitizeString(value, maxLength = 500) {
  return String(value || '')
    .replace(/[\u0000-\u001F\u007F]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLength);
}

function sanitizeObject(obj, schema) {
  const out = {};
  for (const [key, rules] of Object.entries(schema || {})) {
    if (obj[key] === undefined || obj[key] === null) {
      if (rules.required) return { error: `${key} is required` };
      if (rules.default !== undefined) out[key] = rules.default;
      continue;
    }
    const value = obj[key];
    switch (rules.type) {
      case 'string': {
        const s = sanitizeString(value, rules.max || 500);
        if (rules.min && s.length < rules.min) return { error: `${key} must be at least ${rules.min} characters` };
        if (rules.regex && !rules.regex.test(s)) return { error: `${key} is invalid` };
        out[key] = s;
        break;
      }
      case 'number': {
        const n = Number(value);
        if (Number.isNaN(n)) return { error: `${key} must be a number` };
        if (rules.min !== undefined && n < rules.min) return { error: `${key} must be at least ${rules.min}` };
        if (rules.max !== undefined && n > rules.max) return { error: `${key} must be at most ${rules.max}` };
        out[key] = n;
        break;
      }
      case 'boolean':
        out[key] = value === true || value === 'true' || value === 1;
        break;
      case 'array': {
        if (!Array.isArray(value)) return { error: `${key} must be an array` };
        out[key] = value;
        break;
      }
      case 'object':
        out[key] = (value && typeof value === 'object' && !Array.isArray(value)) ? value : null;
        break;
      default:
        out[key] = value;
    }
  }
  return out;
}

function validateBody(schema) {
  return function validate(req, res, next) {
    const result = sanitizeObject(req.body || {}, schema);
    if (result && result.error) {
      return res.status(400).json({ error: result.error });
    }
    req.body = result;
    next();
  };
}

module.exports = {
  createRateLimiter,
  applySecurityHeaders,
  validateBody,
  sanitizeObject,
  sanitizeString,
};
