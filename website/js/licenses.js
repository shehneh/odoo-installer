/**
 * Licenses page logic
 */

let cachedLicenses = [];

document.addEventListener('DOMContentLoaded', () => {
    init();
    
    // Re-render when language changes
    document.addEventListener('languageChange', () => {
        if (cachedLicenses.length > 0) {
            renderLicenses(cachedLicenses);
        }
    });
});

async function init() {
    if (!API.isLoggedIn()) {
        localStorage.setItem('after_login_redirect', window.location.pathname.split('/').pop());
        window.location.href = 'login.html?redirect=licenses.html';
        return;
    }

    let res;
    const t = (key, fallback) => window.I18N ? I18N.t(key, fallback) : fallback;
    try {
        res = await API.getMe();
    } catch (e) {
        UI?.showToast?.(e?.message || t('error.network', 'Error loading user data'), 'error');
        return;
    }

    cachedLicenses = res.licenses || [];
    renderLicenses(cachedLicenses);
}

function renderLicenses(licenses) {
    const list = document.getElementById('licensesList');
    if (!list) return;
    
    // Get translations
    const t = (key, fallback) => window.I18N ? I18N.t(key, fallback) : fallback;

    if (!licenses.length) {
        list.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-key" style="font-size: 3rem; color: var(--gray-light); margin-bottom: 16px;"></i>
                <div style="color: var(--gray-light); margin-bottom: 20px;">${t('licenses.noLicenses', 'You have no licenses yet')}</div>
                <a href="payment.html" class="btn btn-primary"><i class="fas fa-shopping-cart"></i> ${t('licenses.buyLicense', 'Buy License')}</a>
            </div>
        `;
        return;
    }

    list.innerHTML = '';

    licenses
        .slice()
        .sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''))
        .reverse()
        .forEach((lic) => {
            const card = document.createElement('div');
            card.className = 'glass';
            card.style.cssText = 'padding:20px; border-radius:16px; border:1px solid var(--glass-border); background:var(--glass-bg); margin-bottom: 16px;';

            const isActive = lic.status === 'active';
            const isExpired = lic.expires_at && new Date(lic.expires_at) < new Date();
            const isTrial = (lic.plan || '').toLowerCase() === 'trial';
            
            let statusClass = 'color: var(--secondary)';
            let statusText = t('licenses.active', 'Active');
            if (!isActive) {
                statusClass = 'color: var(--accent)';
                statusText = t('licenses.inactive', 'Inactive');
            } else if (isExpired) {
                statusClass = 'color: #f59e0b';
                statusText = t('licenses.expired', 'Expired');
            } else if (isTrial) {
                statusClass = 'color: #8b5cf6';
                statusText = t('licenses.trial', 'Trial');
            }

            const hardwareIds = lic.hardware_ids || [];
            let hardwareHtml = '';
            if (hardwareIds.length > 0) {
                hardwareHtml = `
                    <div style="margin-top: 12px; padding: 10px; background: var(--dark); border-radius: 8px;">
                        <div style="color: var(--gray-light); font-size: 0.85rem; margin-bottom: 6px;">
                            <i class="fas fa-microchip"></i> ${t('licenses.activeDevices', 'Active Devices')} (${hardwareIds.length}/${lic.max_activations || 1}):
                        </div>
                        ${hardwareIds.map(h => `<code style="display: block; color: var(--secondary); font-size: 0.8rem; margin: 4px 0;">${h}</code>`).join('')}
                    </div>
                `;
            }

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div style="flex: 1; min-width: 280px;">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                            <span style="font-weight: 800; font-size: 1.2rem; color: var(--white);">${lic.plan_name || lic.plan || t('licenses.plan', 'Plan')}</span>
                            <span style="padding: 4px 12px; border-radius: 20px; border: 1px solid var(--glass-border); font-size: 0.8rem; ${statusClass}">${statusText}</span>
                        </div>
                        <div style="color: var(--gray-light); font-size: 0.9rem; margin-bottom: 8px;">
                            <i class="fas fa-key" style="width: 20px;"></i>
                            ${t('licenses.key', 'Key')}: <code style="color: var(--primary);">${lic.key}</code>
                        </div>
                        <div style="color: var(--gray-light); font-size: 0.9rem; margin-bottom: 8px;">
                            <i class="fas fa-calendar" style="width: 20px;"></i>
                            ${t('licenses.issued', 'Issued')}: ${formatDate(lic.created_at)}
                        </div>
                        <div style="color: var(--gray-light); font-size: 0.9rem;">
                            <i class="fas fa-clock" style="width: 20px;"></i>
                            ${t('licenses.expires', 'Expires')}: ${formatDate(lic.expires_at)}
                            ${isExpired ? `<span style="color: var(--accent); margin-right: 8px;">(${t('licenses.expired', 'Expired')})</span>` : ''}
                        </div>
                        ${hardwareHtml}
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <button class="btn btn-primary download-btn" type="button" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                            <i class="fas fa-download"></i> ${t('licenses.download', 'Download License File')}
                        </button>
                        <button class="btn btn-ghost copy-btn" type="button">
                            <i class="fas fa-copy"></i> ${t('licenses.copyKey', 'Copy Key')}
                        </button>
                        ${!isTrial && isActive && !isExpired ? `
                            <a href="payment.html?renew=${lic.key}" class="btn btn-ghost" style="text-decoration: none;">
                                <i class="fas fa-sync"></i> ${t('licenses.renew', 'Renew')}
                            </a>
                        ` : ''}
                    </div>
                </div>
            `;

            // Download button handler
            const downloadBtn = card.querySelector('.download-btn');
            downloadBtn?.addEventListener('click', async () => {
                // Use existing hardware ID if available, otherwise ask
                const existingHwid = (lic.hardware_ids && lic.hardware_ids.length > 0) ? lic.hardware_ids[0] : '';
                const hwid = prompt(t('licenses.enterHwid', 'Enter your hardware ID:'), existingHwid);
                if (hwid === null) return; // Cancelled
                
                if (!hwid.trim()) {
                    UI?.showToast?.(t('licenses.hwidRequired', 'Hardware ID is required'), 'error');
                    return;
                }
                
                downloadBtn.disabled = true;
                downloadBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${t('licenses.generating', 'Generating...')}`;
                
                try {
                    await API.downloadLicenseFile(lic.key, hwid.trim());
                    UI?.showToast?.(t('licenses.downloadSuccess', 'License file downloaded'), 'success');
                } catch (e) {
                    UI?.showToast?.(e?.message || t('licenses.downloadError', 'Error downloading license file'), 'error');
                } finally {
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = `<i class="fas fa-download"></i> ${t('licenses.download', 'Download License File')}`;
                }
            });

            // Copy button handler
            const copyBtn = card.querySelector('.copy-btn');
            copyBtn?.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(lic.key);
                    UI?.showToast?.(t('licenses.keyCopied', 'License key copied'), 'success');
                } catch {
                    UI?.showToast?.(t('licenses.copyFailed', 'Copy failed'), 'error');
                }
            });

            list.appendChild(card);
        });
}

function maskLicenseKey(key) {
    if (!key || key.length < 12) return key;
    // Show first 4 and last 4 chars, mask the middle
    return key.slice(0, 4) + '-XXXX-XXXX-' + key.slice(-4);
}

function formatDate(iso) {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        // Use locale based on current language
        const locale = (window.I18N && I18N.currentLang === 'en') ? 'en-US' : 'fa-IR';
        return d.toLocaleDateString(locale);
    } catch {
        return String(iso);
    }
}
