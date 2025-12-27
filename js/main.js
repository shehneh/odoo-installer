/* ============================================
   OdooMaster - Main JavaScript
   Global functionality & interactions
   ============================================ */

// Wait for DOM
document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initParticles();
    initNavbar();
    initSmoothScroll();
    initScrollAnimations();
    initCounterAnimations();
    initCursorGlow();
    initTiltEffect();
    initRippleEffect();
});

/* ============================================
   Theme Toggle (Dark/Light Mode)
   ============================================ */

function initThemeToggle() {
    const themeToggles = Array.from(document.querySelectorAll('.theme-toggle'));
    if (themeToggles.length === 0) return;

    const setIcons = (isLight) => {
        const icon = isLight ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        themeToggles.forEach(btn => {
            btn.innerHTML = icon;
            btn.setAttribute('aria-pressed', isLight ? 'true' : 'false');
        });
    };

    // بررسی تم ذخیره شده
    const savedTheme = localStorage.getItem('theme');
    const isLightSaved = savedTheme === 'light';
    if (isLightSaved) {
        document.body.classList.add('light-theme');
    }
    setIcons(document.body.classList.contains('light-theme'));

    themeToggles.forEach(btn => {
        btn.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');

            const isLight = document.body.classList.contains('light-theme');
            setIcons(isLight);
            localStorage.setItem('theme', isLight ? 'light' : 'dark');

            // انیمیشن
            btn.style.transform = 'rotate(360deg) scale(1.2)';
            setTimeout(() => {
                btn.style.transform = '';
            }, 300);
        });
    });
}

/* ============================================
   Particles.js Background
   ============================================ */

function initParticles() {
    const particlesEl = document.getElementById('particles-js');
    if (!particlesEl || typeof particlesJS === 'undefined') return;

    particlesJS('particles-js', {
        particles: {
            number: {
                value: 80,
                density: {
                    enable: true,
                    value_area: 800
                }
            },
            color: {
                value: ['#714B67', '#00A09D', '#F06050']
            },
            shape: {
                type: 'circle'
            },
            opacity: {
                value: 0.5,
                random: true,
                anim: {
                    enable: true,
                    speed: 1,
                    opacity_min: 0.1,
                    sync: false
                }
            },
            size: {
                value: 3,
                random: true,
                anim: {
                    enable: true,
                    speed: 2,
                    size_min: 0.1,
                    sync: false
                }
            },
            line_linked: {
                enable: true,
                distance: 150,
                color: '#714B67',
                opacity: 0.2,
                width: 1
            },
            move: {
                enable: true,
                speed: 1,
                direction: 'none',
                random: true,
                straight: false,
                out_mode: 'out',
                bounce: false,
                attract: {
                    enable: false,
                    rotateX: 600,
                    rotateY: 1200
                }
            }
        },
        interactivity: {
            detect_on: 'canvas',
            events: {
                onhover: {
                    enable: true,
                    mode: 'grab'
                },
                onclick: {
                    enable: true,
                    mode: 'push'
                },
                resize: true
            },
            modes: {
                grab: {
                    distance: 140,
                    line_linked: {
                        opacity: 0.5
                    }
                },
                push: {
                    particles_nb: 4
                }
            }
        },
        retina_detect: true
    });
}

/* ============================================
   Navbar Scroll Effect
   ============================================ */

function initNavbar() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;

    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }

        // Hide/show on scroll direction
        if (currentScroll > lastScroll && currentScroll > 200) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }

        lastScroll = currentScroll;
    });

    // Mobile menu toggle
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    const navActions = document.querySelector('.nav-actions');

    const ensureMobileActions = () => {
        if (!navLinks || !navActions) return;

        let mobileActions = navLinks.querySelector('.mobile-menu-actions');
        if (mobileActions) return;

        mobileActions = document.createElement('div');
        mobileActions.className = 'mobile-menu-actions';

        // Clone theme toggle (works because initThemeToggle binds by class)
        const themeBtn = navActions.querySelector('.theme-toggle');
        if (themeBtn) {
            const themeClone = themeBtn.cloneNode(true);
            themeClone.removeAttribute('id');
            mobileActions.appendChild(themeClone);
        }

        // Clone auth buttons
        const authButtons = navActions.querySelectorAll('a.btn');
        authButtons.forEach(a => {
            mobileActions.appendChild(a.cloneNode(true));
        });

        navLinks.appendChild(mobileActions);
    };

    const closeMobileMenu = () => {
        if (!navLinks || !mobileMenuBtn) return;
        navLinks.classList.remove('mobile-open');
        mobileMenuBtn.classList.remove('active');
    };

    if (mobileMenuBtn && navLinks) {
        ensureMobileActions();

        mobileMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            navLinks.classList.toggle('mobile-open');
            mobileMenuBtn.classList.toggle('active');

            // اگر تازه ساختیم، آیکون تم را sync کنیم
            initThemeToggle();
        });

        // Close when clicking a link
        navLinks.addEventListener('click', (e) => {
            const target = e.target;
            if (target && target.closest('a')) {
                closeMobileMenu();
            }
        });

        // Close when clicking outside
        document.addEventListener('click', (e) => {
            if (!navLinks.classList.contains('mobile-open')) return;
            if (e.target.closest('.navbar')) return;
            closeMobileMenu();
        });

        // Close on resize to desktop
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) closeMobileMenu();
        });
    }
}

