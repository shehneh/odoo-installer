// Global Navigation Scripts
// این فایل رو در همه صفحات include کنید برای dropdown و menu functionality

(function() {
    'use strict';

    // Toggle dropdown menus on click
    function initDropdowns() {
        document.querySelectorAll('.dropdown').forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle');
            if (toggle) {
                toggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Close other dropdowns
                    document.querySelectorAll('.dropdown').forEach(d => {
                        if (d !== dropdown) d.classList.remove('active');
                    });
                    
                    dropdown.classList.toggle('active');
                });
            }
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('.dropdown').forEach(d => {
                    d.classList.remove('active');
                });
            }
        });
    }

    // Toggle compass menu
    function initCompass() {
        const compassNav = document.querySelector('.compass-nav, #compassNav');
        if (compassNav) {
            const compassIcon = compassNav.querySelector('.compass-icon');
            if (compassIcon) {
                compassIcon.addEventListener('click', (e) => {
                    e.stopPropagation();
                    compassNav.classList.toggle('active');
                });
            }

            // Close compass when clicking outside
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.compass-nav, #compassNav')) {
                    compassNav.classList.remove('active');
                }
            });

            // Keep menu open when clicking inside it
            const compassMenu = compassNav.querySelector('.compass-menu');
            if (compassMenu) {
                compassMenu.addEventListener('click', (e) => {
                    e.stopPropagation();
                });
            }
        }
    }

    // Toggle mobile menu
    function initMobileMenu() {
        const mobileBtn = document.getElementById('mobileMenuBtn');
        const navMenu = document.querySelector('.nav-menu, .nav-links');
        
        if (mobileBtn && navMenu) {
            mobileBtn.addEventListener('click', () => {
                navMenu.classList.toggle('active');
                mobileBtn.classList.toggle('active');
            });
        }
    }

    // Initialize on DOM ready
    function init() {
        initDropdowns();
        initCompass();
        initMobileMenu();
    }

    // Auto-initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Re-initialize after dynamic content loads (for nav-loader.js)
    window.addEventListener('navigationLoaded', init);
    
    // Export init function for manual initialization
    window.initGlobalNav = init;
})();
