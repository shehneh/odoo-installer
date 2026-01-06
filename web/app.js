/**
 * Odoo 19 Installer - Modern UI JavaScript
 * With progress tracking and step-by-step installation
 */

// ============ LICENSE CHECK ============
let licenseCheckIntervalApp = null;

async function checkLicense() {
  try {
    const response = await fetch('/api/license/status');
    const data = await response.json();
    
    if (!data.licensed || !data.is_valid) {
      // Redirect to license activation page
      window.location.href = 'license.html';
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('License check error:', error);
    // On error, allow access (bypass mode)
    return true;
  }
}

// Start periodic license check (every 5 seconds)
function startPeriodicLicenseCheck() {
  if (licenseCheckIntervalApp) return; // Already running
  
  licenseCheckIntervalApp = setInterval(async () => {
    const isValid = await checkLicense();
    if (!isValid) {
      // Will be redirected by checkLicense function
      if (licenseCheckIntervalApp) {
        clearInterval(licenseCheckIntervalApp);
        licenseCheckIntervalApp = null;
      }
    }
  }, 5000);
}

// ============ UTILITY FUNCTIONS ============
function el(tag, attrs = {}, text = '') {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v;
    else if (k === 'title') n.title = v;
    else if (k.startsWith('on') && typeof v === 'function') {
      n.addEventListener(k.slice(2).toLowerCase(), v);
    }
    else n.setAttribute(k, v);
  }
  if (text) n.textContent = text;
  return n;
}

async function api(path) {
  try {
    const r = await fetch(path);
    return await r.json();
  } catch (e) {
    console.error('API Error:', e);
    return { error: e.message };
  }
}

// ============ TOAST NOTIFICATIONS ============
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  const toast = el('div', { class: `toast ${type}` }, message);
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ============ SMART INSTALL UI FUNCTIONS ============

/**
 * Shows a professional confirmation dialog before starting installation
 */
async function showSmartConfirmDialog() {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.backdropFilter = 'blur(4px)';
    
    overlay.innerHTML = `
      <div class="install-modal-pro" style="max-width: 480px;">
        <div class="install-modal-header" style="text-align: center;">
          <h3 style="justify-content: center;">
            <span class="header-icon">🚀</span>
            نصب هوشمند پیش‌نیازها
          </h3>
        </div>
        <div style="padding: 28px; text-align: center;">
          <div style="font-size: 56px; margin-bottom: 16px;">⚙️</div>
          <h4 style="margin: 0 0 16px; font-size: 18px; color: #212529;">آماده نصب همه پیش‌نیازها</h4>
          <p style="color: #6c757d; margin-bottom: 24px; line-height: 1.7;">
            این فرآیند به صورت خودکار:<br>
            ✓ Python, PostgreSQL, Node.js و سایر ابزارها را نصب می‌کند<br>
            ✓ پکیج‌های مورد نیاز را نصب می‌کند<br>
            ✓ تنظیمات لازم را انجام می‌دهد
          </p>
          <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 10px; padding: 12px; margin-bottom: 20px;">
            <strong style="color: #856404;">⚠️ توجه:</strong>
            <span style="color: #856404;">ممکن است پنجره‌های نصب باز شوند. لطفاً آنها را تکمیل کنید.</span>
          </div>
          <div style="display: flex; gap: 12px; justify-content: center;">
            <button id="smart-install-cancel" class="btn btn-secondary" style="padding: 12px 28px; font-size: 15px;">انصراف</button>
            <button id="smart-install-confirm" class="btn-smart-install" style="padding: 12px 28px; font-size: 15px;">
              شروع نصب هوشمند
            </button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    document.getElementById('smart-install-cancel').onclick = () => {
      overlay.remove();
      resolve(false);
    };
    
    document.getElementById('smart-install-confirm').onclick = () => {
      overlay.remove();
      resolve(true);
    };
    
    overlay.onclick = (e) => {
      if (e.target === overlay) {
        overlay.remove();
        resolve(false);
      }
    };
  });
}

/**
 * Creates the professional installation progress modal
 */
function createSmartInstallModal(steps, versionText) {
  // Remove old modal if exists
  const oldModal = document.getElementById('smart-install-overlay');
  if (oldModal) oldModal.remove();
  
  const overlay = document.createElement('div');
  overlay.id = 'smart-install-overlay';
  overlay.className = 'modal-overlay';
  overlay.style.backdropFilter = 'blur(4px)';
  
  let stepsHtml = steps.map((step, idx) => `
    <div class="install-step-card pending" id="step-card-${step.id}">
      <div class="step-icon-pro pending" id="step-icon-${step.id}">${idx + 1}</div>
      <div class="step-content-pro">
        <div class="step-name-pro">${step.label}</div>
        <div class="step-status-pro" id="step-status-${step.id}">
          <span class="status-text">در انتظار...</span>
        </div>
      </div>
    </div>
  `).join('');
  
  overlay.innerHTML = `
    <div class="install-modal-pro">
      <div class="install-modal-header">
        <h3>
          <span class="header-icon">⚙️</span>
          نصب ${versionText}
        </h3>
      </div>
      <div style="padding: 20px 24px; max-height: 400px; overflow-y: auto;">
        ${stepsHtml}
      </div>
      <div class="live-progress">
        <div class="live-progress-bar-container">
          <div class="live-progress-bar" id="smart-progress-bar" style="width: 0%"></div>
        </div>
        <div class="live-progress-text">
          <span class="live-progress-label" id="smart-progress-label">در حال آماده‌سازی...</span>
          <span class="live-progress-percent" id="smart-progress-percent">0%</span>
        </div>
      </div>
    </div>
  `;
  
  // Prevent closing during installation
  overlay.onclick = (e) => {
    if (e.target === overlay) {
      showToast('لطفاً صبر کنید تا نصب تمام شود...', 'warning');
    }
  };
  
  document.body.appendChild(overlay);
  return overlay;
}

/**
 * Updates a step in the smart install modal
 */
function updateSmartStep(stepId, status, statusText = '', timerSeconds = 0) {
  const card = document.getElementById(`step-card-${stepId}`);
  const icon = document.getElementById(`step-icon-${stepId}`);
  const statusEl = document.getElementById(`step-status-${stepId}`);
  
  if (!card) return;
  
  // Remove all status classes
  card.className = 'install-step-card ' + status;
  icon.className = 'step-icon-pro ' + status;
  
  // Update icon content based on status
  if (status === 'active') {
    icon.innerHTML = '<div class="spinner-pro"></div>';
  } else if (status === 'success') {
    icon.innerHTML = '✓';
  } else if (status === 'error') {
    icon.innerHTML = '✗';
  }
  
  // Update status text
  if (statusEl) {
    let timerHtml = '';
    if (timerSeconds > 0 && status === 'active') {
      const mins = Math.floor(timerSeconds / 60);
      const secs = timerSeconds % 60;
      timerHtml = `<span class="timer">${mins}:${secs.toString().padStart(2, '0')}</span>`;
    }
    statusEl.innerHTML = `<span class="status-text">${statusText}</span>${timerHtml}`;
  }
}

/**
 * Updates the smart progress bar
 */
function updateSmartProgress(percent, label) {
  const bar = document.getElementById('smart-progress-bar');
  const percentEl = document.getElementById('smart-progress-percent');
  const labelEl = document.getElementById('smart-progress-label');
  
  if (bar) bar.style.width = percent + '%';
  if (percentEl) percentEl.textContent = Math.round(percent) + '%';
  if (labelEl) labelEl.textContent = label;
}

/**
 * Shows installation result modal
 */
function showSmartResultModal(successSteps, failedSteps, stopped = false) {
  const overlay = document.getElementById('smart-install-overlay');
  if (!overlay) return;
  
  const hasErrors = failedSteps.length > 0;
  const iconClass = stopped ? 'error' : (hasErrors ? 'warning' : 'success');
  const iconEmoji = stopped ? '❌' : (hasErrors ? '⚠️' : '✅');
  const title = stopped ? 'نصب متوقف شد' : (hasErrors ? 'نصب با مشکلاتی تکمیل شد' : 'نصب با موفقیت انجام شد!');
  
  let resultListHtml = '';
  
  if (successSteps.length > 0) {
    resultListHtml += successSteps.map(s => `
      <div class="result-list-item success">
        <span class="item-icon">✓</span>
        <span>${s}</span>
      </div>
    `).join('');
  }
  
  if (failedSteps.length > 0) {
    resultListHtml += failedSteps.map(s => `
      <div class="result-list-item error">
        <span class="item-icon">✗</span>
        <span>${s}</span>
      </div>
    `).join('');
  }
  
  overlay.innerHTML = `
    <div class="install-modal-pro install-result-modal">
      <div class="result-icon ${iconClass}">${iconEmoji}</div>
      <h3 class="result-title">${title}</h3>
      ${resultListHtml ? `<div class="result-list">${resultListHtml}</div>` : ''}
      <button class="btn btn-primary" style="padding: 14px 36px; font-size: 16px;" onclick="this.closest('.modal-overlay').remove(); installationInProgress = false; refresh();">
        متوجه شدم
      </button>
    </div>
  `;
}

/**
 * Smart wait for installation with real-time error detection
 */
async function smartWaitForInstall(step, onTick) {
  const startTime = Date.now();
  const maxWait = step.maxWaitTime || 180000;
  const checkInterval = step.minCheckInterval || 3000;
  let seconds = 0;
  
  // Clear any previous install result
  await api('/api/clear_install_result');
  
  while (Date.now() - startTime < maxWait) {
    await new Promise(r => setTimeout(r, 1000));
    seconds++;
    
    // Call tick callback for timer update
    if (onTick) onTick(seconds);
    
    // Check for results every few seconds
    if (seconds % Math.ceil(checkInterval / 1000) === 0) {
      try {
        const statusCheck = await api('/api/check_install_status');
        
        // === CRITICAL: Check install_result for errors ===
        if (statusCheck.install_result && statusCheck.install_result.step_id === step.id) {
          if (statusCheck.install_result.success === true) {
            return { success: true, message: 'نصب موفق' };
          }
          if (statusCheck.install_result.success === false) {
            return { 
              success: false, 
              message: statusCheck.install_result.message || 'نصب ناموفق',
              error: statusCheck.install_result.error || ''
            };
          }
        }
        
        // Also check deps status for non-pip-wheels steps
        if (statusCheck.deps && step.id !== 'pip_wheels' && step.id !== 'pg_role') {
          const dep = statusCheck.deps.find(d => d.id === step.id);
          if (dep && dep.ok) {
            return { success: true, message: 'نصب موفق (تأیید از وضعیت سیستم)' };
          }
        }
      } catch (e) {
        console.error('Status check error:', e);
      }
    }
  }
  
  // Timeout - ask user
  return { success: null, message: 'زمان انتظار تمام شد', timeout: true };
}

/**
 * Show continue prompt for timed out installations
 */
async function showSmartContinuePrompt(stepLabel) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.backdropFilter = 'blur(4px)';
    overlay.style.zIndex = '10002';
    
    overlay.innerHTML = `
      <div class="install-modal-pro" style="max-width: 420px; text-align: center; padding: 32px;">
        <div style="font-size: 56px; margin-bottom: 16px;">⏱️</div>
        <h4 style="margin: 0 0 12px; font-size: 18px;">زمان انتظار برای ${stepLabel} به پایان رسید</h4>
        <p style="color: #6c757d; margin-bottom: 24px;">
          آیا نصب با موفقیت انجام شده است؟
        </p>
        <div style="display: flex; gap: 12px; justify-content: center;">
          <button class="btn btn-secondary" style="padding: 12px 24px;" onclick="this.closest('.modal-overlay').remove();" id="prompt-no">
            خیر، رد شو
          </button>
          <button class="btn btn-success" style="padding: 12px 24px;" id="prompt-yes">
            بله، ادامه بده
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    document.getElementById('prompt-no').onclick = () => {
      overlay.remove();
      resolve(false);
    };
    
    document.getElementById('prompt-yes').onclick = () => {
      overlay.remove();
      resolve(true);
    };
  });
}

