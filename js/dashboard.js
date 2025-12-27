/* ============================================
   OdooMaster - Dashboard JavaScript
   User Panel & Gamification Logic
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initThemeButton();
    initSidebar();
    initNotificationPanel();
    initXPAnimation();
    initAchievements();
    initDownloadProgress();
    initInstallerZipDownload();
    initActivityFeed();
    initStatsCounter();
    initQuickSearch();
    initMobileMenu();
    checkAdminAccess(); // Check if user is admin and show admin panel button
    loadUserData(); // Load real user data including licenses
    
    // Listen for language change to reload user data
    document.addEventListener('languageChange', () => {
        loadUserData();
    });
});

function showToastSafe(message, type = 'info') {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }
    alert(message);
}

/* ============================================
   Load Real User Data (Licenses, Stats, etc.)
   ============================================ */

async function loadUserData() {
    // Check login
    if (!window.API || !API.isLoggedIn()) {
        // Redirect to login
        window.location.href = 'login.html?redirect=dashboard.html';
        return;
    }

    try {
        const response = await API.getMe();
        if (!response || !response.user) {
            window.location.href = 'login.html?redirect=dashboard.html';
            return;
        }

        const user = response.user;
        const licenses = response.licenses || [];

        // Update welcome message
        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            const name = user.name || (window.I18N ? I18N.t('dashboard.dearUser', 'Dear User') : 'کاربر عزیز');
            userNameEl.textContent = name;
        }

        // Update user card in sidebar
        const userInfo = document.querySelector('.user-info');
        if (userInfo) {
            const name = user.name || (window.I18N ? I18N.t('dashboard.dearUser', 'User') : 'کاربر');
            const activeLicense = licenses.find(l => l.status === 'active' && l.plan !== 'trial');
            const defaultPlan = window.I18N ? I18N.t('plan.free', 'Free Plan') : 'پلن رایگان';
            const planName = activeLicense ? activeLicense.plan_name || activeLicense.plan : defaultPlan;
            userInfo.innerHTML = `<strong>${name}</strong><span>${planName}</span>`;
        }

        // Update avatar
        const userAvatar = document.querySelector('.user-avatar img');
        if (userAvatar && user.name) {
            userAvatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=714B67&color=fff`;
        }

        // Load licenses
        renderUserLicenses(licenses);
        updateStats(licenses, user);

    } catch (e) {
        console.error('Error loading user data:', e);
        // If token is invalid, redirect to login
        if (e?.message?.includes('توکن') || e?.message?.includes('ورود')) {
            localStorage.removeItem('authToken');
            window.location.href = 'login.html?redirect=dashboard.html';
        }
    }
}

function renderUserLicenses(licenses) {
    const licensesList = document.querySelector('.licenses-list');
    if (!licensesList) return;

    // Clear static content
    licensesList.innerHTML = '';

    if (!licenses || licenses.length === 0) {
        licensesList.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 40px 20px;">
                <i class="fas fa-key" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 16px; display: block;"></i>
                <p style="color: var(--text-secondary); margin-bottom: 20px;">هنوز لایسنسی ندارید</p>
                <a href="payment.html" class="btn btn-primary btn-glow">
                    <i class="fas fa-shopping-cart"></i>
                    خرید لایسنس
                </a>
            </div>
        `;
        return;
    }

    licenses.forEach(lic => {
        const isActive = lic.status === 'active';
        const isTrial = (lic.plan || '').toLowerCase() === 'trial';
        const isExpired = lic.expires_at && new Date(lic.expires_at) < new Date();
        
        // Calculate days remaining
        let daysRemaining = '—';
        if (lic.expires_at) {
            const expDate = new Date(lic.expires_at);
            const now = new Date();
            const diffTime = expDate - now;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            if (diffDays > 0) {
                daysRemaining = `${diffDays} روز مانده`;
            } else if (diffDays === 0) {
                daysRemaining = 'امروز منقضی می‌شود';
            } else {
                daysRemaining = 'منقضی شده';
            }
        }

        let statusClass = 'active';
        let statusText = 'فعال';
        if (!isActive) {
            statusClass = 'inactive';
            statusText = 'غیرفعال';
        } else if (isExpired) {
            statusClass = 'expired';
            statusText = 'منقضی';
        } else if (isTrial) {
            statusClass = 'trial';
            statusText = 'آزمایشی';
        }

        const iconClass = isTrial ? 'seedling' : 'gem';
        const iconStyle = isTrial ? 'starter' : 'pro';

        const item = document.createElement('div');
        item.className = 'license-item';
        item.innerHTML = `
            <div class="license-info">
                <div class="license-icon ${iconStyle}">
                    <i class="fas fa-${iconClass}"></i>
                </div>
                <div class="license-details">
                    <strong>${lic.plan_name || lic.plan || 'پلن'}</strong>
                    <span style="font-family: monospace; font-size: 0.85rem;">${maskKey(lic.key)}</span>
                </div>
            </div>
            <div class="license-status">
                <span class="status-badge ${statusClass}">${statusText}</span>
                <span class="expiry">${daysRemaining}</span>
            </div>
            <div class="license-actions">
                <button class="icon-btn copy-btn" title="کپی کلید" data-key="${lic.key}">
                    <i class="fas fa-copy"></i>
                </button>
                <a href="licenses.html" class="icon-btn" title="مدیریت">
                    <i class="fas fa-cog"></i>
                </a>
            </div>
        `;

        // Copy button handler
        const copyBtn = item.querySelector('.copy-btn');
        copyBtn?.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(lic.key);
                showToastSafe('کلید لایسنس کپی شد', 'success');
            } catch {
                showToastSafe('کپی انجام نشد', 'error');
            }
        });

        licensesList.appendChild(item);
    });

    // Add "buy more" button if needed
    const buyMoreBtn = document.createElement('div');
    buyMoreBtn.style.cssText = 'text-align: center; margin-top: 16px;';
    buyMoreBtn.innerHTML = `
        <a href="payment.html" class="btn btn-outline" style="width: 100%;">
            <i class="fas fa-plus"></i>
            خرید لایسنس جدید
        </a>
    `;
    licensesList.appendChild(buyMoreBtn);
}

