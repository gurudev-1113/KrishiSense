const CACHE_NAME = 'krishisense-pwa-v3';
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/static/css/voice-assistant.css',
  '/static/css/style.css',
  '/static/css/disease.css',
  '/static/js/voice-assistant.js',
  '/static/js/lang-toggle.js',
  '/static/js/pwa-install.js',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/img/apple-touch-icon.png',
  '/static/img/krishi-bot-transparent.png',
  '/static/img/logo.png',
  '/static/img/default-avatar.png',
  '/static/favicon.ico',
  '/manifest.json'
];

// Install Event - Pre-cache critical core assets
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[SW] Cache prefetch notice:', err);
      });
    })
  );
});

// Activate Event - Clean up old/stale caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event - Fast, resilient caching
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Skip non-GET requests
  if (req.method !== 'GET') {
    return;
  }

  // 1. CRITICAL: Never intercept video streaming or Range requests (let browser stream natively)
  if (
    url.pathname.endsWith('.mp4') ||
    url.pathname.endsWith('.webm') ||
    url.pathname.includes('/videos/') ||
    req.headers.get('range')
  ) {
    return;
  }

  // 2. Static Assets (CSS, JS, PNG, ICO, WebP, SVG, Fonts) - Cache-first with robust fallback
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req, { ignoreSearch: true }).then((cached) => {
        if (cached) return cached;
        return fetch(req)
          .then((res) => {
            if (res && res.status === 200) {
              const clone = res.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(req, clone)).catch(() => {});
            }
            return res;
          })
          .catch(() => {
            // If network request fails, try matching path without query string or return fallback
            return caches.match(url.pathname, { ignoreSearch: true }).then((fallback) => {
              if (fallback) return fallback;
              return new Response('', { status: 204, statusText: 'No Content' });
            });
          });
      }).catch(() => {
        return fetch(req).catch(() => new Response('', { status: 204, statusText: 'No Content' }));
      })
    );
    return;
  }

  // 3. HTML Pages & Dynamic Navigation - Network First, fallback to cached offline shell
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200 && req.mode === 'navigate') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone)).catch(() => {});
        }
        return res;
      })
      .catch(() => {
        return caches.match(req, { ignoreSearch: true }).then((cached) => {
          return cached || caches.match('/');
        });
      })
      .catch(() => new Response('Offline', { status: 503, statusText: 'Service Unavailable' }))
  );
});
