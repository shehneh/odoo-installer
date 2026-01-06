// Navigation Loader & Global Auth System
// این فایل رو در همه صفحات include کنید

// =====================================
// Service Worker DISABLED - was causing cache issues
// =====================================
// Unregister any existing service workers to fix caching issues
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function(registrations) {
        for(let registration of registrations) {
            registration.unregister();
            console.log('🗑️ Service Worker unregistered');
        }
    });
}

// =====================================
// Global Auth State (مثل GitHub)
// =====================================
window.AUTH = {
    isLoggedIn: false,
    user: null,
    isLoading: true,
    listeners: [],
    
    // Subscribe to auth changes
    onAuthChange: function(callback) {
        this.listeners.push(callback);
        // Call immediately with current state
        if (!this.isLoading) {
            callback(this.isLoggedIn, this.user);
        }
    },
    
    // Notify all listeners
    notifyListeners: function() {
        this.listeners.forEach(cb => cb(this.isLoggedIn, this.user));
    },
    
    // Check auth status from server
    check: async function() {
        this.isLoading = true;
        try {
            const response = await fetch('/api/user-status', {
                credentials: 'same-origin'
            });
            const result = await response.json();
            
            if (result.success && result.logged_in && result.user) {
                this.isLoggedIn = true;
                this.user = result.user;
            } else {
                this.isLoggedIn = false;
                this.user = null;
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.isLoggedIn = false;
            this.user = null;
        }
        this.isLoading = false;
        this.notifyListeners();
        return this.isLoggedIn;
    },
    
    // Logout
    logout: async function() {
        try {
            await fetch('/api/logout', { 
                method: 'POST',
                credentials: 'same-origin'
            });
        } catch (e) {}
        this.isLoggedIn = false;
        this.user = null;
        this.notifyListeners();
        window.location.href = '/';
    }
};

// Legacy support for old code
window.getAuthToken = function() {
    return window.AUTH.isLoggedIn ? 'session' : null;
};

(function() {
    // Load Navigation Component
    function loadNavigation() {
        // Make sure body exists
        if (!document.body) {
            console.log('⏳ Waiting for body...');
            setTimeout(loadNavigation, 10);
            return;
        }
        
        console.log('🔄 Loading navigation...');
        fetch('/components/nav-header.html', { cache: 'no-store' })
            .then(response => {
                console.log('✅ Navigation HTML fetched');
                return response.text();
            })
            .then(html => {
                // Try both possible container IDs
                let navContainer = document.getElementById('mainNav') || document.getElementById('navHeader') || document.getElementById('nav-container');
                console.log('📍 Nav container:', navContainer);
                if (!navContainer) {
                    navContainer = document.createElement('div');
                    navContainer.id = 'navHeader';
                    document.body.insertBefore(navContainer, document.body.firstChild);
                    console.log('➕ Created new nav container');
                }
                navContainer.innerHTML = html;
                console.log('✅ Navigation loaded successfully');
                
                // Execute scripts in the loaded HTML
                const scripts = navContainer.querySelectorAll('script');
                console.log('📜 Found', scripts.length, 'scripts to execute');
                scripts.forEach(script => {
                    const newScript = document.createElement('script');
                    newScript.textContent = script.textContent;
                    document.body.appendChild(newScript);
                });
                
                // Trigger event for other scripts
                window.dispatchEvent(new Event('navigationLoaded'));
            })
            .catch(error => console.error('❌ Error loading navigation:', error));
    }

    // Check auth on page load
    window.AUTH.check();

    // Auto-load navigation - ensure DOM is ready
    function initNav() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', loadNavigation);
        } else if (document.body) {
            loadNavigation();
        } else {
            // Body not ready yet, wait a bit
            setTimeout(loadNavigation, 10);
        }
    }
    
    initNav();

    // TurboNav disabled - was causing page rendering issues
    // Pages now load normally with full page refresh
    // To re-enable, uncomment below:
    /*
    if (!window.TurboNav) {
        const turboScript = document.createElement('script');
        turboScript.src = '/js/turbo-nav.js';
        turboScript.async = true;
        document.head.appendChild(turboScript);
    }
    */
})();