function maskKey(key) {
    if (!key || key.length < 12) return key || '';
    return key.slice(0, 5) + '-****-' + key.slice(-5);
}

function updateStats(licenses, userData) {
    // Update stat cards with real data
    const activeLicenses = licenses.filter(l => l.status === 'active').length;
    const downloads = userData.downloads || 0;
    
    // Find earliest expiry among active licenses
    let daysRemaining = '—';
    const activeLics = licenses.filter(l => l.status === 'active' && l.expires_at);
    if (activeLics.length > 0) {
        const sortedByExpiry = activeLics.sort((a, b) => new Date(a.expires_at) - new Date(b.expires_at));
        const earliestExpiry = new Date(sortedByExpiry[0].expires_at);
        const now = new Date();
        const diffDays = Math.ceil((earliestExpiry - now) / (1000 * 60 * 60 * 24));
        daysRemaining = diffDays > 0 ? diffDays : 0;
    }

    // Update stat values
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        const label = card.querySelector('.stat-label')?.textContent || '';
        const valueEl = card.querySelector('.stat-value');
        
        if (label.includes('لایسنس') && valueEl) {
            valueEl.textContent = toPersianDigits(activeLicenses);
        } else if (label.includes('دانلود') && valueEl) {
            valueEl.textContent = toPersianDigits(downloads);
        } else if (label.includes('روز') && valueEl) {
            valueEl.textContent = typeof daysRemaining === 'number' ? toPersianDigits(daysRemaining) : daysRemaining;
        }
    });

    // Update license badge in nav
    const navBadge = document.querySelector('.nav-item[href="#licenses"] .nav-badge');
    if (navBadge) {
        navBadge.textContent = toPersianDigits(activeLicenses);
    }
}

function toPersianDigits(num) {
    const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return String(num).replace(/\d/g, d => persianDigits[parseInt(d)]);
}

/* ============================================
   Installer ZIP Download (Real)
   ============================================ */

