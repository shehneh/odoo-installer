// ========================================
// ODOOMASTER SERVICE WORKER
// Progressive Web App - Offline Support
// ========================================

const CACHE_NAME = 'odoomaster-v1';
const STATIC_CACHE = 'odoomaster-static-v1';
const DYNAMIC_CACHE = 'odoomaster-dynamic-v1';
const API_CACHE = 'odoomaster-api-v1';

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/app.html',
    '/manifest.json',
    '/css/unified-nav.css',
    '/js/tickets.js',
    '/pages/home.html',
    '/pages/features.html',
    '/pages/downloads.html',
    '/pages/support.html',
    '/pages/dashboard.html',
    '/pages/login.html',
    '/pages/404.html'
];

// API routes to cache with network-first strategy
const API_ROUTES = [
    '/api/user-status',
    '/api/tickets',
    '/api/plans'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('🔧 Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('📦 Caching static assets...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('✅ Static assets cached');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('❌ Cache error:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(name => name !== STATIC_CACHE && 
                                       name !== DYNAMIC_CACHE && 
                                       name !== API_CACHE)
                        .map(name => {
                            console.log('🗑️ Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('✅ Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip external requests
    if (url.origin !== location.origin) {
        return;
    }
    
    // API requests - Network first, then cache
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }
    
    // Static assets - Cache first, then network
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }
    
    // Page requests - Stale while revalidate
    event.respondWith(staleWhileRevalidate(request));
});

// Cache First Strategy
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Network error:', error);
        return getOfflineFallback(request);
    }
}

// Network First Strategy
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('📴 Network failed, trying cache...');
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline JSON response for API
        return new Response(
            JSON.stringify({ 
                success: false, 
                error: 'آفلاین هستید',
                offline: true 
            }),
            { 
                headers: { 'Content-Type': 'application/json' } 
            }
        );
    }
}

// Stale While Revalidate Strategy
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    const networkPromise = fetch(request)
        .then(response => {
            if (response.ok) {
                cache.put(request, response.clone());
            }
            return response;
        })
        .catch(() => null);
    
    return cachedResponse || networkPromise || getOfflineFallback(request);
}

// Check if URL is a static asset
function isStaticAsset(pathname) {
    const staticExtensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf'];
    return staticExtensions.some(ext => pathname.endsWith(ext));
}

// Get offline fallback page
async function getOfflineFallback(request) {
    // For page requests, try to serve the app shell
    if (request.mode === 'navigate') {
        const cachedApp = await caches.match('/app.html');
        if (cachedApp) {
            return cachedApp;
        }
    }
    
    // Return a basic offline response
    return new Response(
        `<!DOCTYPE html>
        <html lang="fa" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>آفلاین - OdooMaster</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: system-ui, -apple-system, sans-serif;
                    background: #1a1a2e;
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: 20px;
                }
                .container {
                    max-width: 400px;
                }
                .icon {
                    font-size: 80px;
                    margin-bottom: 24px;
                }
                h1 {
                    font-size: 24px;
                    margin-bottom: 16px;
                }
                p {
                    color: #64748b;
                    margin-bottom: 32px;
                }
                button {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 14px 32px;
                    border-radius: 12px;
                    font-size: 16px;
                    cursor: pointer;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📶</div>
                <h1>اتصال اینترنت قطع است</h1>
                <p>لطفاً اتصال اینترنت خود را بررسی کنید و دوباره تلاش کنید</p>
                <button onclick="location.reload()">تلاش مجدد</button>
            </div>
        </body>
        </html>`,
        { 
            headers: { 'Content-Type': 'text/html' },
            status: 503
        }
    );
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('🔄 Background sync:', event.tag);
    
    if (event.tag === 'sync-tickets') {
        event.waitUntil(syncPendingTickets());
    }
});

// Sync pending tickets when back online
async function syncPendingTickets() {
    // Get pending tickets from IndexedDB
    // Send them to server
    console.log('📤 Syncing pending tickets...');
}

// Push notifications
self.addEventListener('push', event => {
    console.log('📬 Push notification received');
    
    const data = event.data?.json() || {};
    
    const options = {
        body: data.body || 'پیام جدید دارید',
        icon: '/images/icon-192.png',
        badge: '/images/badge-72.png',
        vibrate: [100, 50, 100],
        data: data,
        dir: 'rtl',
        lang: 'fa',
        actions: [
            { action: 'open', title: 'مشاهده' },
            { action: 'close', title: 'بستن' }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'OdooMaster', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    const data = event.notification.data;
    let url = '/';
    
    if (data?.url) {
        url = data.url;
    } else if (event.action === 'open') {
        url = '/dashboard';
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window' })
            .then(clientList => {
                // Focus existing window if open
                for (const client of clientList) {
                    if (client.url === url && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Otherwise open new window
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

console.log('🚀 OdooMaster Service Worker loaded');
