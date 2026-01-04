// Navigation Loader Helper
// این فایل رو در همه صفحات include کنید

(function() {
    // Load Navigation Component
    function loadNavigation() {
        fetch('/components/nav-header.html')
            .then(response => response.text())
            .then(html => {
                // Try both possible container IDs
                let navContainer = document.getElementById('mainNav') || document.getElementById('navHeader');
                if (!navContainer) {
                    navContainer = document.createElement('div');
                    navContainer.id = 'navHeader';
                    document.body.insertBefore(navContainer, document.body.firstChild);
                }
                navContainer.innerHTML = html;
                
                // Execute scripts in the loaded HTML
                const scripts = navContainer.querySelectorAll('script');
                scripts.forEach(script => {
                    const newScript = document.createElement('script');
                    newScript.textContent = script.textContent;
                    document.body.appendChild(newScript);
                });
                
                // Trigger event for other scripts
                window.dispatchEvent(new Event('navigationLoaded'));
            })
            .catch(error => console.error('Error loading navigation:', error));
    }

    // Auto-load on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNavigation);
    } else {
        loadNavigation();
    }
})();