/* ============================================
   Smooth Scroll for Anchor Links
   ============================================ */

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                const navHeight = document.querySelector('.navbar')?.offsetHeight || 80;
                const targetPosition = targetElement.offsetTop - navHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/* ============================================
   Scroll Reveal Animations
   ============================================ */

function initScrollAnimations() {
    const revealElements = document.querySelectorAll('.reveal, .feature-card, .pricing-card, .stats-card');

    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    revealElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s ease';
        observer.observe(el);
    });
}

/* ============================================
   Counter Animations
   ============================================ */

function initCounterAnimations() {
    const counters = document.querySelectorAll('.count-up');
    
    const observerOptions = {
        threshold: 0.5
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    counters.forEach(counter => observer.observe(counter));
}

function animateCounter(element) {
    const target = parseInt(element.getAttribute('data-target')) || 0;
    const duration = 2000;
    const increment = target / (duration / 16);
    let current = 0;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = formatNumber(target);
            clearInterval(timer);
        } else {
            element.textContent = formatNumber(Math.floor(current));
        }
    }, 16);
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString('fa-IR');
}

/* ============================================
   Cursor Glow Effect
   ============================================ */

function initCursorGlow() {
    const glow = document.querySelector('.cursor-glow');
    if (!glow) return;

    document.addEventListener('mousemove', (e) => {
        glow.style.left = e.clientX + 'px';
        glow.style.top = e.clientY + 'px';
    });
}

/* ============================================
   Card Tilt Effect
   ============================================ */

function initTiltEffect() {
    const cards = document.querySelectorAll('.tilt-effect, .feature-card, .pricing-card');

    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
        });
    });
}

/* ============================================
   Ripple Effect
   ============================================ */

function initRippleEffect() {
    const buttons = document.querySelectorAll('.btn, .ripple');

    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            ripple.classList.add('ripple-effect');

            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';

            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });
}

/* ============================================
   Confetti Effect
   ============================================ */

function createConfetti(count = 100) {
    const container = document.createElement('div');
    container.classList.add('confetti-container');
    document.body.appendChild(container);

    const colors = ['#714B67', '#00A09D', '#F06050', '#f1c40f', '#9b59b6', '#3498db'];

    for (let i = 0; i < count; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.classList.add('confetti');
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
            confetti.style.transform = `rotate(${Math.random() * 360}deg)`;
            container.appendChild(confetti);

            setTimeout(() => confetti.remove(), 3000);
        }, i * 20);
    }

    setTimeout(() => container.remove(), 5000);
}

/* ============================================
   Toast Notifications
   ============================================ */

function showToast(message, type = 'info', duration = 4000) {
    const container = document.querySelector('.toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.classList.add('toast', `toast-${type}`, 'notification-enter');

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
        <button class="toast-close"><i class="fas fa-times"></i></button>
    `;

    container.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => removeToast(toast));

    setTimeout(() => removeToast(toast), duration);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.classList.add('toast-container');
    document.body.appendChild(container);
    return container;
}

function removeToast(toast) {
    toast.classList.remove('notification-enter');
    toast.classList.add('notification-exit');
    setTimeout(() => toast.remove(), 300);
}

/* ============================================
   Loading Overlay
   ============================================ */

function showLoading(message = 'در حال بارگذاری...') {
    const overlay = document.createElement('div');
    overlay.classList.add('loading-overlay');
    overlay.innerHTML = `
        <div class="loading-content glass">
            <div class="loader"></div>
            <p>${message}</p>
        </div>
    `;
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.add('fade-out');
        setTimeout(() => {
            overlay.remove();
            document.body.style.overflow = '';
        }, 300);
    }
}

/* ============================================
   Modal System
   ============================================ */

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal(modalId);
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function escapeHandler(e) {
        if (e.key === 'Escape') {
            closeModal(modalId);
            document.removeEventListener('keydown', escapeHandler);
        }
    });
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('active');
    document.body.style.overflow = '';
}

/* ============================================
   Utility Functions
   ============================================ */

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Format date in Persian
function formatDate(date) {
    return new Intl.DateTimeFormat('fa-IR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(new Date(date));
}

// Format price in Persian
function formatPrice(price) {
    return new Intl.NumberFormat('fa-IR').format(price) + ' تومان';
}

// Copy to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('کپی شد!', 'success');
    } catch (err) {
        showToast('خطا در کپی کردن', 'error');
    }
}

/* ============================================
   Sparkle Effect on Click
   ============================================ */

document.addEventListener('click', (e) => {
    if (e.target.closest('.sparkle-on-click')) {
        createSparkles(e.clientX, e.clientY, 10);
    }
});

function createSparkles(x, y, count = 10) {
    for (let i = 0; i < count; i++) {
        const sparkle = document.createElement('div');
        sparkle.classList.add('sparkle');
        sparkle.style.left = x + (Math.random() - 0.5) * 100 + 'px';
        sparkle.style.top = y + (Math.random() - 0.5) * 100 + 'px';
        document.body.appendChild(sparkle);
        setTimeout(() => sparkle.remove(), 1000);
    }
}

/* ============================================
   Export Functions for Global Use
   ============================================ */

window.OdooMaster = {
    showToast,
    showLoading,
    hideLoading,
    openModal,
    closeModal,
    createConfetti,
    copyToClipboard,
    formatDate,
    formatPrice
};

console.log('🚀 OdooMaster loaded successfully!');