// ============ SETTINGS ============
async function showSettingsModal() {
  // Fetch current settings
  const settings = await api('/api/settings');
  
  // Create modal
  const overlay = el('div', { class: 'modal-overlay' });
  const modal = el('div', { class: 'settings-modal' });
  
  // Header
  const header = el('div', { class: 'modal-header' });
  header.innerHTML = `<h3>⚙️ تنظیمات نصب‌کننده</h3>`;
  const closeBtn = el('button', { class: 'modal-close' }, '×');
  closeBtn.onclick = () => overlay.remove();
  header.appendChild(closeBtn);
  
  // Content
  const content = el('div', { class: 'modal-content settings-content' });
  
  // Odoo Path Setting
  const odooPathSection = document.createElement('div');
  odooPathSection.className = 'setting-section';
  odooPathSection.innerHTML = `
    <label class="setting-label">
      <span class="setting-title">📁 مسیر پوشه Odoo</span>
      <span class="setting-desc">مسیر پوشه‌ای که Odoo در آن نصب شده یا نصب خواهد شد</span>
    </label>
    <div class="setting-input-row">
      <input type="text" id="setting-odoo-path" class="setting-input" 
             placeholder="مثال: C:\\odoo 19" 
             value="${settings.odoo_path || ''}" 
             dir="ltr">
      <button class="btn btn-secondary" id="btn-detect-path" title="تشخیص خودکار">🔍</button>
    </div>
    ${settings.detected_odoo_path ? `<div class="setting-hint">مسیر تشخیص داده شده: <code>${settings.detected_odoo_path}</code></div>` : ''}
  `;
  content.appendChild(odooPathSection);
  
  // Postgres Password
  const pgPassSection = document.createElement('div');
  pgPassSection.className = 'setting-section';
  pgPassSection.innerHTML = `
    <label class="setting-label">
      <span class="setting-title">🔐 رمز عبور PostgreSQL</span>
      <span class="setting-desc">رمز عبور کاربر odoo در دیتابیس</span>
    </label>
    <input type="text" id="setting-pg-password" class="setting-input" 
           value="${settings.postgres_password || 'odoo'}" dir="ltr">
  `;
  content.appendChild(pgPassSection);
  
  // Odoo Port
  const odooPortSection = document.createElement('div');
  odooPortSection.className = 'setting-section';
  odooPortSection.innerHTML = `
    <label class="setting-label">
      <span class="setting-title">🌐 پورت Odoo</span>
      <span class="setting-desc">پورت پیش‌فرض برای اجرای Odoo</span>
    </label>
    <input type="number" id="setting-odoo-port" class="setting-input" 
           value="${settings.odoo_port || 8069}" dir="ltr" min="1" max="65535">
  `;
  content.appendChild(odooPortSection);
  
  // PostgreSQL Port
  const pgPortSection = document.createElement('div');
  pgPortSection.className = 'setting-section';
  pgPortSection.innerHTML = `
    <label class="setting-label">
      <span class="setting-title">🐘 پورت PostgreSQL</span>
      <span class="setting-desc">پورت دیتابیس PostgreSQL</span>
    </label>
    <input type="number" id="setting-pg-port" class="setting-input" 
           value="${settings.postgres_port || 5432}" dir="ltr" min="1" max="65535">
  `;
  content.appendChild(pgPortSection);
  
  // Footer
  const footer = el('div', { class: 'modal-footer' });
  
  const cancelBtn = el('button', { class: 'btn btn-secondary' }, 'انصراف');
  cancelBtn.onclick = () => overlay.remove();
  
  const saveBtn = el('button', { class: 'btn btn-primary' }, '💾 ذخیره تنظیمات');
  saveBtn.onclick = async () => {
    const newSettings = {
      odoo_path: document.getElementById('setting-odoo-path').value.trim(),
      postgres_password: document.getElementById('setting-pg-password').value.trim(),
      odoo_port: parseInt(document.getElementById('setting-odoo-port').value) || 8069,
      postgres_port: parseInt(document.getElementById('setting-pg-port').value) || 5432,
    };
    
    saveBtn.disabled = true;
    saveBtn.textContent = '...';
    
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
      });
      const data = await res.json();
      
      if (data.error) {
        showToast('خطا: ' + data.error, 'error');
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 ذخیره تنظیمات';
      } else {
        showToast('تنظیمات ذخیره شد ✓', 'success');
        overlay.remove();
        
        // Clear cached data to force refresh
        cachedOdooInfo = null;
        cachedCompatibility = null;
        
        // Refresh everything including compatibility check
        refresh();
        
        // Re-check compatibility with new path
        setTimeout(() => checkCompatibility(true), 500);
      }
    } catch (e) {
      showToast('خطا در ذخیره: ' + e.message, 'error');
      saveBtn.disabled = false;
      saveBtn.textContent = '💾 ذخیره تنظیمات';
    }
  };
  
  footer.appendChild(cancelBtn);
  footer.appendChild(saveBtn);
  
  modal.appendChild(header);
  modal.appendChild(content);
  modal.appendChild(footer);
  overlay.appendChild(modal);
  
  // Close on overlay click
  overlay.onclick = (e) => {
    if (e.target === overlay) overlay.remove();
  };
  
  document.body.appendChild(overlay);
  
  // Browse folder button - opens Windows folder picker
  document.getElementById('btn-detect-path').onclick = async () => {
    const btn = document.getElementById('btn-detect-path');
    const originalText = btn.textContent;
    btn.textContent = '...';
    btn.disabled = true;
    
    try {
      const res = await fetch('/api/browse_folder');
      const data = await res.json();
      
      if (data.error) {
        showToast('خطا: ' + data.error, 'error');
      } else if (data.cancelled) {
        showToast('انتخاب لغو شد', 'info');
      } else if (data.path) {
        document.getElementById('setting-odoo-path').value = data.path;
        
        // Validate the selected folder
        try {
          const validateRes = await fetch('/api/validate_folder?path=' + encodeURIComponent(data.path));
          const validation = await validateRes.json();
          
          if (validation.valid) {
            const versionText = validation.version ? ` (Odoo ${validation.version})` : '';
            showToast(`مسیر معتبر انتخاب شد${versionText} ✓`, 'success');
          } else {
            showToast('⚠️ ' + (validation.message || 'پوشه Odoo نامعتبر است'), 'warning', 5000);
          }
        } catch (e) {
          showToast('مسیر انتخاب شد ✓', 'success');
        }
      }
    } catch (e) {
      showToast('خطا در باز کردن پنجره انتخاب پوشه', 'error');
    }
    
    btn.textContent = originalText;
    btn.disabled = false;
  };
}

// ============ STATE ============
let currentStatus = null;
let installationInProgress = false;
let installationSteps = [];
let currentStepIndex = -1;

