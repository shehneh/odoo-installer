/* ============================================
   OdooMaster - Auth JavaScript
   Real Login/Register using website API client (js/api.js)
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initPasswordToggle();
    initFormValidation();
    bindLoginForm();
    initRegisterFlow();
    applyAdminLoginUiIfNeeded();
});

function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

function sanitizeRedirect(target) {
    if (!target) return null;
    const t = String(target).trim();
    if (!t) return null;
    if (t.includes('://') || t.startsWith('//')) return null;
    return t;
}

function getRedirectTarget() {
    const queryRedirect = sanitizeRedirect(getQueryParam('redirect'));
    if (queryRedirect) return queryRedirect;
    const stored = sanitizeRedirect(localStorage.getItem('after_login_redirect'));
    if (stored) return stored;
    return 'dashboard.html';
}

function redirectAfterAuth() {
    const target = getRedirectTarget();
    localStorage.removeItem('after_login_redirect');
    window.location.href = target;
}

function isAdminLoginMode() {
    const redirect = (getRedirectTarget() || '').toString().trim().toLowerCase();
    if (redirect === 'admin.html') return true;

    const qp = (getQueryParam('admin') || '').toString().trim().toLowerCase();
    return qp === '1' || qp === 'true';
}

function applyAdminLoginUiIfNeeded() {
    if (!isAdminLoginMode()) return;

    const headerP = document.querySelector('.auth-header p');
    if (headerP) headerP.textContent = 'وارد پنل مدیریت شوید';

    const emailLabel = document.querySelector('label.form-label');
    if (emailLabel) emailLabel.textContent = 'نام کاربری مدیر';

    const emailInput = document.getElementById('email');
    if (emailInput) {
        emailInput.placeholder = 'نام کاربری مدیر';
        emailInput.autocomplete = 'username';
    }
}

/* ============================================
   Password Toggle Visibility
   ============================================ */

function initPasswordToggle() {
    const toggleBtns = document.querySelectorAll('.password-toggle, .toggle-pass');

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            // Support both .input-wrapper and .input-wrap class names
            const wrapper = btn.closest('.input-wrapper') || btn.closest('.input-wrap');
            const input = wrapper?.querySelector('input');
            const icon = btn.querySelector('i');
            
            if (!input || !icon) return;

            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
}

/* ============================================
   Form Validation
   ============================================ */

function initFormValidation() {
    const forms = document.querySelectorAll('.auth-form');

    forms.forEach(form => {
        const inputs = form.querySelectorAll('.form-control');

        inputs.forEach(input => {
            // Real-time validation on blur
            input.addEventListener('blur', () => validateInput(input));

            // Remove error on focus
            input.addEventListener('focus', () => {
                input.classList.remove('error');
                const errorMsg = input.closest('.form-group')?.querySelector('.error-message');
                if (errorMsg) errorMsg.remove();
            });
        });

        // Form submit validation is handled per-form (login/register).
    });
}

function validateInput(input) {
    const value = input.value.trim();
    const type = input.type;
    const name = input.name;
    let isValid = true;
    let errorMessage = '';

    // Required check
    if (input.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'این فیلد الزامی است';
    }

    // Email validation
    else if (type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            errorMessage = 'ایمیل نامعتبر است';
        }
    }

    // Password validation
    else if (name === 'password' && value) {
        if (value.length < 8) {
            isValid = false;
            errorMessage = 'رمز عبور باید حداقل ۸ کاراکتر باشد';
        }
    }

    // Phone validation (Persian format)
    else if (name === 'phone' && value) {
        const phoneRegex = /^09\d{9}$/;
        if (!phoneRegex.test(value.replace(/\s/g, ''))) {
            isValid = false;
            errorMessage = 'شماره موبایل نامعتبر است';
        }
    }

    // Update UI
    if (!isValid) {
        input.classList.add('error');
        showInputError(input, errorMessage);
    } else {
        input.classList.remove('error');
        input.classList.add('success');
        const errorMsg = input.closest('.form-group')?.querySelector('.error-message');
        if (errorMsg) errorMsg.remove();
    }

    return isValid;
}

function showInputError(input, message) {
    const formGroup = input.closest('.form-group');
    let errorElement = formGroup?.querySelector('.error-message');

    if (!errorElement) {
        errorElement = document.createElement('span');
        errorElement.classList.add('error-message');
        errorElement.style.cssText = 'color: var(--accent); font-size: 0.85rem; margin-top: 8px; display: block;';
        formGroup?.appendChild(errorElement);
    }

    errorElement.textContent = message;
    input.classList.add('error-shake');
    setTimeout(() => input.classList.remove('error-shake'), 400);
}

/* ============================================
   Login
   ============================================ */

function bindLoginForm() {
    const form = document.getElementById('loginForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const emailOrPhone = (document.getElementById('email')?.value || '').trim();
        const password = document.getElementById('password')?.value || '';

        if (!emailOrPhone || !password) {
            UI?.showToast?.(isAdminLoginMode() ? 'نام کاربری و رمز عبور الزامی است' : 'ایمیل/موبایل و رمز عبور الزامی است', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        const original = submitBtn?.innerHTML;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');
        }

        try {
            const res = isAdminLoginMode() ? await API.adminLogin(emailOrPhone, password) : await API.login(emailOrPhone, password);
            if (res?.user) {
                localStorage.setItem('user', JSON.stringify(res.user));
            }
            UI?.showToast?.('ورود موفقیت‌آمیز', 'success');
            setTimeout(redirectAfterAuth, 400);
        } catch (err) {
            UI?.showToast?.(err?.message || 'ورود ناموفق بود', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.classList.remove('loading');
                if (original) submitBtn.innerHTML = original;
            }
        }
    });
}

