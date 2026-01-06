// ========================================
// ODOOMASTER SERVICE WORKER - DISABLED
// This service worker is intentionally disabled
// to prevent caching issues during development
// ========================================

// Immediately uninstall this service worker
self.addEventListener('install', event => {
    console.log('🗑️ Service Worker: Uninstalling...');
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    console.log('🧹 Service Worker: Cleaning up caches...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    console.log('🗑️ Deleting cache:', cache);
                    return caches.delete(cache);
                })
            );
        }).then(() => {
            console.log('✅ All caches cleared');
            // Unregister self
            return self.registration.unregister();
        }).then(() => {
            console.log('✅ Service Worker unregistered');
        })
    );
});

// Pass through all fetch requests (no caching)
self.addEventListener('fetch', event => {
    event.respondWith(fetch(event.request));
});
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(name => name !== STATIC_CACHE && 
                                       name !== DYNAMIC_CACHE)
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
            const cache = await caches.open(DYNAMIC_CACHE);
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
    // For page requests, try to serve the cached index
    if (request.mode === 'navigate') {
        const cachedIndex = await caches.match('/index.html');
        if (cachedIndex) {
            return cachedIndex;
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
