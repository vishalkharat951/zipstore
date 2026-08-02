const API_BASE_URL = 'https://zip-backend-myp0.onrender.com/api';

const _inflight = new Map();
const _dataCache = new Map();
const CACHE_TTL = 30000;
const PERSIST_TTL = 5 * 60 * 1000;
const PERSIST_MAX = 100 * 1024;

function persistKey(url) {
  return 'zipstore_cache_' + url;
}

function persistRead(url) {
  try {
    const raw = localStorage.getItem(persistKey(url));
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function isDataUri(v) {
  return typeof v === 'string' && v.indexOf('data:') === 0;
}

function persistWrite(url, data) {
  try {
    const json = JSON.stringify({ data, ts: Date.now() });
    if (json.length > PERSIST_MAX) return;
    localStorage.setItem(persistKey(url), json);
  } catch {}
}

function evictCacheEntries() {
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.indexOf('zipstore_cache_') === 0) {
        localStorage.removeItem(k);
      }
    }
  } catch {}
}

function cleanupOversizedCache() {
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.indexOf('zipstore_cache_') === 0) {
        const raw = localStorage.getItem(k);
        if (raw && raw.length > PERSIST_MAX) localStorage.removeItem(k);
      }
    }
  } catch {}
}

function fetchFresh(key, url, opts) {
  if (_inflight.has(key)) return _inflight.get(key);
  const p = fetch(url, opts)
    .then(r => { _inflight.delete(key); if (!r.ok) throw new Error('API error'); return r.json(); })
    .then(data => {
      _dataCache.set(key, { data, ts: Date.now() });
      persistWrite(url, data);
      return data;
    })
    .catch(e => { _inflight.delete(key); throw e; });
  _inflight.set(key, p);
  return p;
}

async function apiGet(url, opts) {
  const key = url + (opts ? JSON.stringify(opts) : '');

  if (_inflight.has(key)) {
    try { await _inflight.get(key); } catch {}
  }

  if (_dataCache.has(key)) {
    const entry = _dataCache.get(key);
    if (Date.now() - entry.ts < CACHE_TTL) return entry.data;
    _dataCache.delete(key);
  }

  const persisted = persistRead(url);
  if (persisted && persisted.data) {
    _dataCache.set(key, { data: persisted.data, ts: Date.now() });
    if (Date.now() - persisted.ts < PERSIST_TTL) return persisted.data;
    fetchFresh(key, url, opts).catch(() => {});
    return persisted.data;
  }

  return fetchFresh(key, url, opts);
}

document.addEventListener('click', e => {
  const t = e.target.closest('#navToggle');
  if (t) document.getElementById('navLinks')?.classList.toggle('open');
});

const Cart = {
  _key: 'zipstore_cart',

  get() {
    try {
      return JSON.parse(localStorage.getItem(this._key)) || [];
    } catch {
      return [];
    }
  },

  save(items) {
    try {
      localStorage.setItem(this._key, JSON.stringify(items));
    } catch (e) {
      evictCacheEntries();
      try {
        localStorage.setItem(this._key, JSON.stringify(items));
      } catch {}
    }
    this._updateBadge();
    window.dispatchEvent(new CustomEvent('cart-updated', { detail: items }));
  },

  add(product, quantity = 1) {
    const items = this.get();
    const existing = items.find(i => i.productId === product._id || i.productId === product.id);

    if (existing) {
      existing.quantity += quantity;
    } else {
      const rawImg = product.imageUrl || (product.images && product.images[0]) || '';
      items.push({
        productId: product._id || product.id,
        title: product.title,
        price: product.price,
        imageUrl: isDataUri(rawImg) ? '' : rawImg,
        quantity,
      });
    }

    this.save(items);
    return items;
  },

  remove(productId) {
    const items = this.get().filter(i => (i.productId !== productId));
    this.save(items);
    return items;
  },

  updateQuantity(productId, delta) {
    const items = this.get();
    const item = items.find(i => i.productId === productId);
    if (!item) return items;

    item.quantity += delta;
    if (item.quantity <= 0) {
      return this.remove(productId);
    }

    this.save(items);
    return items;
  },

  setQuantity(productId, qty) {
    const items = this.get();
    const item = items.find(i => i.productId === productId);
    if (!item) return items;

    item.quantity = Math.max(1, qty);
    this.save(items);
    return items;
  },

  clear() {
    this.save([]);
  },

  getTotal() {
    return this.get().reduce((sum, i) => sum + i.price * i.quantity, 0);
  },

  getCount() {
    return this.get().reduce((sum, i) => sum + i.quantity, 0);
  },

  _updateBadge() {
    const count = this.getCount();
    document.querySelectorAll('.cart-count').forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? 'flex' : 'none';
    });
    document.querySelectorAll('.cart-icon').forEach(el => {
      el.classList.toggle('has-items', count > 0);
    });
  },

  init() {
    cleanupOversizedCache();
    this._updateBadge();
  },
};

document.addEventListener('DOMContentLoaded', () => Cart.init());