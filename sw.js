const CACHE = 'zipstore-v9';
const STATIC = [
  'css/global.css',
  'css/loader.css',
  'css/policies.css',
  'js/admin.js',
  'js/cart.js',
  'js/loader.js',
  'assets/css/preloader.css',
  'assets/js/preloader.js',
  'offline.html'
];
const SHELL = [
  'index.html',
  'shop.html',
  'cart.html',
  'checkout.html',
  'my-orders.html',
  'product.html',
  'login.html',
  'admin.html',
  'privacy-policy.html',
  'terms.html',
  'return-policy.html',
  'refund-policy.html',
  'cancellation-policy.html',
  'shipping-policy.html',
  'contact.html',
  'about.html',
  'faq.html',
  'support.html',
  'track-order.html'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => Promise.all([
      cache.addAll(STATIC),
      cache.addAll(SHELL)
    ]))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const { request } = e;
  const url = new URL(request.url);

  if (url.origin !== location.origin) return;

  if (request.method !== 'GET') return;

  if (request.mode === 'navigate') {
    e.respondWith(networkFirst(request));
    return;
  }

  if (url.pathname.indexOf('/api/') !== -1) {
    e.respondWith(staleWhileRevalidate(request));
    return;
  }

  const ext = url.pathname.split('.').pop();
  if (['css','js','png','svg','jpg','jpeg','webp','woff2','woff'].includes(ext)) {
    e.respondWith(cacheFirst(request));
    return;
  }

  e.respondWith(staleWhileRevalidate(request));
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(request);
    if (res.ok) cache.put(request, res.clone());
    return res;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (request.mode === 'navigate') return caches.match('offline.html');
    return new Response('Offline', { status: 503 });
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const res = await fetch(request);
    if (res.ok) {
      const cache = await caches.open(CACHE);
      cache.put(request, res.clone());
    }
    return res;
  } catch {
    return caches.match(request);
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then(res => {
      if (res.ok) cache.put(request, res.clone());
      return res;
    })
    .catch(() => null);

  if (cached) {
    networkPromise.then(fresh => {
      if (fresh) self.clients.matchAll().then(clients => {
        clients.forEach(client => client.postMessage({ type: 'refresh', url: request.url }));
      });
    });
    return cached;
  }

  return networkPromise.then(fresh => {
    if (fresh) return fresh;
    if (request.mode === 'navigate') return caches.match('offline.html');
    return new Response('Offline', { status: 503 });
  });
}