/* ============================================
   Register (3-step UI in register.html)
   ============================================ */

let currentStep = 1;

function initRegisterFlow() {
    const form = document.getElementById('registerForm');
    if (!form) return;

    showStep(1);

    // Bind resend button if present
    const resendBtn = document.getElementById('resendBtn');
    resendBtn?.addEventListener('click', () => {
        resendBtn.disabled = true;
        UI?.showToast?.('کد تایید مجدداً ارسال شد', 'success');
        startRegisterResendTimer(60);
    });

    // OTP inputs behavior
    const otpInputs = Array.from(document.querySelectorAll('.otp-input'));
    otpInputs.forEach((input, idx) => {
        input.addEventListener('input', () => {
            input.value = input.value.replace(/\D/g, '').slice(0, 1);
            if (input.value && idx < otpInputs.length - 1) {
                otpInputs[idx + 1].focus();
            }
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !input.value && idx > 0) {
                otpInputs[idx - 1].focus();
            }
        });
    });
}

function showStep(step) {
    currentStep = step;

    // Toggle form steps
    document.querySelectorAll('.form-step').forEach((el) => {
        el.classList.remove('active');
    });
    const active = document.getElementById(`step${step}`);
    active?.classList.add('active');

    // Toggle progress steps
    const steps = Array.from(document.querySelectorAll('.register-steps .step'));
    steps.forEach((s, idx) => {
        s.classList.remove('active');
        if (idx + 1 === step) s.classList.add('active');
    });
}

async function nextStep(step) {
    // Used by inline onclick in register.html
    if (step === 2) {
        const firstName = (document.getElementById('firstName')?.value || '').trim();
        const lastName = (document.getElementById('lastName')?.value || '').trim();
        const phone = (document.getElementById('mobile')?.value || '').trim();
        const email = (document.getElementById('regEmail')?.value || '').trim();
        const password = document.getElementById('regPassword')?.value || '';

        if (!firstName || !lastName || !phone || !email || !password) {
            UI?.showToast?.('لطفاً همه فیلدهای الزامی را تکمیل کنید', 'error');
            return;
        }

        try {
            const name = `${firstName} ${lastName}`.trim();
            const res = await API.register({ name, email, phone, password });
            if (res?.user) {
                localStorage.setItem('user', JSON.stringify(res.user));
            }
            const displayMobile = document.getElementById('displayMobile');
            if (displayMobile) displayMobile.textContent = phone;
            UI?.showToast?.('ثبت‌نام انجام شد. کد تایید را وارد کنید.', 'success');
            showStep(2);
            startRegisterResendTimer(60);
            focusFirstRegisterOTP();
        } catch (err) {
            UI?.showToast?.(err?.message || 'ثبت‌نام ناموفق بود', 'error');
        }
        return;
    }

    if (step === 3) {
        const otp = getRegisterOTP();
        if (otp.length !== 6) {
            UI?.showToast?.('کد تایید نامعتبر است', 'error');
            return;
        }
        UI?.showToast?.('ثبت‌نام کامل شد! در حال انتقال...', 'success');
        showStep(3);
        // Redirect after showing success
        setTimeout(() => {
            redirectAfterAuth();
        }, 1500);
        return;
    }

    showStep(step);
}

function prevStep(step) {
    // Used by inline onclick in register.html
    showStep(step);
}

function getRegisterOTP() {
    return Array.from(document.querySelectorAll('.otp-input')).map(i => (i.value || '').trim()).join('');
}

function focusFirstRegisterOTP() {
    const first = document.querySelector('.otp-input');
    first?.focus();
}

let registerResendInterval;
function startRegisterResendTimer(seconds) {
    const countdown = document.getElementById('countdown');
    const resendBtn = document.getElementById('resendBtn');
    if (!countdown || !resendBtn) return;

    let remaining = seconds;
    resendBtn.disabled = true;
    countdown.textContent = String(remaining);

    if (registerResendInterval) clearInterval(registerResendInterval);
    registerResendInterval = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
            clearInterval(registerResendInterval);
            resendBtn.disabled = false;
            countdown.textContent = '0';
            return;
        }
        countdown.textContent = String(remaining);
    }, 1000);
}

/* ============================================
   Remember Me Functionality
   ============================================ */

function initRememberMe() {
    const rememberCheckbox = document.getElementById('remember');
    const emailInput = document.getElementById('email');

    if (!rememberCheckbox || !emailInput) return;

    // Load saved email
    const savedEmail = localStorage.getItem('rememberedEmail');
    if (savedEmail) {
        emailInput.value = savedEmail;
        rememberCheckbox.checked = true;
    }

    // Save email on form submit
    document.querySelector('.auth-form')?.addEventListener('submit', () => {
        if (rememberCheckbox.checked) {
            localStorage.setItem('rememberedEmail', emailInput.value);
        } else {
            localStorage.removeItem('rememberedEmail');
        }
    });
}

// Initialize remember me
document.addEventListener('DOMContentLoaded', initRememberMe);

/* ============================================
   Export Functions
   ============================================ */

window.AuthFunctions = {
    nextStep,
    prevStep,
    validateInput
};

// Backward compatibility for inline usage
window.nextStep = nextStep;
window.prevStep = prevStep;