function initInstallerZipDownload() {
    const btn = document.getElementById('downloadBtn');
    if (!btn) return;

    const progress = document.getElementById('downloadProgress');
    const progressText = progress?.querySelector('.progress-text');
    const progressFill = progress?.querySelector('.progress-fill');

    const setUi = (state) => {
        if (!progress) return;
        if (state === 'hide') {
            progress.style.display = 'none';
            if (progressFill) progressFill.style.width = '0%';
            if (progressText) progressText.textContent = 'در حال آمادهسازی...';
            return;
        }
        progress.style.display = 'block';
    };

    btn.addEventListener('click', async () => {
        if (!window.API || typeof window.API.requestDownload !== 'function') {
            showToastSafe('API آماده نیست. لطفاً سرور 5001 را اجرا کنید.', 'error');
            return;
        }

        const token = localStorage.getItem('authToken');
        if (!token) {
            window.location.href = 'login.html?redirect=dashboard.html';
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال آمادهسازی...';
        setUi('show');
        if (progressFill) progressFill.style.width = '30%';
        if (progressText) progressText.textContent = 'در حال آمادهسازی لینک دانلود...';

        try {
            // This download id exists in website/downloads.json
            const resp = await window.API.requestDownload('odoo19-lite-online');
            const url = resp && resp.download_url;
            if (!url) throw new Error('لینک دانلود آماده نشد');

            if (progressFill) progressFill.style.width = '100%';
            if (progressText) progressText.textContent = 'دانلود شروع شد.';
            window.open(url, '_blank', 'noopener');

            btn.innerHTML = '<i class="fas fa-check"></i> شروع شد';
            showToastSafe('دانلود در تب جدید شروع شد.', 'success');
        } catch (e) {
            const msg = (e && e.message) ? e.message : 'خطا در شروع دانلود';
            showToastSafe(msg, 'error');

            // If license is required, guide user to licenses section
            if (/لایسنس|خرید|معتبر/.test(msg)) {
                try {
                    history.replaceState(null, '', '#licenses');
                } catch (_) {}
                const target = document.querySelector('#licenses');
                target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            btn.innerHTML = '<i class="fas fa-download"></i> دانلود نصاب';
        } finally {
            btn.disabled = false;
            // Keep progress visible briefly
            setTimeout(() => setUi('hide'), 1200);
        }
    });
}

/* ============================================
   Theme Toggle (Dashboard)
   ============================================ */

function initThemeButton() {
    const btn = document.getElementById('themeBtn');
    if (!btn) return;

    const applyTheme = (isLight) => {
        document.documentElement.classList.toggle('light-theme', isLight);
        document.body.classList.toggle('light-theme', isLight);

        btn.innerHTML = isLight ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        btn.setAttribute('aria-pressed', isLight ? 'true' : 'false');
    };

    // initial state
    const savedTheme = localStorage.getItem('theme');
    applyTheme(savedTheme === 'light');

    btn.addEventListener('click', () => {
        const isLight = !document.body.classList.contains('light-theme');
        applyTheme(isLight);
        localStorage.setItem('theme', isLight ? 'light' : 'dark');

        // tiny feedback animation
        btn.style.transform = 'rotate(360deg) scale(1.1)';
        setTimeout(() => {
            btn.style.transform = '';
        }, 250);
    });
}

/* ============================================
   Sidebar Toggle
   ============================================ */

function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');
    const mainContent = document.querySelector('.main-content');

    if (!sidebar || !toggleBtn) return;

    // Load saved state
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
    }

    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });

    const navLinks = Array.from(document.querySelectorAll('.sidebar-nav a.nav-item'));

    const setActiveLink = (href) => {
        navLinks.forEach((a) => a.classList.remove('active'));
        const match = navLinks.find((a) => a.getAttribute('href') === href);
        if (match) match.classList.add('active');
    };

    const scrollToHashTarget = (hash) => {
        if (!hash || !hash.startsWith('#')) return false;
        const target = document.querySelector(hash);
        if (!target) return false;

        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return true;
    };

    const updateActiveFromLocation = () => {
        const hash = window.location.hash;
        if (hash === '#licenses' || hash === '#downloads') {
            setActiveLink(hash);
            scrollToHashTarget(hash);
            return;
        }

        // Default to dashboard item
        setActiveLink('dashboard.html');
    };

    // Intercept in-dashboard navigation
    const internalTargets = new Set(['#licenses', '#downloads']);
    document.addEventListener('click', (e) => {
        const a = e.target?.closest?.('a');
        if (!a) return;
        const href = a.getAttribute('href');
        if (!href || !internalTargets.has(href)) return;
        if (a.classList.contains('disabled-link')) return;

        e.preventDefault();
        setActiveLink(href);
        // Update URL hash without adding lots of history entries
        history.replaceState(null, '', href);
        scrollToHashTarget(href);
    });

    window.addEventListener('hashchange', updateActiveFromLocation);
    updateActiveFromLocation();
}

