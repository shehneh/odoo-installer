/**
 * OdooMaster Unified Navigation System v2
 * سیستم ناوبری یکپارچه با پشتیبانی از لاگین
 */

// Check if user is logged in
let isLoggedIn = false;
let currentUser = null;

async function checkLoginStatus() {
    try {
        const response = await fetch('/api/user-status');
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.user) {
                isLoggedIn = true;
                currentUser = result.user;
                return true;
            }
        }
    } catch (error) {
        console.log('Not logged in');
    }
    isLoggedIn = false;
    currentUser = null;
    return false;
}

// Navigation structure based on login status
function getNavStructure() {
    if (isLoggedIn) {
        return {
            main: [
                { title: 'صفحه اصلی', url: '/index.html', icon: 'fa-home' },
                { title: 'دمو رایگان', url: '/demo.html', icon: 'fa-eye' }
            ],
            user: [
                { title: 'ساخت دیتابیس', url: '/onboarding.html', icon: 'fa-rocket', highlight: true },
                { title: 'حساب کاربری', url: '/profile.html', icon: 'fa-user' },
                { title: 'نصب ماژول‌ها', url: '/install_modules.html', icon: 'fa-puzzle-piece' }
            ],
            resources: [
                { title: 'نصب آفلاین', url: '/install.html', icon: 'fa-download' },
                { title: 'مستندات', url: '/docs.html', icon: 'fa-book' }
            ],
            admin: [
                { title: 'پنل ادمین', url: '/admin_customers.html', icon: 'fa-shield-alt' }
            ]
        };
    } else {
        return {
            main: [
                { title: 'صفحه اصلی', url: '/index.html', icon: 'fa-home' },
                { title: 'دمو رایگان', url: '/demo.html', icon: 'fa-eye' }
            ],
            account: [
                { title: 'ثبت نام', url: '/user-register.html', icon: 'fa-user-plus', highlight: true },
                { title: 'ورود', url: '/user-login.html', icon: 'fa-sign-in-alt' }
            ],
            resources: [
                { title: 'نصب آفلاین', url: '/install.html', icon: 'fa-download' },
                { title: 'مستندات', url: '/docs.html', icon: 'fa-book' }
            ]
        };
    }
}

// Create unified navigation bar
function createUnifiedNav() {
    const currentPath = window.location.pathname;
    const currentPage = currentPath.split('/').pop() || 'index.html';
    const navStructure = getNavStructure();
    
    let groupsHTML = '';
    
    // Main group
    groupsHTML += `
        <div class="nav-group">
            <span class="nav-group-title">اصلی</span>
            ${navStructure.main.map(item => `
                <a href="${item.url}" class="nav-item ${currentPage === item.url.split('/').pop() ? 'active' : ''} ${item.highlight ? 'highlight' : ''}">
                    <i class="fas ${item.icon}"></i>
                    <span>${item.title}</span>
                </a>
            `).join('')}
        </div>
    `;
    
    // User/Account group
    if (isLoggedIn && navStructure.user) {
        groupsHTML += `
            <div class="nav-group">
                <span class="nav-group-title">کاربری</span>
                ${navStructure.user.map(item => `
                    <a href="${item.url}" class="nav-item ${currentPage === item.url.split('/').pop() ? 'active' : ''} ${item.highlight ? 'highlight' : ''}">
                        <i class="fas ${item.icon}"></i>
                        <span>${item.title}</span>
                    </a>
                `).join('')}
            </div>
        `;
    } else if (navStructure.account) {
        groupsHTML += `
            <div class="nav-group">
                <span class="nav-group-title">حساب کاربری</span>
                ${navStructure.account.map(item => `
                    <a href="${item.url}" class="nav-item ${currentPage === item.url.split('/').pop() ? 'active' : ''} ${item.highlight ? 'highlight' : ''}">
                        <i class="fas ${item.icon}"></i>
                        <span>${item.title}</span>
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    // Resources group
    groupsHTML += `
        <div class="nav-group">
            <span class="nav-group-title">منابع</span>
            ${navStructure.resources.map(item => `
                <a href="${item.url}" class="nav-item ${currentPage === item.url.split('/').pop() ? 'active' : ''}">
                    <i class="fas ${item.icon}"></i>
                    <span>${item.title}</span>
                </a>
            `).join('')}
        </div>
    `;
    
    // Admin group (only for logged in)
    if (isLoggedIn && navStructure.admin) {
        groupsHTML += `
            <div class="nav-group">
                ${navStructure.admin.map(item => `
                    <a href="${item.url}" class="nav-item ${currentPage === item.url.split('/').pop() ? 'active' : ''}">
                        <i class="fas ${item.icon}"></i>
                        <span>${item.title}</span>
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    // User status display
    let userStatusHTML = '';
    if (isLoggedIn && currentUser) {
        userStatusHTML = `
            <div class="user-status">
                <span class="user-name">${currentUser.name || currentUser.email || currentUser.phone}</span>
                <button class="nav-item logout-btn" id="logoutBtn" title="خروج">
                    <i class="fas fa-sign-out-alt"></i>
                </button>
            </div>
        `;
    }
    
    const navHTML = `
        <nav class="unified-nav glass-effect" id="unifiedNav">
            <div class="nav-container">
                <a href="/index.html" class="unified-logo">
                    <i class="fas fa-cube"></i>
                    <span>Odoo<strong>Master</strong></span>
                </a>
                
                <div class="nav-groups">
                    ${groupsHTML}
                </div>
                
                <div class="nav-actions">
                    ${userStatusHTML}
                    <button class="nav-toggle" id="navToggle">
                        <i class="fas fa-bars"></i>
                    </button>
                </div>
            </div>
        </nav>
    `;
    
    // Remove existing nav if any
    const existingNav = document.getElementById('unifiedNav');
    if (existingNav) {
        existingNav.remove();
    }
    
    document.body.insertAdjacentHTML('afterbegin', navHTML);
    
    // Event listeners
    const navToggle = document.getElementById('navToggle');
    const unifiedNav = document.getElementById('unifiedNav');
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            unifiedNav.classList.toggle('mobile-open');
        });
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/logout', { method: 'POST' });
                window.location.href = '/index.html';
            } catch (error) {
                console.error('Logout error:', error);
            }
        });
    }
    
    // Close mobile menu on outside click
    document.addEventListener('click', (e) => {
        if (unifiedNav && !unifiedNav.contains(e.target) && unifiedNav.classList.contains('mobile-open')) {
            unifiedNav.classList.remove('mobile-open');
        }
    });
}

