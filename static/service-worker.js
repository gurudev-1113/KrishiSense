/**
 * KrishiSense Service Worker
 * Enables offline support, caching, and multi-user concurrent access
 */

const CACHE_NAME = 'krishisense-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/styles.css',
  '/static/js/main.js',
  '/manifest.json',
  '/offline.html'
];

// Install event - cache essential assets
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.log('[Service Worker] Some assets failed to cache', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first, fall back to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Skip non-GET requests (POST, PUT, DELETE, etc.)
  if (request.method !== 'GET') {
    return;
  }

  // Skip WebSocket and chrome-extension requests
  if (request.url.startsWith('ws:') || request.url.startsWith('wss:') || request.url.startsWith('chrome-extension:')) {
    return;
  }

  // For API calls, use network-first strategy with cache fallback
  if (request.url.includes('/api/') || request.url.includes('/predict') || request.url.includes('/dashboard')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Only cache successful responses
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return caches.match(request).then((cached) => {
            return cached || new Response('Offline - Data not available', { status: 503 });
          });
        })
    );
  } else {
    // For static assets, use cache-first strategy
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        }).catch(() => {
          return new Response('Offline - Resource not available', { status: 503 });
        });
      })
    );
  }
});

// Handle messages from clients (for multi-user sync)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    console.log('[Service Worker] Clearing cache per user request');
    caches.delete(CACHE_NAME);
  }

  if (event.data && event.data.type === 'SYNC_USER_DATA') {
    console.log('[Service Worker] Syncing user data across sessions');
    // Broadcast to all clients for real-time sync
    self.clients.matchAll().then((clients) => {
      clients.forEach((client) => {
        client.postMessage({
          type: 'USER_DATA_SYNCED',
          data: event.data.payload
        });
      });
    });
  }
});

console.log('[Service Worker] Script loaded and ready');