/* ============================================
   Notification Panel
   ============================================ */

function initNotificationPanel() {
    const notificationBtn = document.querySelector('.notification-btn');
    const panel = document.querySelector('.notification-panel');
    const overlay = document.querySelector('.panel-overlay');
    const closeBtn = document.querySelector('.panel-close');

    if (!notificationBtn || !panel) return;

    notificationBtn.addEventListener('click', () => {
        panel.classList.add('active');
        overlay?.classList.add('active');
        document.body.style.overflow = 'hidden';
    });

    const closePanel = () => {
        panel.classList.remove('active');
        overlay?.classList.remove('active');
        document.body.style.overflow = '';
    };

    closeBtn?.addEventListener('click', closePanel);
    overlay?.addEventListener('click', closePanel);

    // Keyboard shortcut
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && panel.classList.contains('active')) {
            closePanel();
        }
    });

    // Mark notification as read on click
    document.querySelectorAll('.notification-item').forEach(item => {
        item.addEventListener('click', () => {
            item.classList.remove('unread');
            updateNotificationBadge();
        });
    });
}

function updateNotificationBadge() {
    const badge = document.querySelector('.notification-badge');
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;

    if (badge) {
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'flex' : 'none';
    }
}

/* ============================================
   XP & Level Animation
   ============================================ */

function initXPAnimation() {
    const xpCircle = document.querySelector('.xp-circle .progress');
    const xpLevel = document.querySelector('.xp-level');
    const xpCurrent = document.querySelector('.xp-current');
    const xpNeeded = document.querySelector('.xp-needed');

    if (!xpCircle) return;

    // User XP data (would come from API)
    const userData = {
        level: 5,
        currentXP: 2750,
        xpToNextLevel: 3500
    };

    // Calculate progress percentage
    const progress = (userData.currentXP / userData.xpToNextLevel) * 100;
    const circumference = 2 * Math.PI * 70; // radius = 70
    const offset = circumference - (progress / 100) * circumference;

    // Animate the circle
    setTimeout(() => {
        xpCircle.style.strokeDashoffset = offset;
    }, 500);

    // Animate numbers
    if (xpLevel) animateNumber(xpLevel, userData.level);
    if (xpCurrent) animateNumber(xpCurrent, userData.currentXP);
    if (xpNeeded) animateNumber(xpNeeded, userData.xpToNextLevel);
}

