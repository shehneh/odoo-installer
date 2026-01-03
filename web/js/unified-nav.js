/**
 * Unified Navigation System for OdooMaster
 * یک منوی یکپارچه برای تمام صفحات
 */

// Navigation structure
const navStructure = {
    main: [
        { title: 'صفحه اصلی', url: 'index.html', icon: 'fa-home' },
        { title: 'دمو رایگان', url: 'demo.html', icon: 'fa-eye' },
        { title: 'نصب آنلاین', url: 'install.html', icon: 'fa-rocket', highlight: true },
        { title: 'داشبورد من', url: 'dashboard.html', icon: 'fa-th-large' }
    ],
    odoo: [
        { title: 'ثبت دیتابیس اختصاصی', url: 'register_tenant.html', icon: 'fa-user-plus', highlight: true },
        { title: 'ورود کاربران', url: 'login.html', icon: 'fa-sign-in-alt' },
        { title: 'داشبورد کاربر', url: 'user_dashboard.html', icon: 'fa-user' },
        { title: 'دانلودها', url: 'downloads.html', icon: 'fa-download' },
        { title: 'پشتیبانی', url: 'support.html', icon: 'fa-headset' }
    ],
    info: [
        { title: 'مستندات', url: 'docs.html', icon: 'fa-book' },
        { title: 'لایسنس‌ها', url: 'licenses.html', icon: 'fa-key' },
        { title: 'قیمت‌گذاری', url: 'payment.html', icon: 'fa-credit-card' },
        { title: 'راهنمای چند دیتابیس', url: 'multi_database_help.html', icon: 'fa-database' }
    ]
};

// Create unified navigation bar
function createUnifiedNav() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    const navHTML = `
        <nav class="unified-nav glass-effect" id="unifiedNav">
            <div class="nav-container">
                <a href="index.html" class="unified-logo">
                    <i class="fas fa-cube"></i>
                    <span>Odoo<strong>Master</strong></span>
                </a>
                
                <div class="nav-groups">
                    <div class="nav-group">
                        <span class="nav-group-title">منوی اصلی</span>
                        ${navStructure.main.map(item => `
                            <a href="${item.url}" class="nav-item ${currentPage === item.url ? 'active' : ''} ${item.highlight ? 'highlight' : ''}">
                                <i class="fas ${item.icon}"></i>
                                <span>${item.title}</span>
                            </a>
                        `).join('')}
                    </div>
                    
                    <div class="nav-group">
                        <span class="nav-group-title">Odoo</span>
                        ${navStructure.odoo.map(item => `
                            <a href="${item.url}" class="nav-item ${currentPage === item.url ? 'active' : ''}">
                                <i class="fas ${item.icon}"></i>
                                <span>${item.title}</span>
                            </a>
                        `).join('')}
                    </div>
                    
                    <div class="nav-group">
                        <span class="nav-group-title">اطلاعات</span>
                        ${navStructure.info.map(item => `
                            <a href="${item.url}" class="nav-item ${currentPage === item.url ? 'active' : ''}">
                                <i class="fas ${item.icon}"></i>
                                <span>${item.title}</span>
                            </a>
                        `).join('')}
                    </div>
                </div>
                
                <div class="nav-actions">
                    <button class="nav-toggle" id="navToggle">
                        <i class="fas fa-bars"></i>
                    </button>
                </div>
            </div>
        </nav>
    `;
    
    // Insert at the beginning of body
    document.body.insertAdjacentHTML('afterbegin', navHTML);
    
    // Add mobile menu toggle
    const navToggle = document.getElementById('navToggle');
    const unifiedNav = document.getElementById('unifiedNav');
    
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            unifiedNav.classList.toggle('mobile-open');
        });
    }
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!unifiedNav.contains(e.target) && unifiedNav.classList.contains('mobile-open')) {
            unifiedNav.classList.remove('mobile-open');
        }
    });
}

// Create breadcrumb navigation
function createBreadcrumb() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    let pageName = 'صفحه اصلی';
    
    // Find page name
    for (const category of Object.values(navStructure)) {
        const page = category.find(item => item.url === currentPage);
        if (page) {
            pageName = page.title;
            break;
        }
    }
    
    const breadcrumbHTML = `
        <div class="breadcrumb-nav">
            <a href="index.html"><i class="fas fa-home"></i> خانه</a>
            <i class="fas fa-chevron-left"></i>
            <span>${pageName}</span>
        </div>
    `;
    
    const mainContent = document.querySelector('main, .container, .demo-container, .installer-container');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', breadcrumbHTML);
    }
}