// ============ PROGRESS CALCULATION ============
function calculateProgress(deps) {
  if (!deps || deps.length === 0) return 0;
  
  const weights = {
    python: 18,
    postgres: 20,
    pg_dump: 5,
    wkhtmltopdf: 12,
    vc_redist: 8,
    nodejs: 8,
    git: 7,
    wheelhouse: 12,
    odoo: 10
  };
  
  let totalWeight = 0;
  let completedWeight = 0;
  
  for (const dep of deps) {
    const w = weights[dep.id] || 10;
    totalWeight += w;
    if (dep.ok) completedWeight += w;
  }
  
  return totalWeight > 0 ? Math.round((completedWeight / totalWeight) * 100) : 0;
}

function updateMainProgress(percent, title, status) {
  const bar = document.getElementById('main-progress-bar');
  const percentEl = document.getElementById('progress-percent');
  const titleEl = document.getElementById('progress-title');
  const statusEl = document.getElementById('progress-status');
  
  bar.style.width = percent + '%';
  percentEl.textContent = percent + '%';
  if (title) titleEl.textContent = title;
  if (status) statusEl.textContent = status;
}

// ============ DEPENDENCIES RENDERING ============

// Installation guides for each dependency
const installGuides = {
  python: {
    title: '🐍 راهنمای نصب Python',
    content: `
<h4>Python چیست؟</h4>
<p>Python زبان برنامه‌نویسی اصلی Odoo است. بدون Python، Odoo اجرا نمی‌شود.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>به سایت <a href="https://python.org/downloads" target="_blank">python.org/downloads</a> بروید</li>
  <li>نسخه <strong>Python 3.11.x</strong> را دانلود کنید (نسخه 64-bit)</li>
  <li>فایل نصب را اجرا کنید</li>
  <li><strong>مهم:</strong> گزینه <code>Add Python to PATH</code> را حتماً تیک بزنید</li>
  <li>روی <code>Install Now</code> کلیک کنید</li>
</ol>

<h4>نصب از پوشه آفلاین:</h4>
<p>فایل نصب‌کننده در مسیر زیر قرار دارد:</p>
<code>offline\\python\\python-3.11.x-amd64.exe</code>

<h4>تأیید نصب:</h4>
<p>در Command Prompt یا PowerShell اجرا کنید:</p>
<code>python --version</code>
`
  },
  postgres: {
    title: '🐘 راهنمای نصب PostgreSQL',
    content: `
<h4>PostgreSQL چیست؟</h4>
<p>PostgreSQL دیتابیس اصلی Odoo است. تمام اطلاعات شرکت، محصولات، فاکتورها و... در این دیتابیس ذخیره می‌شوند.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>به سایت <a href="https://www.postgresql.org/download/windows/" target="_blank">postgresql.org</a> بروید</li>
  <li>نسخه <strong>PostgreSQL 16</strong> را دانلود کنید</li>
  <li>فایل نصب را اجرا کنید</li>
  <li>پسورد <code>postgres</code> را برای کاربر superuser وارد کنید (یا پسورد دلخواه)</li>
  <li>پورت پیش‌فرض <code>5432</code> را نگه دارید</li>
</ol>

<h4>بعد از نصب:</h4>
<p>باید یک کاربر برای Odoo بسازید:</p>
<code>createuser -U postgres -P -s odoo</code>

<h4>نصب از پوشه آفلاین:</h4>
<code>offline\\postgresql\\postgresql-16.x-windows-x64.exe</code>
`
  },
  pg_dump: {
    title: '💾 راهنمای pg_dump',
    content: `
<h4>pg_dump چیست؟</h4>
<p>ابزار پشتیبان‌گیری از دیتابیس PostgreSQL. برای بکاپ گرفتن از دیتابیس Odoo استفاده می‌شود.</p>

<h4>نصب:</h4>
<p>این ابزار همراه با PostgreSQL نصب می‌شود. اگر PostgreSQL نصب باشد، pg_dump هم وجود دارد.</p>

<h4>محل قرارگیری:</h4>
<code>C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe</code>

<h4>استفاده:</h4>
<code>pg_dump -U odoo -d mydb > backup.sql</code>
`
  },
  wkhtmltopdf: {
    title: '📄 راهنمای نصب wkhtmltopdf',
    content: `
<h4>wkhtmltopdf چیست؟</h4>
<p>ابزاری برای تبدیل HTML به PDF. Odoo از این ابزار برای ساخت گزارش‌های PDF (فاکتور، پیش‌فاکتور، ...) استفاده می‌کند.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>به سایت <a href="https://wkhtmltopdf.org/downloads.html" target="_blank">wkhtmltopdf.org</a> بروید</li>
  <li>نسخه <strong>0.12.6</strong> برای Windows را دانلود کنید</li>
  <li>فایل نصب را اجرا کنید</li>
  <li>مسیر پیش‌فرض را قبول کنید</li>
</ol>

<h4>نصب از پوشه آفلاین:</h4>
<code>offline\\wkhtmltopdf\\wkhtmltox-0.12.6-1.msvc2015-win64.exe</code>

<h4>تأیید نصب:</h4>
<code>wkhtmltopdf --version</code>
`
  },
  vc_redist: {
    title: '⚙️ راهنمای نصب VC++ Redistributable',
    content: `
<h4>VC++ Redistributable چیست؟</h4>
<p>کتابخانه‌های C++ مایکروسافت که بسیاری از برنامه‌ها (از جمله Python و PostgreSQL) به آن نیاز دارند.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>به سایت <a href="https://aka.ms/vs/17/release/vc_redist.x64.exe" target="_blank">مایکروسافت</a> بروید</li>
  <li>فایل <code>vc_redist.x64.exe</code> را دانلود کنید</li>
  <li>فایل را اجرا و نصب کنید</li>
</ol>

<h4>نصب از پوشه آفلاین:</h4>
<code>offline\\vc_redist\\VC_redist.x64.exe</code>

<h4>نکته:</h4>
<p>اگر قبلاً Visual Studio نصب کرده‌اید، احتمالاً این کتابخانه‌ها نصب هستند.</p>
`
  },
  nodejs: {
    title: '🟢 راهنمای نصب Node.js',
    content: `
<h4>Node.js چیست؟</h4>
<p>Node.js برای کامپایل کردن assets (CSS، JavaScript) در Odoo استفاده می‌شود. برای توسعه‌دهندگان و حالت debug لازم است.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>به سایت <a href="https://nodejs.org" target="_blank">nodejs.org</a> بروید</li>
  <li>نسخه <strong>LTS</strong> (پیشنهادی) را دانلود کنید</li>
  <li>فایل MSI را اجرا و نصب کنید</li>
</ol>

<h4>نصب از پوشه آفلاین:</h4>
<code>offline\\nodejs\\node-v20.x.x-x64.msi</code>

<h4>تأیید نصب:</h4>
<code>node --version</code>
<code>npm --version</code>

<h4>نکته:</h4>
<p>Node.js برای اجرای عادی Odoo <strong>اجباری نیست</strong>، فقط برای توسعه‌دهندگان توصیه می‌شود.</p>
`
  },
  git: {
    title: '🔀 راهنمای نصب Git',
    content: `
<h4>Git چیست؟</h4>
<p>سیستم کنترل نسخه که برای دانلود و بروزرسانی سورس‌کد Odoo و ماژول‌ها استفاده می‌شود.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>به سایت <a href="https://git-scm.com/download/win" target="_blank">git-scm.com</a> بروید</li>
  <li>نسخه 64-bit را دانلود کنید</li>
  <li>فایل را اجرا کنید</li>
  <li>تنظیمات پیش‌فرض را قبول کنید (Next → Next → Install)</li>
</ol>

<h4>نصب از پوشه آفلاین:</h4>
<code>offline\\git\\Git-2.x.x-64-bit.exe</code>

<h4>تأیید نصب:</h4>
<code>git --version</code>

<h4>استفاده برای کلون Odoo:</h4>
<code>git clone https://github.com/odoo/odoo.git --branch 19.0 --depth 1</code>
`
  },
  wheelhouse: {
    title: '📦 راهنمای Offline Wheels',
    content: `
<h4>Wheels چیست؟</h4>
<p>فایل‌های از پیش کامپایل شده پکیج‌های Python. برای نصب آفلاین وابستگی‌های Odoo استفاده می‌شوند.</p>

<h4>نصب دستی:</h4>
<ol>
  <li>محیط مجازی Python بسازید: <code>python -m venv venv</code></li>
  <li>فعال کنید: <code>venv\\Scripts\\activate</code></li>
  <li>پکیج‌ها را نصب کنید: <code>pip install -r requirements.txt</code></li>
</ol>

<h4>نصب از پوشه آفلاین:</h4>
<code>pip install --no-index --find-links offline\\wheels -r offline\\requirements.txt</code>

<h4>ساخت wheels برای سیستم‌های دیگر:</h4>
<code>pip download -r requirements.txt -d offline\\wheels</code>
`
  },
  odoo: {
    title: '🟣 راهنمای راه‌اندازی Odoo Workspace',
    content: `
<h4>Odoo Workspace چیست؟</h4>
<p>پوشه‌ای که شامل سورس‌کد Odoo، محیط مجازی Python و تنظیمات است.</p>

<h4>راه‌اندازی دستی:</h4>
<ol>
  <li>پوشه <code>odoo 19</code> را کنار پوشه Setup ایجاد کنید</li>
  <li>سورس‌کد Odoo را دانلود کنید از <a href="https://github.com/odoo/odoo" target="_blank">GitHub</a></li>
  <li>محیط مجازی بسازید: <code>python -m venv venv</code></li>
  <li>وابستگی‌ها را نصب کنید</li>
  <li>فایل <code>odoo.conf</code> را تنظیم کنید</li>
</ol>

<h4>ساختار پوشه:</h4>
<pre>
odoo 19/
├── odoo-src/
│   └── odoo-19.0/
├── venv/
├── addons/
├── odoo.conf
└── run_odoo.bat
</pre>

<h4>اجرای Odoo:</h4>
<code>venv\\Scripts\\python odoo-src\\odoo-19.0\\odoo-bin -c odoo.conf</code>
`
  }
};

