/**
 * Payment page logic - Enhanced version
 * - Requires login
 * - Gets hardware ID from URL (must be from installer)
 * - Binds license to hardware
 * - Downloads license file immediately after purchase
 * - Strict validation of all required fields
 */

let selectedPlan = null;
let hardwareId = '';
let plans = [];
let isValidHardwareId = false; // Track if hardware ID is from installer

document.addEventListener('DOMContentLoaded', () => {
    init();
});

function showError(message) {
    const el = document.getElementById('errorAlert');
    const msgEl = document.getElementById('errorMessage');
    if (el && msgEl) {
        msgEl.textContent = message;
        el.style.display = 'block';
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function hideError() {
    const el = document.getElementById('errorAlert');
    if (el) el.style.display = 'none';
}

function showSuccess(message) {
    const el = document.getElementById('successAlert');
    const msgEl = document.getElementById('successMessage');
    if (el && msgEl) {
        msgEl.textContent = message;
        el.style.display = 'block';
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Show existing license message with download button
function showExistingLicenseMessage(licenseKey, hwid) {
    const el = document.getElementById('errorAlert');
    const msgEl = document.getElementById('errorMessage');
    if (el && msgEl) {
        msgEl.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 12px; align-items: flex-start;">
                <span>شما در حال حاضر یک لایسنس فعال برای این دستگاه دارید. کلید: <strong>${licenseKey}</strong></span>
                <button onclick="downloadExistingLicense('${licenseKey}', '${hwid}')" 
                        class="btn btn-success btn-sm" 
                        style="display: inline-flex; align-items: center; gap: 6px;">
                    <i class="fas fa-download"></i>
                    دریافت فایل لایسنس
                </button>
            </div>
        `;
        el.style.display = 'block';
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Download license file for existing license
async function downloadExistingLicense(licenseKey, hwid) {
    try {
        const res = await API.request(`/licenses/${licenseKey}/file`, {
            method: 'POST',
            body: JSON.stringify({ hardware_id: hwid || '' })
        });
        
        if (res && res.license_file) {
            downloadLicenseFile(res.license_file, licenseKey);
            UI?.showToast?.('فایل لایسنس با موفقیت دانلود شد', 'success');
        } else {
            throw new Error(res?.error || 'خطا در دریافت فایل لایسنس');
        }
    } catch (e) {
        console.error('Error downloading existing license:', e);
        UI?.showToast?.(e?.message || 'خطا در دریافت فایل لایسنس', 'error');
    }
}

function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

// Validate hardware ID format (must be 16 hex characters from real installer)
function isValidHardwareIdFormat(hwid) {
    if (!hwid || typeof hwid !== 'string') return false;
    // Must be exactly 16 hex characters (real hardware ID from installer)
    return /^[a-f0-9]{16}$/i.test(hwid.trim());
}

async function init() {
    // Enforce login
    if (!API.isLoggedIn()) {
        localStorage.setItem('after_login_redirect', 'payment.html' + window.location.search);
        window.location.href = 'login.html?redirect=payment.html';
        return;
    }

    // Get hardware ID ONLY from URL (passed from installer) - no fallback generation
    hardwareId = (getQueryParam('hwid') || getQueryParam('hardware_id') || '').trim();
    
    // Also check localStorage (set by installer UI)
    if (!hardwareId) {
        hardwareId = (localStorage.getItem('installer_hardware_id') || '').trim();
    }
    
    // Validate hardware ID
    isValidHardwareId = isValidHardwareIdFormat(hardwareId);
    
    // Display hardware ID
    const hwEl = document.getElementById('hardwareId');
    const hwInput = document.getElementById('hardwareIdInput');
    const validateBtn = document.getElementById('validateHwidBtn');
    
    if (isValidHardwareId) {
        if (hwInput) hwInput.value = hardwareId;
    }
    
    // Setup validate button for manual HWID entry
    if (validateBtn) {
        validateBtn.addEventListener('click', () => {
            const manualHwid = hwInput?.value?.trim() || '';
            if (isValidHardwareIdFormat(manualHwid)) {
                hardwareId = manualHwid;
                isValidHardwareId = true;
                hideError();
                validateBtn.innerHTML = '<i class="fas fa-check"></i> <span>تایید شد</span>';
                validateBtn.style.background = 'var(--secondary)';
                validateBtn.style.color = 'white';
                hwInput.style.borderColor = 'var(--secondary)';
                
                // Enable pay button if plan is selected
                updatePayButtonState();
            } else {
                showError('شناسه سخت‌افزاری نامعتبر است. باید 16 کاراکتر هگزادسیمال (0-9, a-f) باشد.');
                hwInput.style.borderColor = '#ef4444';
            }
        });
    }
    
    // Also validate on input change
    if (hwInput) {
        hwInput.addEventListener('input', () => {
            const val = hwInput.value.trim();
            if (isValidHardwareIdFormat(val)) {
                hwInput.style.borderColor = 'var(--secondary)';
            } else if (val.length > 0) {
                hwInput.style.borderColor = '#f59e0b';
            } else {
                hwInput.style.borderColor = '';
            }
        });
    }

    // Load user info to pre-fill customer details
    try {
        const me = await API.getMe();
        const user = me?.user || me;
        if (user) {
            const nameEl = document.getElementById('customerName');
            const emailEl = document.getElementById('customerEmail');
            const phoneEl = document.getElementById('customerPhone');
            
            if (nameEl && user.name) nameEl.value = user.name;
            if (emailEl && user.email) emailEl.value = user.email;
            if (phoneEl && user.phone) phoneEl.value = user.phone;
        }
    } catch (e) {
        console.warn('Could not load user info:', e);
    }

    // Load plans
    try {
        const res = await API.getPlans();
        plans = res.plans || [];
        renderPlans(plans);
    } catch (e) {
        showError(e?.message || 'خطا در دریافت پلن‌ها');
        return;
    }

    // Setup pay button
    const payBtn = document.getElementById('payBtn');
    if (payBtn) {
        payBtn.addEventListener('click', handlePurchase);
        // Keep button disabled until plan is selected AND hardware ID is valid
        updatePayButtonState();
    }
}

function updatePayButtonState() {
    const payBtn = document.getElementById('payBtn');
    if (!payBtn) return;
    
    const canPay = selectedPlan && isValidHardwareId;
    payBtn.disabled = !canPay;
    
    if (canPay) {
        payBtn.style.cursor = 'pointer';
        payBtn.style.opacity = '1';
    } else {
        payBtn.style.cursor = 'not-allowed';
        payBtn.style.opacity = '0.6';
    }
}

function renderPlans(plans) {
    const container = document.getElementById('plansGrid');
    if (!container) return;

    container.innerHTML = '';

    plans.forEach((p, index) => {
        const isPopular = index === 1; // Middle plan is popular
        
        const card = document.createElement('div');
        card.className = `plan-card${isPopular ? ' popular' : ''}`;
        card.dataset.planId = p.id;

        const price = Number(p.price || 0);
        const durationText = getPlanDurationText(p);

        const features = p.features || [];
        let featuresHtml = '';
        features.forEach(f => {
            featuresHtml += `<li><i class="fas fa-check"></i> ${f}</li>`;
        });

        card.innerHTML = `
            <div class="plan-name">${p.name || 'پلن'}</div>
            <div class="plan-price">${price.toLocaleString('fa-IR')} تومان</div>
            <div class="plan-duration">${durationText}</div>
            <ul class="plan-features">${featuresHtml}</ul>
        `;

        card.addEventListener('click', () => selectPlan(p, card));
        container.appendChild(card);
    });
}

function getPlanDurationInfo(plan) {
    const unit = (plan && plan.duration_unit) ? String(plan.duration_unit) : null;
    const rawValue = (plan && plan.duration_value != null)
        ? plan.duration_value
        : (plan ? plan.duration_days : null);
    const value = Number(rawValue);

    if (!Number.isFinite(value)) {
        return { unit: unit || 'days', value: null };
    }

    // Unlimited license: duration_value <= 0 (new model) OR legacy huge days
    if (value <= 0) {
        return { unit: unit || 'days', value: 0 };
    }

    // If unit is missing, assume legacy days
    if (!unit) {
        return { unit: 'days', value };
    }

    if (unit === 'hours' || unit === 'days') {
        return { unit, value };
    }

    // Unknown unit: fall back to days
    return { unit: 'days', value };
}

function getPlanDurationText(plan) {
    const info = getPlanDurationInfo(plan);
    if (info.value === 0) return 'نامحدود';
    if (info.value == null) return '—';

    if (info.unit === 'hours') {
        const h = Math.trunc(info.value);
        if (h === 1) return 'یک ساعته';
        return `${h} ساعته`;
    }

    const days = Math.trunc(info.value);
    if (days <= 1) return '۱ روزه';
    if (days <= 7) return 'یک هفته ای';
    if (days <= 30) return 'یک ماهه';
    if (days <= 90) return 'سه ماهه';
    if (days <= 180) return 'شش ماهه';
    if (days <= 365) return 'یکساله';
    return `${days} روزه`;
}

function selectPlan(plan, cardElement) {
    hideError();
    
    // Check if hardware ID is valid - show warning but allow selection
    const hwInput = document.getElementById('hardwareIdInput');
    if (!isValidHardwareId && hwInput) {
        const manualHwid = hwInput.value.trim();
        if (isValidHardwareIdFormat(manualHwid)) {
            hardwareId = manualHwid;
            isValidHardwareId = true;
        }
    }
    
    // Remove selection from all cards
    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
    
    // Select this card
    cardElement.classList.add('selected');
    selectedPlan = plan;

    // Update summary
    const summaryPlan = document.getElementById('summaryPlan');
    const summaryPrice = document.getElementById('summaryPrice');
    const payBtnText = document.getElementById('payBtnText');

    const price = Number(plan.price || 0);
    
    if (summaryPlan) summaryPlan.textContent = plan.name || 'پلن';
    if (summaryPrice) summaryPrice.textContent = price.toLocaleString('fa-IR') + ' تومان';
    if (payBtnText) payBtnText.textContent = `پرداخت ${price.toLocaleString('fa-IR')} تومان`;
    
    // Update pay button state
    updatePayButtonState();
}

async function handlePurchase() {
    hideError();
    
    // === STRICT VALIDATION ===
    
    // 1. Check hardware ID from real installer
    if (!isValidHardwareId) {
        showError('شناسه سخت‌افزاری معتبر نیست! برای خرید لایسنس باید از طریق نصب‌کننده OdooMaster وارد این صفحه شوید.');
        return;
    }

    // 2. Check plan selection
    if (!selectedPlan) {
        showError('لطفاً یک پلن انتخاب کنید');
        return;
    }

    // 3. Validate customer information
    const customerName = (document.getElementById('customerName')?.value || '').trim();
    const customerEmail = (document.getElementById('customerEmail')?.value || '').trim();
    const customerPhone = (document.getElementById('customerPhone')?.value || '').trim();

    // Name validation
    if (!customerName || customerName.length < 3) {
        showError('لطفاً نام و نام خانوادگی خود را وارد کنید (حداقل ۳ کاراکتر)');
        document.getElementById('customerName')?.focus();
        return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!customerEmail || !emailRegex.test(customerEmail)) {
        showError('لطفاً ایمیل معتبر وارد کنید');
        document.getElementById('customerEmail')?.focus();
        return;
    }

    // Phone validation (Iranian phone number)
    const phoneRegex = /^(0|\+98)?9\d{9}$/;
    const cleanPhone = customerPhone.replace(/[\s\-]/g, '');
    if (!cleanPhone || !phoneRegex.test(cleanPhone)) {
        showError('لطفاً شماره تلفن همراه معتبر وارد کنید (مثال: 09123456789)');
        document.getElementById('customerPhone')?.focus();
        return;
    }

    // === ALL VALIDATIONS PASSED ===

    const payBtn = document.getElementById('payBtn');
    const payBtnText = document.getElementById('payBtnText');
    
    if (payBtn) payBtn.disabled = true;
    if (payBtnText) payBtnText.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال پردازش...';

    try {
        const res = await API.purchasePlan(selectedPlan.id, {
            hardware_id: hardwareId,
            customer_name: customerName,
            customer_email: customerEmail,
            customer_phone: cleanPhone
        });

        if (res.success) {
            showSuccess('خرید با موفقیت انجام شد! در حال دانلود فایل لایسنس...');
            
            // Store license key
            if (res.license_key) {
                localStorage.setItem('lastLicenseKey', res.license_key);
            }

            // Download license file immediately if available
            if (res.license_file) {
                downloadLicenseFile(res.license_file, res.license_key);
            }

            // Redirect to licenses page after 2 seconds
            setTimeout(() => {
                window.location.href = 'licenses.html';
            }, 2500);
        } else {
            throw new Error(res.error || 'خطا در خرید');
        }
    } catch (e) {
        // Check if it's a duplicate license error
        const licenseKey = e?.existing_license_key || e?.payload?.existing_license_key;
        if (licenseKey) {
            showExistingLicenseMessage(licenseKey, hardwareId);
        } else {
            showError(e?.message || e?.error || 'خطا در انجام خرید');
        }
        
        if (payBtn) payBtn.disabled = false;
        if (payBtnText) {
            const price = Number(selectedPlan?.price || 0);
            payBtnText.textContent = `پرداخت ${price.toLocaleString('fa-IR')} تومان`;
        }
    }
}

function downloadLicenseFile(licenseBundle, licenseKey) {
    try {
        const content = JSON.stringify(licenseBundle, null, 2);
        const blob = new Blob([content], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'license.oml';  // Always use standard name for installer compatibility
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
        
        UI?.showToast?.('فایل لایسنس دانلود شد', 'success');
    } catch (e) {
        console.error('Error downloading license file:', e);
    }
}

// Extend API object for enhanced purchase
if (typeof API !== 'undefined') {
    API.purchasePlan = async function(planId, options = {}) {
        const body = {
            plan_id: planId,
            hardware_id: options.hardware_id || '',
            customer_name: options.customer_name || '',
            customer_email: options.customer_email || '',
            customer_phone: options.customer_phone || ''
        };
        
        const response = await this.request('/purchase', {
            method: 'POST',
            body: JSON.stringify(body)
        });
        
        return response;
    };
}