// Add quick action floating button
function createQuickActions() {
    // Check if compass is disabled
    const compassDisabled = localStorage.getItem('compassDisabled') === 'true';
    if (compassDisabled) {
        return; // Don't create compass if disabled
    }
    
    const quickActionsHTML = `
        <div class="quick-actions" id="quickActions">
            <button class="quick-action-trigger" id="quickActionTrigger">
                <i class="fas fa-compass"></i>
            </button>
            <div class="quick-action-menu">
                <a href="register_tenant.html" class="quick-action-item register" style="background: linear-gradient(135deg, rgba(113, 75, 103, 0.3), rgba(147, 112, 219, 0.3)); border-color: rgba(113, 75, 103, 0.5);">
                    <i class="fas fa-user-plus"></i>
                    <span>ساخت دیتابیس اختصاصی</span>
                </a>
                <a href="install.html" class="quick-action-item install">
                    <i class="fas fa-rocket"></i>
                    <span>نصب آنلاین</span>
                </a>
                <a href="demo.html" class="quick-action-item demo">
                    <i class="fas fa-play-circle"></i>
                    <span>دمو رایگان</span>
                </a>
                <a href="dashboard.html" class="quick-action-item dashboard">
                    <i class="fas fa-th-large"></i>
                    <span>داشبورد من</span>
                </a>
                <a href="login.html" class="quick-action-item login">
                    <i class="fas fa-sign-in-alt"></i>
                    <span>ورود کاربر</span>
                </a>
                <a href="index.html" class="quick-action-item home">
                    <i class="fas fa-home"></i>
                    <span>صفحه اصلی</span>
                </a>
                <button class="quick-action-item disable" id="disableCompass" style="background: rgba(220, 53, 69, 0.2); border-color: rgba(220, 53, 69, 0.5); cursor: pointer; border: 1px solid rgba(220, 53, 69, 0.5); width: 100%;">
                    <i class="fas fa-times-circle"></i>
                    <span>غیرفعال کردن قطب‌نما</span>
                </button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', quickActionsHTML);
    
    const trigger = document.getElementById('quickActionTrigger');
    const quickActions = document.getElementById('quickActions');
    const disableBtn = document.getElementById('disableCompass');
    
    if (trigger) {
        trigger.addEventListener('click', () => {
            quickActions.classList.toggle('active');
        });
    }
    
    // Handle disable compass button
    if (disableBtn) {
        disableBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('آیا مطمئن هستید که می‌خواهید قطب‌نما را غیرفعال کنید؟\n\nبرای فعال‌سازی دوباره، از تنظیمات مرورگر یا Console استفاده کنید:\nlocalStorage.removeItem("compassDisabled")')) {
                localStorage.setItem('compassDisabled', 'true');
                quickActions.style.display = 'none';
                alert('قطب‌نما غیرفعال شد. برای فعال‌سازی دوباره صفحه را رفرش کنید و از Console استفاده کنید:\nlocalStorage.removeItem("compassDisabled")');
            }
        });
    }
}

// Add compass toggle button to nav
function addCompassToggle() {
    const compassDisabled = localStorage.getItem('compassDisabled') === 'true';
    
    if (compassDisabled) {
        // Add enable button to nav
        const navActions = document.querySelector('.nav-actions');
        if (navActions) {
            const enableBtn = document.createElement('button');
            enableBtn.className = 'nav-item';
            enableBtn.innerHTML = '<i class="fas fa-compass"></i><span>فعال‌سازی قطب‌نما</span>';
            enableBtn.style.cssText = 'background: rgba(40, 167, 69, 0.2); border: 1px solid rgba(40, 167, 69, 0.5); cursor: pointer; margin-left: 10px;';
            enableBtn.addEventListener('click', () => {
                localStorage.removeItem('compassDisabled');
                location.reload();
            });
            navActions.insertBefore(enableBtn, navActions.firstChild);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    createUnifiedNav();
    createBreadcrumb();
    createQuickActions();
    addCompassToggle();
    
    console.log('✅ Unified Navigation System loaded');
    console.log('💡 Compass status:', localStorage.getItem('compassDisabled') === 'true' ? 'Disabled' : 'Enabled');
});