// Show installation guide modal
function showInstallGuide(depId, depLabel) {
  const guide = installGuides[depId];
  if (!guide) {
    showToast('راهنمایی برای این مورد موجود نیست', 'warning');
    return;
  }
  
  // Create modal
  const overlay = el('div', { class: 'modal-overlay' });
  const modal = el('div', { class: 'install-guide-modal' });
  
  // Header
  const header = el('div', { class: 'modal-header' });
  header.innerHTML = `<h3>${guide.title}</h3>`;
  const closeBtn = el('button', { class: 'modal-close' }, '×');
  closeBtn.onclick = () => overlay.remove();
  header.appendChild(closeBtn);
  
  // Content
  const content = el('div', { class: 'modal-content' });
  content.innerHTML = guide.content;
  
  // Footer
  const footer = el('div', { class: 'modal-footer' });
  const okBtn = el('button', { class: 'btn btn-primary' }, 'متوجه شدم');
  okBtn.onclick = () => overlay.remove();
  footer.appendChild(okBtn);
  
  modal.appendChild(header);
  modal.appendChild(content);
  modal.appendChild(footer);
  overlay.appendChild(modal);
  
  // Close on overlay click
  overlay.onclick = (e) => {
    if (e.target === overlay) overlay.remove();
  };
  
  document.body.appendChild(overlay);
}

function renderDeps(deps) {
  const grid = document.getElementById('deps-grid');
  if (!grid) return;
  
  // Avoid flicker by checking if content changed
  const newHash = JSON.stringify(deps);
  if (grid.dataset.hash === newHash) return;
  grid.dataset.hash = newHash;
  
  grid.innerHTML = '';
  
  const icons = {
    python: '🐍',
    postgres: '🐘',
    pg_dump: '💾',
    wkhtmltopdf: '📄',
    vc_redist: '⚙️',
    nodejs: '🟢',
    git: '🔀',
    wheelhouse: '📦',
    odoo: '🟣'
  };
  
  // Uninstall commands mapping
  const uninstallCmds = {
    python: 'uninstall_python',
    postgres: 'uninstall_postgresql',
    wkhtmltopdf: 'uninstall_wkhtmltopdf',
    vc_redist: 'uninstall_vc_redist',
    nodejs: 'uninstall_nodejs',
    git: 'uninstall_git'
  };
  
  for (const d of deps) {
    const card = el('div', { class: `dep-card ${d.ok ? 'installed' : 'missing'}` });
    
    // Icon
    const iconDiv = el('div', { class: `dep-icon ${d.ok ? 'ok' : 'bad'}` });
    iconDiv.innerHTML = d.ok 
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    
    // Info
    const info = el('div', { class: 'dep-info' });
    const nameRow = el('div', { class: 'dep-name-row' });
    nameRow.appendChild(el('span', { class: 'dep-name' }, (icons[d.id] || '📌') + ' ' + d.label));
    
    // Help button
    if (installGuides[d.id]) {
      const helpBtn = el('button', { class: 'help-btn', title: 'راهنمای نصب' });
      helpBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
      helpBtn.onclick = (e) => {
        e.stopPropagation();
        showInstallGuide(d.id, d.label);
      };
      nameRow.appendChild(helpBtn);
    }
    
    info.appendChild(nameRow);
    if (d.details) {
      info.appendChild(el('div', { class: 'dep-details', title: d.details }, d.details.substring(0, 60) + (d.details.length > 60 ? '...' : '')));
    }
    
    // Badge
    const badge = el('span', { class: `dep-badge ${d.ok ? 'ok' : 'bad'}` }, d.ok ? 'نصب شده ✓' : 'نصب نشده');
    
    // Buttons container
    const btnContainer = el('div', { class: 'dep-buttons' });
    
    // Install button
    const canInstall = !!d.install_cmd && !d.ok;
    const installBtn = el('button', { class: 'install-btn' });
    
    if (d.ok) {
      installBtn.textContent = '✓';
      installBtn.disabled = true;
      installBtn.classList.add('installed');
    } else if (!d.install_cmd) {
      installBtn.textContent = '—';
      installBtn.disabled = true;
    } else {
      // Check if needs online action (wheels download or odoo setup)
      const needsOnline = d.id === 'wheelhouse' || d.id === 'odoo';
      const buttonLabel = d.install_label || (needsOnline ? 'راه‌اندازی' : (!d.offline_ready ? 'فایل آفلاین ندارد' : 'نصب'));
      
      installBtn.textContent = buttonLabel;
      
      // Enable for online-capable installs even without offline files
      if (!d.offline_ready && !needsOnline) {
        installBtn.disabled = true;
      } else {
        installBtn.onclick = async () => {
          installBtn.disabled = true;
          installBtn.textContent = '...';
          showToast(`در حال ${needsOnline ? 'راه‌اندازی' : 'نصب'} ${d.label}...`, 'info');
          
          const res = await api('/api/install/' + d.install_cmd);
          if (res.error) {
            showToast(`خطا: ${res.error}`, 'error');
            installBtn.textContent = buttonLabel;
            installBtn.disabled = false;
          } else {
            showToast(`${d.label} شروع شد. منتظر بمانید...`, 'success');
            // Longer wait for online operations
            setTimeout(refresh, needsOnline ? 10000 : 5000);
          }
        };
      }
    }
    btnContainer.appendChild(installBtn);
    
    // Uninstall button (only for installed items with uninstall capability)
    if (d.ok && uninstallCmds[d.id]) {
      const uninstallBtn = el('button', { class: 'uninstall-btn' });
      uninstallBtn.textContent = 'حذف';
      uninstallBtn.onclick = async () => {
        if (!confirm(`آیا از حذف ${d.label} اطمینان دارید؟`)) return;
        uninstallBtn.disabled = true;
        uninstallBtn.textContent = '...';
        showToast(`در حال حذف ${d.label}...`, 'warning');
        
        const res = await api('/api/uninstall/' + uninstallCmds[d.id]);
        if (res.error) {
          showToast(`خطا: ${res.error}`, 'error');
          uninstallBtn.textContent = 'حذف';
          uninstallBtn.disabled = false;
        } else {
          showToast(`${d.label} در حال حذف است...`, 'info');
          setTimeout(refresh, 5000);
        }
      };
      btnContainer.appendChild(uninstallBtn);
    }
    
    card.appendChild(iconDiv);
    card.appendChild(info);
    card.appendChild(badge);
    card.appendChild(btnContainer);
    grid.appendChild(card);
  }
}