// Create breadcrumb navigation
function createBreadcrumb() {
    const currentPath = window.location.pathname;
    const currentPage = currentPath.split('/').pop() || 'index.html';
    
    const pageNames = {
        'index.html': 'صفحه اصلی',
        'demo.html': 'دمو رایگان',
        'user-login.html': 'ورود',
        'user-register.html': 'ثبت نام',
        'verify-account.html': 'تایید حساب',
        'onboarding.html': 'ساخت دیتابیس',
        'profile.html': 'حساب کاربری',
        'install.html': 'نصب آفلاین',
        'install_modules.html': 'نصب ماژول‌ها',
        'docs.html': 'مستندات',
        'downloads.html': 'دانلود',
        'admin_customers.html': 'پنل ادمین'
    };
    
    const pageName = pageNames[currentPage] || currentPage;
    
    if (currentPage === 'index.html') return; // No breadcrumb on home
    
    const breadcrumbHTML = `
        <div class="breadcrumb-nav">
            <a href="/index.html"><i class="fas fa-home"></i> خانه</a>
            <i class="fas fa-chevron-left"></i>
            <span>${pageName}</span>
        </div>
    `;
    
    const mainContent = document.querySelector('main, .container, .demo-container, .installer-container, .onboarding-container, .login-container, .register-container, .verify-container, .profile-container');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', breadcrumbHTML);
    }
}

// Create quick action floating button (compass)
function createQuickActions() {
    const compassDisabled = localStorage.getItem('compassDisabled') === 'true';
    if (compassDisabled) return;
    
    const navStructure = getNavStructure();
    
    let quickItemsHTML = '';
    
    if (isLoggedIn) {
        quickItemsHTML = `
            <a href="/onboarding.html" class="quick-action-item" style="background: linear-gradient(135deg, rgba(72, 187, 120, 0.3), rgba(56, 161, 105, 0.3));">
                <i class="fas fa-rocket"></i>
                <span>ساخت دیتابیس</span>
            </a>
            <a href="/profile.html" class="quick-action-item">
                <i class="fas fa-user"></i>
                <span>حساب کاربری</span>
            </a>
            <a href="/install_modules.html" class="quick-action-item">
                <i class="fas fa-puzzle-piece"></i>
                <span>نصب ماژول‌ها</span>
            </a>
        `;
    } else {
        quickItemsHTML = `
            <a href="/user-register.html" class="quick-action-item" style="background: linear-gradient(135deg, rgba(113, 75, 103, 0.3), rgba(147, 112, 219, 0.3));">
                <i class="fas fa-user-plus"></i>
                <span>ثبت نام</span>
            </a>
            <a href="/user-login.html" class="quick-action-item">
                <i class="fas fa-sign-in-alt"></i>
                <span>ورود</span>
            </a>
        `;
    }
    
    quickItemsHTML += `
        <a href="/demo.html" class="quick-action-item">
            <i class="fas fa-eye"></i>
            <span>دمو رایگان</span>
        </a>
        <a href="/docs.html" class="quick-action-item">
            <i class="fas fa-book"></i>
            <span>مستندات</span>
        </a>
    `;
    
    const quickActionsHTML = `
        <div class="quick-actions" id="quickActions">
            <button class="quick-action-trigger" id="quickActionTrigger" title="منوی سریع">
                <i class="fas fa-compass"></i>
            </button>
            <div class="quick-action-menu">
                ${quickItemsHTML}
            </div>
        </div>
    `;
    
    // Remove existing
    const existing = document.getElementById('quickActions');
    if (existing) existing.remove();
    
    document.body.insertAdjacentHTML('beforeend', quickActionsHTML);
    
    const trigger = document.getElementById('quickActionTrigger');
    const quickActions = document.getElementById('quickActions');
    
    if (trigger) {
        trigger.addEventListener('click', () => {
            quickActions.classList.toggle('active');
        });
    }
    
    // Close on outside click
    document.addEventListener('click', (e) => {
        if (quickActions && !quickActions.contains(e.target)) {
            quickActions.classList.remove('active');
        }
    });
}

// Initialize navigation
async function initNavigation() {
    await checkLoginStatus();
    createUnifiedNav();
    createBreadcrumb();
    createQuickActions();
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavigation);
} else {
    initNavigation();
}

// Export for manual use
window.OdooMasterNav = {
    init: initNavigation,
    checkLogin: checkLoginStatus,
    isLoggedIn: () => isLoggedIn,
    getUser: () => currentUser
};