function animateNumber(element, target, duration = 1500) {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.floor(start + (target - start) * easeOutQuart);

        element.textContent = current.toLocaleString('fa-IR');

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

/* ============================================
   Achievements System
   ============================================ */

function initAchievements() {
    const achievements = document.querySelectorAll('.achievement');

    achievements.forEach((achievement, index) => {
        // Staggered entrance animation
        achievement.style.opacity = '0';
        achievement.style.transform = 'scale(0.8)';

        setTimeout(() => {
            achievement.style.transition = 'all 0.4s ease';
            achievement.style.opacity = '1';
            achievement.style.transform = 'scale(1)';
        }, 100 + index * 100);

        // Hover tooltip
        achievement.addEventListener('mouseenter', showAchievementTooltip);
        achievement.addEventListener('mouseleave', hideAchievementTooltip);
    });
}

function showAchievementTooltip(e) {
    const achievement = e.currentTarget;
    const name = achievement.querySelector('.achievement-name')?.textContent;
    const xp = achievement.querySelector('.achievement-xp')?.textContent;
    const isLocked = achievement.classList.contains('locked');

    const tooltip = document.createElement('div');
    tooltip.classList.add('achievement-tooltip');
    tooltip.innerHTML = `
        <strong>${name}</strong>
        <span>${isLocked ? '🔒 قفل شده' : '✓ باز شده'}</span>
        ${xp ? `<span class="xp">${xp}</span>` : ''}
    `;

    document.body.appendChild(tooltip);

    const rect = achievement.getBoundingClientRect();
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
    tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
}

function hideAchievementTooltip() {
    document.querySelector('.achievement-tooltip')?.remove();
}

// Add achievement unlock animation
function unlockAchievement(achievementId) {
    const achievement = document.querySelector(`[data-achievement="${achievementId}"]`);
    if (!achievement || !achievement.classList.contains('locked')) return;

    // Unlock animation
    achievement.classList.remove('locked');
    achievement.classList.add('achievement-unlock');

    // Show confetti
    if (typeof createConfetti === 'function') {
        createConfetti(50);
    }

    // Show toast
    const name = achievement.querySelector('.achievement-name')?.textContent;
    if (typeof showToast === 'function') {
        showToast(`🏆 دستاورد جدید: ${name}`, 'success');
    }

    // Play sound (if available)
    playAchievementSound();
}

function playAchievementSound() {
    const audio = new Audio('sounds/achievement.mp3');
    audio.volume = 0.5;
    audio.play().catch(() => {});
}

/* ============================================
   Download Progress Simulation
   ============================================ */

function initDownloadProgress() {
    const downloadBtns = document.querySelectorAll('.btn-download');

    downloadBtns.forEach(btn => {
        btn.addEventListener('click', () => startDownload(btn));
    });
}

async function startDownload(btn) {
    const downloadItem = btn.closest('.download-item');
    const progressContainer = downloadItem?.querySelector('.download-progress');
    const progressFill = progressContainer?.querySelector('.progress-fill');
    const progressPercent = progressContainer?.querySelector('.progress-percent');
    const progressSpeed = progressContainer?.querySelector('.progress-speed');

    // Disable button
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    // Show progress
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }

    // Simulate download progress
    let progress = 0;
    const speeds = ['1.2 MB/s', '2.5 MB/s', '3.1 MB/s', '2.8 MB/s', '3.5 MB/s'];

    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);

            // Download complete
            setTimeout(() => {
                if (progressContainer) progressContainer.style.display = 'none';
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> دانلود شد';
                btn.classList.add('success');

                // Add XP
                addXP(50);

                if (typeof showToast === 'function') {
                    showToast('دانلود با موفقیت انجام شد!', 'success');
                }
            }, 500);
        }

        if (progressFill) progressFill.style.width = progress + '%';
        if (progressPercent) progressPercent.textContent = Math.round(progress) + '%';
        if (progressSpeed) progressSpeed.textContent = speeds[Math.floor(Math.random() * speeds.length)];
    }, 200);
}

/* ============================================
   Add XP Function
   ============================================ */

function addXP(amount) {
    const xpCurrent = document.querySelector('.xp-current');
    if (!xpCurrent) return;

    const currentXP = parseInt(xpCurrent.textContent.replace(/,/g, '')) || 0;
    const newXP = currentXP + amount;

    animateNumber(xpCurrent, newXP, 500);

    // Show floating +XP indicator
    showXPGain(amount);

    // Check for level up
    checkLevelUp(newXP);
}