// ============ SOFTWARE TOOLS RENDERING ============
function renderSoftTools(tools, systemInfo) {
  const grid = document.getElementById('soft-tools-grid');
  if (!grid) return;
  
  // Check if content changed to avoid flicker
  const newContentHash = JSON.stringify(tools);
  if (grid.dataset.hash === newContentHash) return;
  grid.dataset.hash = newContentHash;
  
  grid.innerHTML = '';
  
  if (!tools || tools.length === 0) {
    grid.innerHTML = '<p style="color: #666; padding: 20px; text-align: center;">ابزاری در پوشه soft یافت نشد</p>';
    return;
  }
  
  // Show system info
  if (systemInfo) {
    const infoDiv = document.createElement('div');
    infoDiv.className = 'system-info-banner';
    infoDiv.innerHTML = `<span>💻 سیستم: ${systemInfo.windows_edition || systemInfo.os} | معماری: <strong>${systemInfo.arch}</strong></span>`;
    grid.appendChild(infoDiv);
  }
  
  const toolIcons = {
    'WinRAR': '📦',
    'speedtop': '⚡',
    'VSCode': '💻',
    'copilot-rtl': '🤖',
    'Git': '🌿',
    'Python': '🐍',
  };
  
  for (const tool of tools) {
    const isInstalled = tool.installed === true;
    const card = el('div', { class: `dep-card ${tool.compatible === false ? 'incompatible' : ''} ${isInstalled ? 'installed' : ''}` });
    
    // Icon
    const iconDiv = el('div', { class: `dep-icon ${isInstalled ? 'ok' : ''}` });
    let icon = '🔧';
    for (const [key, emoji] of Object.entries(toolIcons)) {
      if (tool.name.includes(key)) {
        icon = emoji;
        break;
      }
    }
    if (isInstalled) {
      iconDiv.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
    } else {
      iconDiv.textContent = icon;
    }
    
    // Info
    const info = el('div', { class: 'dep-info' });
    info.appendChild(el('div', { class: 'dep-name' }, tool.name));
    
    let detailsText = '';
    if (isInstalled && tool.install_details) {
      detailsText = tool.install_details;
    } else if (tool.size > 0) {
      detailsText = (tool.size / 1024 / 1024).toFixed(2) + ' MB';
      if (tool.arch) {
        detailsText += ' | ' + tool.arch;
      }
    } else if (tool.arch) {
      detailsText = tool.arch;
    }
    if (detailsText) {
      info.appendChild(el('div', { class: 'dep-details', title: tool.path || '' }, detailsText));
    }
    
    // Badge - show installed status
    const badge = el('span', { class: `dep-badge ${isInstalled ? 'ok' : (tool.compatible === false ? 'bad' : '')}` });
    if (isInstalled) {
      badge.textContent = 'نصب شده ✓';
    } else if (tool.compatible === false) {
      badge.textContent = 'ناسازگار';
    } else if (tool.needs_download) {
      badge.textContent = 'نیاز به دانلود';
      badge.className = 'dep-badge warning';
    } else {
      badge.textContent = 'آماده نصب';
    }
    
    // Buttons container
    const btnContainer = el('div', { class: 'dep-buttons' });
    
    if (isInstalled) {
      // Already installed - show checkmark button
      const installedBtn = el('button', { class: 'install-btn installed', disabled: true });
      installedBtn.textContent = '✓';
      btnContainer.appendChild(installedBtn);
    } else if (tool.needs_download && tool.download_url) {
      // Need to download first
      const downloadBtn = el('button', { class: 'install-btn download' });
      downloadBtn.textContent = '📥 دانلود';
      downloadBtn.onclick = async () => {
        downloadBtn.disabled = true;
        downloadBtn.textContent = '...';
        showToast(`در حال دانلود ${tool.name}...`, 'info');
        
        const res = await api('/api/install/download_and_install?software=' + encodeURIComponent(tool.name));
        if (res.error) {
          showToast(`خطا: ${res.error}`, 'error');
          downloadBtn.textContent = '📥 دانلود';
          downloadBtn.disabled = false;
        } else {
          showToast(`${tool.name} در حال دانلود و نصب است...`, 'success');
          downloadBtn.textContent = '⏳';
          setTimeout(refresh, 10000);
        }
      };
      btnContainer.appendChild(downloadBtn);
    } else if (tool.path && tool.compatible !== false) {
      // Can install directly
      const installBtn = el('button', { class: 'install-btn' });
      installBtn.textContent = 'نصب';
      installBtn.onclick = async () => {
        installBtn.disabled = true;
        installBtn.textContent = '...';
        showToast(`در حال نصب ${tool.name}...`, 'info');
        
        const res = await api('/api/install/install_soft_tool?path=' + encodeURIComponent(tool.path));
        if (res.error) {
          showToast(`خطا: ${res.error}`, 'error');
          installBtn.textContent = 'نصب';
          installBtn.disabled = false;
        } else {
          showToast(`${tool.name} در حال نصب است...`, 'success');
          installBtn.textContent = '✓';
          setTimeout(refresh, 5000);
        }
      };
      btnContainer.appendChild(installBtn);
    } else {
      // Cannot install
      const disabledBtn = el('button', { class: 'install-btn', disabled: true });
      disabledBtn.textContent = tool.compatible === false ? '—' : '—';
      btnContainer.appendChild(disabledBtn);
    }
    
    card.appendChild(iconDiv);
    card.appendChild(info);
    card.appendChild(badge);
    card.appendChild(btnContainer);
    grid.appendChild(card);
  }
}

// ============ PORT STATUS ============
function updatePortStatus(ports) {
  for (const [port, active] of Object.entries(ports)) {
    const el = document.getElementById(`port-${port}`);
    if (el) {
      el.classList.toggle('active', active);
    }
  }
}

// ============ ODOO INFO ============
let cachedOdooInfo = null;

async function fetchOdooInfo() {
  try {
    const info = await api('/api/odoo_info');
    cachedOdooInfo = info;
    updateOdooInfoPanel(info);
    return info;
  } catch (e) {
    console.error('Error fetching odoo info:', e);
    return null;
  }
}

function updateOdooInfoPanel(info) {
  if (!info) return;
  
  // Update path
  const pathEl = document.getElementById('odoo-root-path');
  if (pathEl) {
    pathEl.textContent = info.odoo_root || 'پیدا نشد ❌';
    pathEl.classList.toggle('warning', !info.odoo_root);
  }
  
  // Update config path
  const configPathEl = document.getElementById('odoo-config-path');
  if (configPathEl) {
    if (info.config?.config_found) {
      configPathEl.textContent = info.config.config_path || 'یافت شد ✓';
    } else {
      configPathEl.textContent = 'پیدا نشد (از پیش‌فرض استفاده می‌شود)';
      configPathEl.classList.add('warning');
    }
  }
  
  // Update HTTP port
  const portEl = document.getElementById('odoo-http-port');
  if (portEl) {
    const port = info.http_port || 8069;
    portEl.textContent = port;
  }
  
  // Update version
  const versionEl = document.getElementById('odoo-version');
  if (versionEl) {
    versionEl.textContent = info.version ? `Odoo ${info.version}` : 'نامشخص';
  }
  
  // Update ready status
  const readyEl = document.getElementById('odoo-ready-status');
  if (readyEl) {
    if (info.ready_to_run) {
      readyEl.textContent = '✅ بله - آماده اجرا';
      readyEl.className = 'info-value ready';
    } else {
      const issues = info.issues?.join('، ') || 'مشکلات ناشناخته';
      readyEl.textContent = '❌ خیر - ' + issues;
      readyEl.className = 'info-value not-ready';
    }
  }
  
  // Update primary port item
  const port = info.http_port || 8069;
  const primaryPortItem = document.getElementById('port-primary');
  const primaryPortLabel = document.getElementById('port-primary-label');
  const primaryPortLink = document.getElementById('port-primary-link');
  
  if (primaryPortItem) {
    primaryPortItem.classList.add('primary');
  }
  if (primaryPortLabel) {
    primaryPortLabel.textContent = `پورت ${port} (تنظیم شده در کانفیگ)`;
  }
  if (primaryPortLink) {
    primaryPortLink.href = `http://localhost:${port}`;
  }
}

// ============ PACKAGE COMPATIBILITY ============
let cachedCompatibility = null;
let isCheckingCompatibility = false;

async function checkCompatibility(forceRefresh = false) {
  if (isCheckingCompatibility && !forceRefresh) return cachedCompatibility;
  
  isCheckingCompatibility = true;
  updateCompatibilityUI({ status: 'loading' });
  
  try {
    const result = await api('/api/check_compatibility');
    cachedCompatibility = result;
    updateCompatibilityUI(result);
    return result;
  } catch (e) {
    console.error('Error checking compatibility:', e);
    updateCompatibilityUI({ status: 'error', summary: 'خطا در بررسی سازگاری' });
    return null;
  } finally {
    isCheckingCompatibility = false;
  }
}

function updateCompatibilityUI(result) {
  const badge = document.getElementById('compat-badge');
  const compatCount = document.getElementById('compat-count');
  const incompatCount = document.getElementById('incompat-count');
  const missingCount = document.getElementById('missing-count');
  const packageList = document.getElementById('package-list');
  
  if (!badge) return;
  
  // Update badge
  badge.className = 'summary-badge';
  
  if (result.status === 'loading') {
    badge.classList.add('loading');
    badge.innerHTML = '<span class="badge-icon">⏳</span><span class="badge-text">در حال بررسی...</span>';
    return;
  }
  
  if (result.status === 'ok') {
    badge.classList.add('ok');
    badge.innerHTML = `<span class="badge-icon">✓</span><span class="badge-text">${result.summary}</span>`;
  } else if (result.status === 'warning') {
    badge.classList.add('warning');
    badge.innerHTML = `<span class="badge-icon">⚠</span><span class="badge-text">${result.summary}</span>`;
  } else {
    badge.classList.add('error');
    badge.innerHTML = `<span class="badge-icon">✗</span><span class="badge-text">${result.summary}</span>`;
  }
  
  // Update stats
  if (compatCount) compatCount.textContent = result.compatible || 0;
  if (incompatCount) incompatCount.textContent = result.incompatible || 0;
  if (missingCount) missingCount.textContent = result.missing || 0;
  
  // Render package list
  if (packageList && result.packages) {
    renderPackageList(result.packages);
  }
}

function renderPackageList(packages) {
  const container = document.getElementById('package-list');
  if (!container) return;
  
  container.innerHTML = '';
  
  if (!packages || packages.length === 0) {
    container.innerHTML = '<div class="package-item"><span>هیچ پکیجی یافت نشد</span></div>';
    return;
  }
  
  for (const pkg of packages) {
    const item = document.createElement('div');
    item.className = `package-item ${pkg.status}`;
    if (pkg.status === 'newer_available') item.className = 'package-item newer';
    
    // Package name
    const nameEl = document.createElement('span');
    nameEl.className = 'package-name';
    nameEl.textContent = pkg.name;
    
    // Version info
    const versionEl = document.createElement('span');
    versionEl.className = 'package-version';
    versionEl.innerHTML = `
      <span class="required">نیاز: ${pkg.required_version || 'any'}</span>
      <span class="installed">موجود: ${pkg.installed_version || '-'}</span>
    `;
    
    // Status
    const statusEl = document.createElement('span');
    statusEl.className = `package-status ${pkg.status}`;
    
    let statusIcon = '✓';
    if (pkg.status === 'missing') statusIcon = '✗';
    else if (pkg.status === 'incompatible') statusIcon = '⚠';
    else if (pkg.status === 'newer_available') statusIcon = '↑';
    
    statusEl.innerHTML = `<span>${statusIcon}</span><span>${pkg.message}</span>`;
    
    // Action button for missing/incompatible packages
    const actionEl = document.createElement('div');
    actionEl.className = 'package-action';
    
    if (pkg.status === 'missing' || pkg.status === 'incompatible') {
      const downloadBtn = document.createElement('button');
      downloadBtn.className = 'btn btn-sm btn-primary';
      downloadBtn.innerHTML = '⬇ دانلود';
      downloadBtn.onclick = () => downloadPackage(pkg.name, pkg.required_version, downloadBtn);
      actionEl.appendChild(downloadBtn);
    }
    
    item.appendChild(nameEl);
    item.appendChild(versionEl);
    item.appendChild(statusEl);
    item.appendChild(actionEl);
    
    container.appendChild(item);
  }
}

