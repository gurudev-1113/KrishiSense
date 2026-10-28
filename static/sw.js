const CACHE_NAME = 'krishisense-pwa-v2';
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
  '/static/favicon.ico',
  '/manifest.json'
];

// Install Event
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

// Activate Event - clean up stale caches
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

// Fetch Event - Fast, responsive caching
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Skip POST/PUT/DELETE requests
  if (req.method !== 'GET') {
    return;
  }

  // 1. CRITICAL: NEVER intercept video files (let browser stream natively via HTTP 206)
  if (url.pathname.endsWith('.mp4') || url.pathname.endsWith('.webm') || url.pathname.includes('/videos/')) {
    return;
  }

  // 2. Static Assets (CSS, JS, PNG, ICO, Fonts) - Cache First for instant speed
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return res;
        });
      })
    );
    return;
  }

  // 3. HTML Pages & Dynamic Navigation - Network First, fallback to cached offline shell
  event.respondWith(
    fetch(req).catch(() => {
      return caches.match(req).then((cached) => {
        return cached || caches.match('/');
      });
    })
  );
});
