// Service Worker for Moji Assistant PWA
const APP_VERSION = '1.0.0'; // Must match the version in version-manager.js
const CACHE_NAME = `moji-cache-v${APP_VERSION}`;

// Assets to cache
const STATIC_ASSETS = [
  '/',
  '/assets/app.css',
  '/assets/glassy-theme.css',
  '/assets/_variables.css',
  '/assets/_base.css',
  '/assets/_login.css',
  '/assets/_chat.css',
  '/assets/_header.css',
  '/assets/_messages.css',
  '/assets/_input.css',
  '/assets/_tools.css',
  '/assets/_modal.css',
  '/assets/_json_view.css',
  '/assets/_media_queries.css',
  '/assets/_animations.css',
  '/assets/app.js',
  '/assets/pwa-install.js',
  '/assets/version-manager.js',
  '/assets/offline.html',
  '/assets/manifest.json',
  '/assets/icons/favicon-16x16.png',
  '/assets/icons/favicon-32x32.png',
  '/assets/icons/icon-72x72.png',
  '/assets/icons/icon-96x96.png',
  '/assets/icons/icon-128x128.png',
  '/assets/icons/icon-144x144.png',
  '/assets/icons/icon-152x152.png',
  '/assets/icons/icon-192x192.png',
  '/assets/icons/icon-384x384.png',
  '/assets/icons/icon-512x512.png',
  '/assets/icons/maskable-icon-512x512.png',
  '/assets/icons/apple-touch-icon-iphone-60x60.png',
  '/assets/icons/apple-touch-icon-ipad-76x76.png',
  '/assets/icons/apple-touch-icon-iphone-retina-120x120.png',
  '/assets/icons/apple-touch-icon-ipad-retina-152x152.png',
  '/assets/icons/apple-touch-icon-180x180.png',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css',
  'https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js',
  'https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[Service Worker] Successfully installed');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('[Service Worker] Install error:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Removing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[Service Worker] Activated and ready to handle fetches');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  // Skip cross-origin requests like API calls
  if (!event.request.url.startsWith(self.location.origin) && 
      !event.request.url.includes('fonts.googleapis.com') && 
      !event.request.url.includes('cdnjs.cloudflare.com') &&
      !event.request.url.includes('unpkg.com')) {
    return;
  }
  
  // Handle API requests specially - but with special handling for version endpoint
  if (event.request.url.includes('/api/')) {
    // Special handling for version endpoint - never cache
    if (event.request.url.includes('/api/version')) {
      // Always use network for version checks - crucial for update mechanism
      event.respondWith(
        fetch(event.request).catch(() => {
          // If network fails, return a default version response
          return new Response(JSON.stringify({
            version: APP_VERSION,
            build_date: 'unknown',
            release_notes: 'Using cached version information'
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        })
      );
      return;
    }
    
    // For other API requests, try the network and if that fails, show offline content
    event.respondWith(
      fetch(event.request).catch(() => {
        // If API fails and it's a GET request, return a custom offline response
        if (event.request.method === 'GET') {
          return new Response(JSON.stringify({
            success: false,
            error: 'You are offline. Please check your connection.'
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        // For non-GET requests that fail, return a basic error
        return new Response('Network request failed. You are offline.', {
          status: 503,
          statusText: 'Service Unavailable'
        });
      })
    );
    
    return;
  }
  
  // For regular assets, use cache-first strategy
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // Return from cache if found
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Otherwise try to fetch from network
        return fetch(event.request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response as it can only be consumed once
            const responseToCache = response.clone();
            
            // Cache the new resource
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            
            return response;
          })
          .catch(error => {
            console.error('[Service Worker] Fetch error:', error);
            
            // If HTML is requested, return our offline page
            if (event.request.headers.get('accept').includes('text/html')) {
              return caches.match('/assets/offline.html');
            }
            
            // For other files that weren't cached, return an error
            return new Response('You are offline and this resource is not available.', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
      })
  );
});

// Handle push notifications
self.addEventListener('push', event => {
  const data = event.data.json();
  
  self.registration.showNotification('Moji Assistant', {
    body: data.message || 'New update from Moji!',
    icon: '/assets/icons/icon-192x192.png',
    badge: '/assets/icons/notification-badge-96x96.png',
    data: {
      url: data.url || '/'
    }
  });
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  event.waitUntil(
    clients.matchAll({type: 'window'})
      .then(windowClients => {
        // Check if there's already a window open
        for (const client of windowClients) {
          if (client.url === event.notification.data.url && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Otherwise open a new window
        if (clients.openWindow) {
          return clients.openWindow(event.notification.data.url);
        }
      })
  );
});