async function downloadPackage(packageName, version, btnElement) {
  if (!packageName) return;
  
  // Show loading state
  const originalContent = btnElement.innerHTML;
  btnElement.innerHTML = '<span class="spinner"></span> دانلود...';
  btnElement.disabled = true;
  
  try {
    const versionParam = version ? `&version=${encodeURIComponent(version.replace(/^[=<>!~]+/, ''))}` : '';
    const result = await api(`/api/download_package?package=${encodeURIComponent(packageName)}${versionParam}`);
    
    if (result.success) {
      showToast(`پکیج ${packageName} با موفقیت دانلود شد ✓`, 'success');
      btnElement.innerHTML = '✓ دانلود شد';
      btnElement.className = 'btn btn-sm btn-success';
      
      // Refresh compatibility after download
      setTimeout(() => checkCompatibility(true), 1000);
    } else {
      showToast(`خطا در دانلود ${packageName}: ${result.message}`, 'error');
      btnElement.innerHTML = originalContent;
      btnElement.disabled = false;
    }
  } catch (e) {
    showToast(`خطای شبکه: ${e.message}`, 'error');
    btnElement.innerHTML = originalContent;
    btnElement.disabled = false;
  }
}

async function downloadAllMissing() {
  if (!cachedCompatibility?.packages) {
    showToast('ابتدا سازگاری را بررسی کنید', 'warning');
    return;
  }
  
  const missing = cachedCompatibility.packages.filter(p => 
    p.status === 'missing' || p.status === 'incompatible'
  );
  
  if (missing.length === 0) {
    showToast('همه پکیج‌ها موجود هستند ✓', 'success');
    return;
  }
  
  showToast(`در حال دانلود ${missing.length} پکیج...`, 'info');
  
  let downloaded = 0;
  let failed = 0;
  
  for (const pkg of missing) {
    try {
      const versionParam = pkg.required_version ? 
        `&version=${encodeURIComponent(pkg.required_version.replace(/^[=<>!~]+/, ''))}` : '';
      const result = await api(`/api/download_package?package=${encodeURIComponent(pkg.name)}${versionParam}`);
      
      if (result.success) {
        downloaded++;
      } else {
        failed++;
      }
    } catch (e) {
      failed++;
    }
  }
  
  if (failed === 0) {
    showToast(`همه ${downloaded} پکیج با موفقیت دانلود شدند ✓`, 'success');
  } else {
    showToast(`${downloaded} دانلود شد، ${failed} ناموفق`, 'warning');
  }
  
  // Refresh compatibility
  checkCompatibility(true);
}

// ============ MODAL FUNCTIONS ============
function showModal() {
  document.getElementById('modal-overlay').style.display = 'flex';
}

function hideModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  installationInProgress = false;
}