function showXPGain(amount) {
    const indicator = document.createElement('div');
    indicator.classList.add('xp-gain-indicator');
    indicator.textContent = `+${amount} XP`;
    indicator.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--gradient-secondary);
        padding: 16px 32px;
        border-radius: 100px;
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        z-index: 9999;
        animation: xpPop 1s ease forwards;
    `;

    document.body.appendChild(indicator);

    setTimeout(() => indicator.remove(), 1000);
}

function checkLevelUp(currentXP) {
    const levelThresholds = [0, 500, 1500, 3000, 5000, 8000, 12000, 17000, 23000, 30000, 40000, 50000];
    const currentLevel = parseInt(document.querySelector('.xp-level')?.textContent) || 1;

    const newLevel = levelThresholds.findIndex((threshold, i) => {
        const nextThreshold = levelThresholds[i + 1] || Infinity;
        return currentXP >= threshold && currentXP < nextThreshold;
    }) + 1;

    if (newLevel > currentLevel) {
        showLevelUp(newLevel);
    }
}

function showLevelUp(newLevel) {
    const modal = document.createElement('div');
    modal.classList.add('level-up-modal');
    modal.innerHTML = `
        <div class="level-up-content glass">
            <div class="level-up-icon">🎉</div>
            <h2>سطح جدید!</h2>
            <div class="new-level">سطح ${newLevel}</div>
            <p>تبریک! شما به سطح ${newLevel} ارتقا یافتید</p>
            <button class="btn btn-primary" onclick="this.closest('.level-up-modal').remove()">
                عالی!
            </button>
        </div>
    `;
    modal.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    document.body.appendChild(modal);

    if (typeof createConfetti === 'function') {
        createConfetti(200);
    }
}

/* ============================================
   Activity Feed
   ============================================ */

function initActivityFeed() {
    const activityItems = document.querySelectorAll('.activity-item');

    activityItems.forEach((item, index) => {
        // Staggered animation
        item.style.opacity = '0';
        item.style.transform = 'translateX(20px)';

        setTimeout(() => {
            item.style.transition = 'all 0.4s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 200 + index * 150);
    });
}

// Add new activity to feed
function addActivity(title, description) {
    const timeline = document.querySelector('.activity-timeline');
    if (!timeline) return;

    const item = document.createElement('div');
    item.classList.add('activity-item');
    item.innerHTML = `
        <div class="activity-dot"></div>
        <div class="activity-content">
            <h4>${title}</h4>
            <p>${description}</p>
            <span class="activity-time">همین الان</span>
        </div>
    `;

    item.style.opacity = '0';
    item.style.transform = 'translateX(20px)';

    timeline.insertBefore(item, timeline.firstChild);

    setTimeout(() => {
        item.style.transition = 'all 0.4s ease';
        item.style.opacity = '1';
        item.style.transform = 'translateX(0)';
    }, 100);
}

/* ============================================
   Stats Counter Animation
   ============================================ */

function initStatsCounter() {
    const statsNumbers = document.querySelectorAll('.stats-info h3');

    statsNumbers.forEach(stat => {
        const target = parseInt(stat.getAttribute('data-target')) || parseInt(stat.textContent) || 0;
        stat.textContent = '0';

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateNumber(stat, target, 2000);
                    observer.unobserve(stat);
                }
            });
        }, { threshold: 0.5 });

        observer.observe(stat);
    });
}

/* ============================================
   Quick Search
   ============================================ */

function initQuickSearch() {
    const searchInput = document.querySelector('.search-box input');
    if (!searchInput) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            performSearch(e.target.value);
        }, 300);
    });

    // Keyboard shortcut (Ctrl + K)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

function performSearch(query) {
    if (query.length < 2) return;

    // Simulate search results
    console.log('Searching for:', query);

    // In real implementation, this would search through:
    // - Licenses
    // - Downloads
    // - Help articles
    // - Settings
}

/* ============================================
   Mobile Menu
   ============================================ */

function initMobileMenu() {
    const menuBtn = document.createElement('button');
    menuBtn.classList.add('mobile-sidebar-toggle');
    menuBtn.innerHTML = '<i class="fas fa-bars"></i>';
    menuBtn.style.cssText = `
        display: none;
        position: fixed;
        top: 20px;
        right: 20px;
        width: 48px;
        height: 48px;
        background: var(--gradient-primary);
        border: none;
        border-radius: var(--radius-md);
        color: white;
        font-size: 1.2rem;
        cursor: pointer;
        z-index: 1001;
    `;

    document.body.appendChild(menuBtn);

    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    function openSidebar() {
        sidebar?.classList.add('mobile-open');
        overlay?.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar?.classList.remove('mobile-open');
        overlay?.classList.remove('active');
        document.body.style.overflow = '';
    }

    menuBtn.addEventListener('click', () => {
        if (sidebar?.classList.contains('mobile-open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    // Close sidebar when clicking overlay
    overlay?.addEventListener('click', closeSidebar);

    // Close sidebar when clicking nav links
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 1024) {
                closeSidebar();
            }
        });
    });

    // Show on mobile
    if (window.innerWidth <= 1024) {
        menuBtn.style.display = 'flex';
        menuBtn.style.alignItems = 'center';
        menuBtn.style.justifyContent = 'center';
    }

    window.addEventListener('resize', () => {
        if (window.innerWidth <= 1024) {
            menuBtn.style.display = 'flex';
            menuBtn.style.alignItems = 'center';
            menuBtn.style.justifyContent = 'center';
        } else {
            menuBtn.style.display = 'none';
            closeSidebar();
        }
    });
}

/* ============================================
   License Management
   ============================================ */

function copyLicenseKey(key) {
    if (typeof OdooMaster?.copyToClipboard === 'function') {
        OdooMaster.copyToClipboard(key);
    } else {
        navigator.clipboard.writeText(key).then(() => {
            if (typeof showToast === 'function') {
                showToast('کلید لایسنس کپی شد!', 'success');
            }
        });
    }
}

function renewLicense(licenseId) {
    if (typeof showToast === 'function') {
        showToast('در حال انتقال به صفحه پرداخت...', 'info');
    }

    // Redirect to payment
    setTimeout(() => {
        window.location.href = `payment.html?renew=${licenseId}`;
    }, 1000);
}

/* ============================================
   Logout Functionality
   ============================================ */

function logout() {
    const doClientLogout = () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        sessionStorage.clear();

        if (typeof showToast === 'function') {
            showToast('خروج موفقیت a0آمیز', 'success');
        }

        setTimeout(() => {
            window.location.href = 'login.html';
        }, 400);
    };

    // Try server-side logout if API client is available; fall back to client-only
    if (typeof API !== 'undefined' && API && typeof API.logout === 'function') {
        API.logout().catch(() => {}).finally(doClientLogout);
        return;
    }

    doClientLogout();
}

// Logout button handler (current markup uses .logout-btn)
document.querySelector('.logout-btn')?.addEventListener('click', logout);

/* ============================================
   CSS Injection for Dynamic Styles
   ============================================ */

const dashboardStyles = document.createElement('style');
dashboardStyles.textContent = `
    @keyframes xpPop {
        0% { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
        50% { opacity: 1; transform: translate(-50%, -50%) scale(1.2); }
        100% { opacity: 0; transform: translate(-50%, -100%) scale(1); }
    }

    .achievement-tooltip {
        position: fixed;
        background: var(--dark-light);
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-md);
        padding: 12px 16px;
        z-index: 1000;
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 0.85rem;
        animation: fadeIn 0.2s ease;
    }

    .achievement-tooltip .xp {
        color: var(--secondary);
        font-weight: 600;
    }

    .level-up-content {
        text-align: center;
        padding: 48px;
        border-radius: var(--radius-xl);
        animation: scaleIn 0.5s ease;
    }

    .level-up-icon {
        font-size: 4rem;
        margin-bottom: 16px;
    }

    .new-level {
        font-size: 3rem;
        font-weight: 800;
        color: var(--secondary);
        margin: 16px 0;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes scaleIn {
        from { opacity: 0; transform: scale(0.8); }
        to { opacity: 1; transform: scale(1); }
    }
`;
document.head.appendChild(dashboardStyles);

/* ============================================
   Admin Access Check
   ============================================ */

async function checkAdminAccess() {
    try {
        // Check if API is available
        if (!window.API || typeof window.API.getMe !== 'function') {
            return;
        }

        // Get current user info
        const response = await window.API.getMe();
        
        // Check if user is admin
        if (response && response.user && response.user.is_admin) {
            // Show admin section
            const adminSection = document.getElementById('adminNavSection');
            if (adminSection) {
                adminSection.style.display = 'block';
            }

            initEmbeddedAdminPanel();
        }
    } catch (error) {
        console.log('Could not check admin access:', error);
    }
}

function initEmbeddedAdminPanel() {
    const adminCard = document.getElementById('admin');
    const adminLink = document.getElementById('adminNavLink');
    const closeBtn = document.getElementById('closeAdminPanel');

    if (!adminCard || !adminLink) return;

    const openAdmin = () => {
        adminCard.style.display = 'block';
        try {
            history.replaceState(null, '', '#admin');
        } catch (_) {}
        adminCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    const closeAdmin = (e) => {
        if (e) e.preventDefault();
        adminCard.style.display = 'none';
        try {
            if (location.hash === '#admin') history.replaceState(null, '', ' ');
        } catch (_) {}
    };

    adminLink.addEventListener('click', (e) => {
        e.preventDefault();
        openAdmin();
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', closeAdmin);
    }

    // Open automatically if URL hash requests it
    if (location.hash === '#admin') {
        openAdmin();
    }
}

/* ============================================
   Export Functions
   ============================================ */

window.DashboardFunctions = {
    addXP,
    addActivity,
    unlockAchievement,
    copyLicenseKey,
    renewLicense,
    logout
};

console.log('📊 Dashboard loaded successfully!');
