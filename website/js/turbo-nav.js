/**
 * OdooMaster Turbo Navigation
 * ناوبری سریع بدون reload کامل صفحه
 * 
 * Features:
 * - AJAX page loading (no full reload)
 * - Page preloading on hover
 * - Smooth page transitions
 * - Browser history support
 * - Cache for faster navigation
 */

(function() {
    'use strict';

    const TurboNav = {
        cache: new Map(),
        currentUrl: location.href,
        isNavigating: false,
        preloadQueue: new Set(),

        init() {
            // Create transition overlay
            this.createOverlay();
            
            // Intercept all internal links
            document.addEventListener('click', (e) => this.handleClick(e));
            
            // Handle browser back/forward
            window.addEventListener('popstate', (e) => this.handlePopState(e));
            
            // Preload links on hover
            document.addEventListener('mouseover', (e) => this.handleHover(e));
            
            // Touch devices - preload on touchstart
            document.addEventListener('touchstart', (e) => this.handleHover(e), { passive: true });

            console.log('⚡ TurboNav initialized');
        },

        createOverlay() {
            const overlay = document.createElement('div');
            overlay.id = 'turbo-overlay';
            overlay.innerHTML = `
                <div class="turbo-spinner"></div>
            `;
            document.body.appendChild(overlay);

            // Add styles
            const style = document.createElement('style');
            style.textContent = `
                #turbo-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(26, 26, 46, 0.3);
                    backdrop-filter: blur(2px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 99999;
                    opacity: 0;
                    visibility: hidden;
                    transition: opacity 0.15s ease, visibility 0.15s ease;
                }
                #turbo-overlay.active {
                    opacity: 1;
                    visibility: visible;
                }
                .turbo-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(255,255,255,0.2);
                    border-top-color: #667eea;
                    border-radius: 50%;
                    animation: turbo-spin 0.6s linear infinite;
                }
                @keyframes turbo-spin {
                    to { transform: rotate(360deg); }
                }
                
                /* Page transition animations */
                .turbo-fade-out {
                    animation: turboFadeOut 0.15s ease forwards;
                }
                .turbo-fade-in {
                    animation: turboFadeIn 0.2s ease forwards;
                }
                @keyframes turboFadeOut {
                    from { opacity: 1; transform: translateY(0); }
                    to { opacity: 0; transform: translateY(-10px); }
                }
                @keyframes turboFadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        },

        handleClick(e) {
            const link = e.target.closest('a');
            if (!link) return;

            const href = link.getAttribute('href');
            if (!this.shouldNavigate(link, href)) return;

            e.preventDefault();
            this.navigate(href);
        },

        shouldNavigate(link, href) {
            // Skip if no href
            if (!href) return false;
            
            // Skip external links
            if (href.startsWith('http') && !href.includes(location.host)) return false;
            
            // Skip anchors
            if (href.startsWith('#')) return false;
            
            // Skip downloads
            if (link.hasAttribute('download')) return false;
            
            // Skip target="_blank"
            if (link.target === '_blank') return false;
            
            // Skip javascript: links
            if (href.startsWith('javascript:')) return false;
            
            // Skip API calls
            if (href.includes('/api/')) return false;
            
            // Skip auth redirects
            if (href.includes('/auth/')) return false;

            return true;
        },

        async navigate(url, pushState = true) {
            if (this.isNavigating) return;
            
            // Resolve relative URLs
            const fullUrl = new URL(url, location.origin).href;
            
            // Skip if same page
            if (fullUrl === this.currentUrl) return;

            this.isNavigating = true;
            const overlay = document.getElementById('turbo-overlay');
            const main = document.querySelector('main, .main-content, body > div:not(#turbo-overlay):not(script)') || document.body;

            try {
                // Start transition
                main.classList.add('turbo-fade-out');
                
                // Show loading after short delay (feels snappier)
                const loadingTimeout = setTimeout(() => {
                    overlay.classList.add('active');
                }, 100);

                // Fetch page (from cache or network)
                const html = await this.fetchPage(fullUrl);
                
                clearTimeout(loadingTimeout);

                // Parse and update DOM
                await this.updatePage(html, fullUrl);

                // Update history
                if (pushState) {
                    history.pushState({ turbo: true }, '', fullUrl);
                }

                this.currentUrl = fullUrl;

                // Hide loading
                overlay.classList.remove('active');

                // Fade in new content
                const newMain = document.querySelector('main, .main-content, body > div:not(#turbo-overlay):not(script)') || document.body;
                newMain.classList.add('turbo-fade-in');
                
                setTimeout(() => {
                    newMain.classList.remove('turbo-fade-in');
                }, 200);

                // Scroll to top
                window.scrollTo({ top: 0, behavior: 'instant' });

                // Dispatch event
                window.dispatchEvent(new CustomEvent('turbo:load', { detail: { url: fullUrl } }));

            } catch (error) {
                console.error('TurboNav error:', error);
                // Fallback to normal navigation
                location.href = fullUrl;
            } finally {
                this.isNavigating = false;
                main.classList.remove('turbo-fade-out');
            }
        },

        async fetchPage(url) {
            // Check cache first
            if (this.cache.has(url)) {
                return this.cache.get(url);
            }

            const response = await fetch(url, {
                headers: { 'X-Turbo': 'true' }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const html = await response.text();
            
            // Cache the page
            this.cache.set(url, html);
            
            // Limit cache size
            if (this.cache.size > 20) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }

            return html;
        },

        async updatePage(html, url) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Update title
            document.title = doc.title;

            // Update body content
            const newBody = doc.body;
            const oldBody = document.body;

            // Preserve turbo overlay
            const overlay = document.getElementById('turbo-overlay');
            
            // Replace body content
            oldBody.innerHTML = newBody.innerHTML;
            
            // Re-add overlay
            if (overlay) {
                document.body.appendChild(overlay);
            } else {
                this.createOverlay();
            }

            // Copy body attributes
            Array.from(newBody.attributes).forEach(attr => {
                oldBody.setAttribute(attr.name, attr.value);
            });

            // Execute new scripts
            await this.executeScripts(doc);

            // Re-init navigation components
            this.reinitComponents();
        },

        async executeScripts(doc) {
            const scripts = doc.querySelectorAll('script:not([type="application/json"])');
            
            for (const oldScript of scripts) {
                // Skip external scripts that are already loaded
                if (oldScript.src && document.querySelector(`script[src="${oldScript.src}"]`)) {
                    continue;
                }

                const newScript = document.createElement('script');
                
                if (oldScript.src) {
                    newScript.src = oldScript.src;
                    await new Promise((resolve, reject) => {
                        newScript.onload = resolve;
                        newScript.onerror = reject;
                        document.body.appendChild(newScript);
                    });
                } else if (oldScript.textContent) {
                    newScript.textContent = oldScript.textContent;
                    document.body.appendChild(newScript);
                }
            }
        },

        reinitComponents() {
            // Re-init nav loader if exists
            if (typeof loadNavigation === 'function') {
                loadNavigation();
            }

            // Re-init particles if on home page
            if (typeof initParticles === 'function' && document.getElementById('particles-js')) {
                initParticles();
            }

            // Re-init any page-specific initializers
            if (typeof pageInit === 'function') {
                pageInit();
            }

            // Dispatch DOMContentLoaded for scripts that listen to it
            document.dispatchEvent(new Event('DOMContentLoaded'));
        },

        handlePopState(e) {
            if (e.state?.turbo || this.cache.has(location.href)) {
                this.navigate(location.href, false);
            } else {
                // Full reload for pages not in history
                location.reload();
            }
        },

        handleHover(e) {
            const link = e.target.closest('a');
            if (!link) return;

            const href = link.getAttribute('href');
            if (!this.shouldNavigate(link, href)) return;

            const fullUrl = new URL(href, location.origin).href;
            
            // Don't preload if already cached or in queue
            if (this.cache.has(fullUrl) || this.preloadQueue.has(fullUrl)) return;

            this.preloadQueue.add(fullUrl);

            // Preload after short delay (avoid preloading on quick hovers)
            setTimeout(() => {
                if (this.preloadQueue.has(fullUrl)) {
                    this.preload(fullUrl);
                }
            }, 100);
        },

        async preload(url) {
            try {
                await this.fetchPage(url);
                console.log('⚡ Preloaded:', url);
            } catch (e) {
                // Ignore preload errors
            } finally {
                this.preloadQueue.delete(url);
            }
        },

        // Manual cache clear
        clearCache() {
            this.cache.clear();
            console.log('⚡ Cache cleared');
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => TurboNav.init());
    } else {
        TurboNav.init();
    }

    // Expose globally
    window.TurboNav = TurboNav;

})();