// Show a prompt asking user if installation was completed manually
function showContinuePrompt(stepLabel) {
  return new Promise((resolve) => {
    const overlay = el('div', { class: 'modal-overlay continue-prompt-overlay' });
    const modal = el('div', { class: 'continue-prompt-modal' });
    
    modal.innerHTML = `
      <div class="prompt-icon">⚠️</div>
      <h3>آیا نصب ${stepLabel} کامل شد؟</h3>
      <p style="color: var(--text-secondary); margin: 16px 0; line-height: 1.8;">
        به نظر می‌رسد نصب ${stepLabel} در زمان تعیین شده تکمیل نشده است.<br>
        اگر نصب را به صورت دستی تکمیل کرده‌اید، روی <strong>"بله، ادامه بده"</strong> کلیک کنید.<br>
        در غیر این صورت، روی <strong>"توقف نصب"</strong> کلیک کنید.
      </p>
      <div style="display: flex; gap: 12px; justify-content: center; margin-top: 24px;">
        <button class="btn btn-secondary" id="prompt-stop">
          <span>🛑</span> توقف نصب
        </button>
        <button class="btn btn-primary btn-glow" id="prompt-continue">
          <span>✓</span> بله، ادامه بده
        </button>
      </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Style the modal
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 10001;';
    modal.style.cssText = 'background: var(--surface); border-radius: 20px; padding: 32px; max-width: 500px; text-align: center; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); border: 1px solid var(--glass-border);';
    
    document.getElementById('prompt-stop').onclick = () => {
      overlay.remove();
      resolve(false);
    };
    
    document.getElementById('prompt-continue').onclick = () => {
      overlay.remove();
      resolve(true);
    };
  });
}

// Show installation summary
function showInstallSummary(successful, failed, wasStopped = false) {
  const overlay = el('div', { class: 'modal-overlay summary-overlay' });
  const modal = el('div', { class: 'summary-modal' });
  
  const allSuccess = failed.length === 0;
  const icon = allSuccess ? '✅' : (wasStopped ? '⚠️' : '⚠️');
  const title = allSuccess ? 'نصب با موفقیت کامل شد!' : (wasStopped ? 'نصب متوقف شد' : 'نصب با مشکلاتی مواجه شد');
  
  let successList = '';
  if (successful.length > 0) {
    successList = `
      <div class="summary-section success">
        <h4>✓ نصب شده:</h4>
        <ul>${successful.map(s => `<li>${s}</li>`).join('')}</ul>
      </div>
    `;
  }
  
  let failedList = '';
  if (failed.length > 0) {
    failedList = `
      <div class="summary-section failed">
        <h4>✗ نصب نشده:</h4>
        <ul>${failed.map(f => `<li>${f}</li>`).join('')}</ul>
      </div>
    `;
  }
  
  modal.innerHTML = `
    <div class="summary-icon">${icon}</div>
    <h3>${title}</h3>
    ${successList}
    ${failedList}
    <div style="margin-top: 24px;">
      <button class="btn btn-primary btn-glow" id="summary-close">متوجه شدم</button>
    </div>
  `;
  
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  
  // Style
  overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 10001;';
  modal.style.cssText = 'background: var(--surface); border-radius: 20px; padding: 32px; max-width: 500px; text-align: center; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); border: 1px solid var(--glass-border);';
  
  // Style sections
  const style = document.createElement('style');
  style.textContent = `
    .summary-icon { font-size: 48px; margin-bottom: 16px; }
    .summary-section { text-align: right; margin: 16px 0; padding: 12px; border-radius: 12px; }
    .summary-section.success { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); }
    .summary-section.failed { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); }
    .summary-section h4 { margin: 0 0 8px 0; font-size: 0.9rem; }
    .summary-section.success h4 { color: #10b981; }
    .summary-section.failed h4 { color: #ef4444; }
    .summary-section ul { margin: 0; padding-right: 20px; }
    .summary-section li { margin: 4px 0; font-size: 0.85rem; color: var(--text-secondary); }
  `;
  modal.appendChild(style);
  
  document.getElementById('summary-close').onclick = () => {
    overlay.remove();
    refresh();
  };
}

function renderInstallSteps(steps, currentIndex) {
  const container = document.getElementById('install-steps');
  container.innerHTML = '';
  
  steps.forEach((step, idx) => {
    const item = el('div', { class: 'step-item' });
    
    const icon = el('div', { class: 'step-icon' });
    if (idx < currentIndex) {
      icon.classList.add('done');
      icon.innerHTML = '✓';
    } else if (idx === currentIndex) {
      icon.classList.add('running');
      icon.innerHTML = '⟳';
    } else {
      icon.classList.add('pending');
      icon.textContent = idx + 1;
    }
    
    const label = el('span', {}, step.label);
    
    item.appendChild(icon);
    item.appendChild(label);
    container.appendChild(item);
  });
}

function updateModalProgress(percent, status) {
  document.getElementById('modal-progress-bar').style.width = percent + '%';
  document.getElementById('modal-status').textContent = status;
}

// ============ FULL INSTALLATION ============

// Function to show settings modal and wait for user to configure
async function ensureSettingsConfigured() {
  return new Promise(async (resolve) => {
    const settings = await api('/api/settings');
    
    // Check if odoo_path is already set
    if (settings.odoo_path) {
      resolve(true);
      return;
    }
    
    // Show alert and open settings
    const userConfirmed = confirm('⚠️ مسیر پوشه Odoo تنظیم نشده است.\n\nقبل از شروع نصب، باید مسیر پوشه Odoo را مشخص کنید.\n\nآیا می‌خواهید صفحه تنظیمات باز شود؟');
    
    if (!userConfirmed) {
      resolve(false);
      return;
    }
    
    // Show settings modal with callback
    showSettingsModalWithCallback(resolve);
  });
}

// Settings modal with callback when saved
async function showSettingsModalWithCallback(callback) {
  // Fetch current settings
  const settings = await api('/api/settings');
  
  // Create modal
  const overlay = el('div', { class: 'modal-overlay' });
  const modal = el('div', { class: 'settings-modal' });
  
  // Header
  const header = el('div', { class: 'modal-header' });
  header.innerHTML = `<h3>⚙️ تنظیمات نصب‌کننده</h3>`;
  const closeBtn = el('button', { class: 'modal-close' }, '×');
  closeBtn.onclick = () => {
    overlay.remove();
    if (callback) callback(false);
  };
  header.appendChild(closeBtn);
  
  // Alert message
  const alertBox = el('div', { class: 'settings-alert' });
  alertBox.innerHTML = `
    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 12px 16px; margin: 16px 20px 0; display: flex; align-items: center; gap: 10px;">
      <span style="font-size: 24px;">⚠️</span>
      <div>
        <strong>لطفاً مسیر پوشه Odoo را مشخص کنید</strong>
        <p style="margin: 4px 0 0; font-size: 13px; color: #856404;">این مسیر محل نصب و اجرای Odoo خواهد بود</p>
      </div>
    </div>
  `;
  
  // Content
  const content = el('div', { class: 'modal-content settings-content' });
  
  // Odoo Path Setting (highlighted)
  const odooPathSection = document.createElement('div');
  odooPathSection.className = 'setting-section setting-required';
  odooPathSection.innerHTML = `
    <label class="setting-label">
      <span class="setting-title">📁 مسیر پوشه Odoo <span style="color: #dc3545;">*</span></span>
      <span class="setting-desc">مسیر پوشه‌ای که Odoo در آن نصب شده یا نصب خواهد شد</span>
    </label>
    <div class="setting-input-row">
      <input type="text" id="setting-odoo-path-req" class="setting-input setting-input-required" 
             placeholder="روی دکمه 🔍 کلیک کنید تا پوشه را انتخاب کنید" 
             value="${settings.odoo_path || ''}" 
             dir="ltr">
      <button class="btn btn-secondary" id="btn-browse-path-req" title="انتخاب پوشه">🔍</button>
    </div>
    ${settings.detected_odoo_path ? `<div class="setting-hint">مسیر تشخیص داده شده: <code>${settings.detected_odoo_path}</code></div>` : ''}
  `;
  content.appendChild(odooPathSection);
  
  // Postgres Password
  const pgPassSection = document.createElement('div');
  pgPassSection.className = 'setting-section';
  pgPassSection.innerHTML = `
    <label class="setting-label">
      <span class="setting-title">🔐 رمز عبور PostgreSQL</span>
      <span class="setting-desc">رمز عبور کاربر odoo در دیتابیس</span>
    </label>
    <input type="text" id="setting-pg-password-req" class="setting-input" 
           value="${settings.postgres_password || 'odoo'}" dir="ltr">
  `;
  content.appendChild(pgPassSection);
  
  // Footer
  const footer = el('div', { class: 'modal-footer' });
  
  const cancelBtn = el('button', { class: 'btn btn-secondary' }, 'انصراف');
  cancelBtn.onclick = () => {
    overlay.remove();
    if (callback) callback(false);
  };
  
  const saveBtn = el('button', { class: 'btn btn-primary' }, '✓ تأیید و ادامه نصب');
  saveBtn.onclick = async () => {
    const odooPath = document.getElementById('setting-odoo-path-req').value.trim();
    
    if (!odooPath) {
      showToast('لطفاً مسیر پوشه Odoo را انتخاب کنید', 'warning');
      document.getElementById('setting-odoo-path-req').focus();
      return;
    }
    
    const newSettings = {
      odoo_path: odooPath,
      postgres_password: document.getElementById('setting-pg-password-req').value.trim() || 'odoo',
      odoo_port: settings.odoo_port || 8069,
      postgres_port: settings.postgres_port || 5432,
    };
    
    saveBtn.disabled = true;
    saveBtn.textContent = '...';
    
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
      });
      const data = await res.json();
      
      if (data.error) {
        showToast('خطا: ' + data.error, 'error');
        saveBtn.disabled = false;
        saveBtn.textContent = '✓ تأیید و ادامه نصب';
      } else {
        showToast('تنظیمات ذخیره شد ✓', 'success');
        overlay.remove();
        if (callback) callback(true);
      }
    } catch (e) {
      showToast('خطا در ذخیره: ' + e.message, 'error');
      saveBtn.disabled = false;
      saveBtn.textContent = '✓ تأیید و ادامه نصب';
    }
  };
  
  footer.appendChild(cancelBtn);
  footer.appendChild(saveBtn);
  
  modal.appendChild(header);
  modal.appendChild(alertBox);
  modal.appendChild(content);
  modal.appendChild(footer);
  overlay.appendChild(modal);
  
  // Prevent closing on overlay click (force user to use buttons)
  overlay.onclick = (e) => {
    if (e.target === overlay) {
      showToast('لطفاً مسیر پوشه Odoo را تنظیم کنید یا انصراف را بزنید', 'info');
    }
  };
  
  document.body.appendChild(overlay);
  
  // Browse folder button
  document.getElementById('btn-browse-path-req').onclick = async () => {
    const btn = document.getElementById('btn-browse-path-req');
    const originalText = btn.textContent;
    btn.textContent = '...';
    btn.disabled = true;
    
    try {
      const res = await fetch('/api/browse_folder');
      const data = await res.json();
      
      if (data.error) {
        showToast('خطا: ' + data.error, 'error');
      } else if (data.cancelled) {
        showToast('انتخاب لغو شد', 'info');
      } else if (data.path) {
        document.getElementById('setting-odoo-path-req').value = data.path;
        showToast('مسیر انتخاب شد ✓', 'success');
      }
    } catch (e) {
      showToast('خطا در باز کردن پنجره انتخاب پوشه', 'error');
    }
    
    btn.textContent = originalText;
    btn.disabled = false;
  };
}

async function runFullInstall() {
  if (installationInProgress) {
    showToast('نصب در حال انجام است...', 'warning');
    return;
  }
  
  // First, ensure settings are configured
  const settingsOk = await ensureSettingsConfigured();
  if (!settingsOk) {
    showToast('نصب لغو شد - تنظیمات تکمیل نشد', 'warning');
    return;
  }
  
  // === SMART INSTALL CONFIRMATION ===
  const confirmResult = await showSmartConfirmDialog();
  if (!confirmResult) return;
  
  installationInProgress = true;
  
  // Get Odoo info
  const odooInfo = cachedOdooInfo || await fetchOdooInfo();
  const odooVersion = odooInfo?.version || '';
  const versionText = odooVersion ? `Odoo ${odooVersion}` : 'Odoo';
  
  // === SMART INSTALLATION STEPS ===
  // Increased maxWaitTime for online downloads (Git, wkhtmltopdf, nodejs)
  const PRIORITY_STEPS = [
    { id: 'python', label: 'Python', cmd: 'install_python_offline', weight: 18, maxWaitTime: 420000, minCheckInterval: 3000, critical: true },
    { id: 'vc_redist', label: 'VC++ Redistributable', cmd: 'install_vc_redist_offline', weight: 8, maxWaitTime: 180000, minCheckInterval: 2000, critical: false },
    { id: 'postgres', label: 'PostgreSQL', cmd: 'install_postgresql_offline', weight: 20, maxWaitTime: 480000, minCheckInterval: 4000, critical: true },
    { id: 'wkhtmltopdf', label: 'wkhtmltopdf', cmd: 'install_wkhtmltopdf_offline', weight: 12, maxWaitTime: 360000, minCheckInterval: 3000, critical: false },
    { id: 'nodejs', label: 'Node.js', cmd: 'install_nodejs_offline', weight: 8, maxWaitTime: 360000, minCheckInterval: 3000, critical: false },
    { id: 'git', label: 'Git', cmd: 'install_git_offline', weight: 8, maxWaitTime: 420000, minCheckInterval: 3000, critical: false },
    { id: 'pip_wheels', label: 'پکیج‌های Python', cmd: 'install_pip_wheels', weight: 16, maxWaitTime: 420000, minCheckInterval: 3000, critical: false },
    { id: 'pg_role', label: 'کاربر دیتابیس', cmd: 'create_pg_role', weight: 10, maxWaitTime: 60000, minCheckInterval: 2000, critical: false },
  ];
  
  // Filter already installed
  const stepsToRun = PRIORITY_STEPS.filter(step => {
    if (!currentStatus || !currentStatus.deps) return true;
    const dep = currentStatus.deps.find(d => d.id === step.id);
    return !dep || !dep.ok;
  });
  
  if (stepsToRun.length === 0) {
    showToast('همه پیش‌نیازها قبلاً نصب شده‌اند!', 'success');
    installationInProgress = false;
    return;
  }
  
  // Create smart modal
  createSmartInstallModal(stepsToRun, versionText);
  
  let totalWeight = stepsToRun.reduce((sum, s) => sum + s.weight, 0);
  let completedWeight = 0;
  let failedSteps = [];
  let successfulSteps = [];
  
  // Process each step
  for (let i = 0; i < stepsToRun.length; i++) {
    const step = stepsToRun[i];
    
    // Mark step as active
    updateSmartStep(step.id, 'active', 'در حال نصب...', 0);
    updateSmartProgress(
      Math.round((completedWeight / totalWeight) * 100),
      `در حال نصب: ${step.label}`
    );
    
    // Start installation
    const res = await api('/api/install/' + step.cmd);
    
    if (res.error) {
      updateSmartStep(step.id, 'error', res.error);
      failedSteps.push(`${step.label}: ${res.error}`);
      
      if (step.critical) {
        showSmartResultModal(successfulSteps, failedSteps, true);
        installationInProgress = false;
        return;
      }
      completedWeight += step.weight;
      continue;
    }
    
    // Wait for installation with real-time feedback
    const result = await smartWaitForInstall(step, (seconds) => {
      updateSmartStep(step.id, 'active', 'در حال نصب...', seconds);
      updateSmartProgress(
        Math.round((completedWeight / totalWeight) * 100 + (step.weight / totalWeight) * Math.min(90, seconds * 0.5)),
        `در حال نصب: ${step.label}`
      );
    });
    
    if (result.success === true) {
      updateSmartStep(step.id, 'success', 'نصب شد ✓');
      successfulSteps.push(step.label);
    } else if (result.success === false) {
      updateSmartStep(step.id, 'error', result.message || 'خطا در نصب');
      failedSteps.push(`${step.label}: ${result.message || 'خطا'}`);
      
      if (step.critical) {
        showSmartResultModal(successfulSteps, failedSteps, true);
        installationInProgress = false;
        return;
      }
    } else if (result.timeout) {
      // Ask user
      const userConfirmed = await showSmartContinuePrompt(step.label);
      if (userConfirmed) {
        updateSmartStep(step.id, 'success', 'تأیید شد (دستی)');
        successfulSteps.push(step.label + ' (دستی)');
      } else {
        updateSmartStep(step.id, 'error', 'رد شد');
        failedSteps.push(step.label);
        
        if (step.critical) {
          showSmartResultModal(successfulSteps, failedSteps, true);
          installationInProgress = false;
          return;
        }
      }
    }
    
    completedWeight += step.weight;
  }
  
  // All done
  updateSmartProgress(100, 'نصب تکمیل شد!');
  await new Promise(r => setTimeout(r, 1000));
  await refresh();
  
  showSmartResultModal(successfulSteps, failedSteps, false);
  installationInProgress = false;
}

// ============ MAIN REFRESH ============
async function refresh() {
  try {
    const j = await api('/api/status');
    currentStatus = j;
    
    // Update connection status
    const connEl = document.getElementById('connection-status');
    if (connEl) {
      connEl.querySelector('.dot').classList.add('connected');
      connEl.querySelector('span:last-child').textContent = 'متصل';
    }
    
    // Update deps
    if (j.deps) {
      renderDeps(j.deps);
      
      // Update main progress
      if (!installationInProgress) {
        const progress = calculateProgress(j.deps);
        const allInstalled = j.deps.every(d => d.ok || !d.install_cmd);
        
        if (allInstalled) {
          updateMainProgress(100, 'آماده اجرا ✓', 'همه پیش‌نیازها نصب شده‌اند. روی "اجرای Odoo" کلیک کنید.');
        } else if (progress > 0) {
          updateMainProgress(progress, 'نصب ناقص', 'برخی پیش‌نیازها نصب نشده‌اند.');
        } else {
          updateMainProgress(0, 'آماده نصب', 'برای شروع نصب روی دکمه "نصب کامل" کلیک کنید');
        }
      }
    }
    
    // Update soft tools
    if (j.soft_tools) {
      renderSoftTools(j.soft_tools, j.system_info);
    }
    
    // Update port status
    if (j.odoo_ports) {
      updatePortStatus(j.odoo_ports);
    }
    
    // Fetch and update Odoo info (config, port, etc.)
    fetchOdooInfo();
    
    // Check package compatibility (don't block refresh, run in background)
    if (!cachedCompatibility) {
      checkCompatibility();
    }
    
    // Update log
    const logEl = document.getElementById('logtail');
    if (logEl && j.log_tail) {
      logEl.textContent = j.log_tail.slice(-50).join('\n') || 'بدون لاگ';
      logEl.scrollTop = logEl.scrollHeight;
    }
    
    // Legacy compatibility
    const statusJson = document.getElementById('status-json');
    if (statusJson) {
      statusJson.textContent = JSON.stringify(j.offline, null, 2);
    }
    
  } catch (e) {
    const connEl = document.getElementById('connection-status');
    if (connEl) {
      connEl.querySelector('.dot').classList.remove('connected');
      connEl.querySelector('span:last-child').textContent = 'قطع شده';
    }
  }
}

// ============ EVENT LISTENERS ============
document.addEventListener('DOMContentLoaded', async () => {
  // Check license first
  const isLicensed = await checkLicense();
  if (!isLicensed) {
    return; // Will be redirected to license page
  }
  
  // Start periodic license check to detect license removal/expiry
  startPeriodicLicenseCheck();
  
  // Settings button
  document.getElementById('btn-settings').addEventListener('click', showSettingsModal);
  
  // Full install button
  document.getElementById('btn-full-install').addEventListener('click', runFullInstall);
  
  // Start Odoo
  document.getElementById('btn-start-odoo').addEventListener('click', async () => {
    const btn = document.getElementById('btn-start-odoo');
    btn.disabled = true;
    btn.textContent = '...';
    
    try {
      // First check if Odoo is already running by checking the configured port
      const odooInfo = cachedOdooInfo || await fetchOdooInfo();
      const port = odooInfo?.http_port || 8069;
      
      // Check if the port is already active
      const status = await api('/api/status');
      const portActive = status?.odoo_ports?.[String(port)];
      
      if (portActive) {
        // Odoo is already running, just open the browser
        showToast(`Odoo در حال اجرا است روی پورت ${port}. در حال باز کردن مرورگر...`, 'success');
        window.open(`http://localhost:${port}`, '_blank');
        btn.disabled = false;
        btn.innerHTML = '▶ اجرای Odoo';
        return;
      }
      
      // Odoo is not running, start it
      showToast('در حال اجرای Odoo...', 'info');
      const res = await api('/api/start_odoo');
      
      if (res.error) {
        // Show detailed error with suggestion
        showToast(`خطا: ${res.error}`, 'error', 8000);
        
        // If it's a missing dependency error, suggest full install
        if (res.error.includes('پیدا نشد') || res.error.includes('ایجاد نشده')) {
          setTimeout(() => {
            if (confirm('برای رفع این مشکل، آیا می‌خواهید "نصب کامل" را اجرا کنید؟')) {
              document.getElementById('btn-full-install').click();
            }
          }, 1000);
        }
      } else {
        // Get the port from the response (read from odoo.conf)
        const actualPort = res.http_port || 8069;
        const configInfo = res.config_found ? ` (از کانفیگ)` : ' (پیش‌فرض)';
        showToast(`Odoo در حال راه‌اندازی روی پورت ${actualPort}${configInfo}...`, 'success', 6000);
        
        // Wait a bit for Odoo to start, then open browser
        setTimeout(() => {
          window.open(`http://localhost:${actualPort}`, '_blank');
        }, 5000);
      }
    } catch (e) {
      showToast(`خطای شبکه: ${e.message}`, 'error');
    }
    
    btn.disabled = false;
    btn.innerHTML = '▶ اجرای Odoo';
    setTimeout(refresh, 2000);
  });
  
  // Restart Odoo
  document.getElementById('btn-restart-odoo').addEventListener('click', async () => {
    showToast('در حال ری‌استارت Odoo...', 'info');
    await api('/api/install/restart_odoo');
    showToast('Odoo ری‌استارت شد', 'success');
    setTimeout(refresh, 3000);
  });
  
  // Compatibility check button
  const btnCheckCompat = document.getElementById('btn-check-compatibility');
  if (btnCheckCompat) {
    btnCheckCompat.addEventListener('click', async () => {
      btnCheckCompat.disabled = true;
      btnCheckCompat.innerHTML = '<span class="spinner"></span> بررسی...';
      await checkCompatibility(true);
      btnCheckCompat.disabled = false;
      btnCheckCompat.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"/>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        بررسی مجدد
      `;
    });
  }
  
  // Compatibility details toggle
  const toggleCompatDetails = document.getElementById('toggle-compat-details');
  if (toggleCompatDetails) {
    toggleCompatDetails.addEventListener('click', function() {
      const content = document.getElementById('package-list');
      const isOpen = content.style.display !== 'none';
      content.style.display = isOpen ? 'none' : 'block';
      this.classList.toggle('open', !isOpen);
    });
  }
  
  // Advanced toggle
  document.getElementById('toggle-advanced').addEventListener('click', function() {
    const content = document.getElementById('advanced-content');
    const isOpen = content.style.display !== 'none';
    content.style.display = isOpen ? 'none' : 'block';
    this.classList.toggle('open', !isOpen);
  });
  
  // Advanced buttons
  document.getElementById('btn-run-fetch').addEventListener('click', async () => {
    showToast('در حال دانلود وابستگی‌ها...', 'info');
    await api('/api/run_fetch');
    setTimeout(refresh, 2000);
  });
  
  document.getElementById('btn-run-fetch-auto').addEventListener('click', async () => {
    showToast('در حال دانلود و نصب خودکار...', 'info');
    await api('/api/run_fetch?autorun=1');
    setTimeout(refresh, 2000);
  });
  
  document.getElementById('btn-run-check').addEventListener('click', async () => {
    showToast('در حال بررسی وضعیت...', 'info');
    const res = await api('/api/run_check');
    if (res.stdout) {
      alert(res.stdout);
    }
    setTimeout(refresh, 1000);
  });
  
  document.getElementById('btn-create-role').addEventListener('click', async () => {
    showToast('در حال ساخت کاربر دیتابیس...', 'info');
    await api('/api/install/create_pg_role');
    showToast('پنجره ساخت کاربر باز شد', 'success');
    setTimeout(refresh, 5000);
  });
  
  // Clear log
  document.getElementById('btn-clear-log').addEventListener('click', () => {
    document.getElementById('logtail').textContent = '';
    showToast('لاگ پاک شد', 'info');
  });
  
  // Modal close
  document.getElementById('modal-close').addEventListener('click', hideModal);
  document.getElementById('modal-cancel').addEventListener('click', hideModal);
  document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hideModal();
  });
  
  // Initial refresh
  refresh();
  
  // Auto-refresh every 5 seconds
  setInterval(refresh, 5000);
});

