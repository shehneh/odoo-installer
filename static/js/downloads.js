/* ============================================
   OdooMaster - Downloads Page
   Release-driven downloads via downloads.json
   ============================================ */

(function () {
    const state = {
        data: null,
        activeMajor: 19,
    };

    function qs(sel, root = document) { return root.querySelector(sel); }
    function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

    function getToken() {
        const raw = localStorage.getItem('authToken');
        if (raw === null || raw === undefined) return null;
        let t = String(raw).trim();
        if (!t) return null;
        if (t === 'null' || t === 'undefined') return null;
        if (/^bearer\s+/i.test(t)) t = t.replace(/^bearer\s+/i, '').trim();
        return t || null;
    }

    async function validateSession() {
        const token = getToken();
        if (!token || typeof API === 'undefined' || !API.getMe) return;

        try {
            // Ensure API.token is in sync (defensive)
            API.token = token;
            const res = await API.getMe();
            if (res?.user) {
                localStorage.setItem('user', JSON.stringify(res.user));
                UI?.updateNavigation?.();
            }
        } catch (e) {
            // Token invalid/expired -> clear local state so UI doesn't think it's logged in
            if (e && (e.status === 401 || /توکن|وارد شوید/.test(e.message || ''))) {
                localStorage.removeItem('authToken');
                localStorage.removeItem('user');
                UI?.updateNavigation?.();
            }
        }
    }

    function showToastSafe(message, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }
        // fallback
        if (type === 'error') {
            alert(message);
        } else {
            console.log(message);
        }
    }

    function formatMajorLabel(major) {
        return `Odoo ${major}`;
    }

    function buildTabs(versions) {
        const tabsRoot = qs('.version-tabs');
        if (!tabsRoot) return;

        // pick max with items, otherwise max major
        const majorsWithItems = versions
            .filter(v => Array.isArray(v.items) && v.items.length > 0)
            .map(v => v.odoo_major);
        const maxMajor = Math.max(...versions.map(v => v.odoo_major));
        state.activeMajor = majorsWithItems.length ? Math.max(...majorsWithItems) : maxMajor;

        tabsRoot.innerHTML = versions
            .sort((a, b) => b.odoo_major - a.odoo_major)
            .map(v => {
                const active = v.odoo_major === state.activeMajor ? 'active' : '';
                const badge = v.badge ? `<span class="badge">${v.badge}</span>` : '';
                return `<button class="version-tab ${active}" data-version="${v.odoo_major}">${badge}${formatMajorLabel(v.odoo_major)}</button>`;
            })
            .join('');

        qsa('.version-tab', tabsRoot).forEach(btn => {
            btn.addEventListener('click', () => {
                qsa('.version-tab', tabsRoot).forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.activeMajor = Number(btn.dataset.version);
                renderCards();
            });
        });
    }

    function renderEmptyState(container, major) {
        container.innerHTML = `
            <div class="download-card" style="grid-column: 1 / -1; text-align: center;">
                <div class="download-header" style="justify-content:center;">
                    <div class="download-icon"><i class="fas fa-clock"></i></div>
                    <div class="download-info">
                        <h3>فعلاً در دست آماده‌سازی</h3>
                        <div class="download-meta"><span><i class="fas fa-code-branch"></i> ${formatMajorLabel(major)}</span></div>
                    </div>
                </div>
                <p class="download-desc">برای این نسخه هنوز Release عمومی ثبت نشده است.</p>
            </div>
        `;
    }

    function escapeHtml(str) {
        return String(str)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function cardIconFor(item) {
        if (item.id.includes('full')) return '<i class="fas fa-box"></i>';
        if (item.id.includes('lite')) return '<i class="fas fa-feather"></i>';
        if (item.id.includes('addons')) return '<i class="fas fa-puzzle-piece"></i>';
        return '<i class="fas fa-download"></i>';
    }

    function buildCard(item) {
        const featuredClass = item.featured ? 'featured' : '';
        // Check URL for highlight parameter
        const params = new URLSearchParams(window.location.search);
        const highlightId = params.get('highlight');
        const highlightClass = (highlightId && item.id === highlightId) ? 'highlighted' : '';
        
        const sizeText = item.size_hint ? escapeHtml(item.size_hint) : '';
        const verText = item.version ? `v${escapeHtml(item.version)}` : '';
        const sha = item.sha256 ? escapeHtml(item.sha256) : '';
        const shaRow = sha
            ? `<span title="SHA256"><i class="fas fa-fingerprint"></i> SHA256</span>`
            : '';

        const features = Array.isArray(item.features) ? item.features : [];

        const isLoggedIn = !!getToken();

        const hasDirectUrl = !!(item.download_url && String(item.download_url).trim());
        const hasReleaseFile = !!(item.file_name && String(item.file_name).trim());
        const isDownloadReady = hasDirectUrl || hasReleaseFile;

        const downloadLabel = !isDownloadReady
            ? 'به\u200Cزودی'
            : (item.requires_login && !isLoggedIn ? 'دانلود (پس از ورود)' : 'دانلود');

        const downloadDisabled = !isDownloadReady ? 'disabled' : '';
        
        // Add badge for highlighted item
        const highlightBadge = highlightClass ? '<div class="highlight-badge"><i class="fas fa-arrow-down"></i> این فایل را دانلود کنید</div>' : '';

        return `
            <div class="download-card ${featuredClass} ${highlightClass}" id="${escapeHtml(item.id)}">
                ${highlightBadge}
                <div class="download-header">
                    <div class="download-icon">${cardIconFor(item)}</div>
                    <div class="download-info">
                        <h3>${escapeHtml(item.title || '')}</h3>
                        <div class="download-meta">
                            ${sizeText ? `<span><i class=\"fas fa-file-archive\"></i> ${sizeText}</span>` : ''}
                            ${verText ? `<span><i class=\"fas fa-code-branch\"></i> ${verText}</span>` : ''}
                            ${shaRow}
                        </div>
                    </div>
                </div>
                <p class="download-desc">${escapeHtml(item.description || '')}</p>
                <ul class="download-features">
                    ${features.map(f => `<li><i class=\"fas fa-check\"></i> ${escapeHtml(f)}</li>`).join('')}
                </ul>
                ${sha ? `
                <div class="code-block" style="margin: 0 0 16px;">
                    <button class="code-copy" data-copy="${sha}"><i class="fas fa-copy"></i> کپی</button>
                    <pre style="direction:ltr; text-align:left; margin:0; font-family:Consolas, monospace; font-size: 0.85rem; color: var(--gray-light);">${sha}</pre>
                </div>` : ''}
                <div class="download-actions">
                    <a href="#" class="btn btn-primary btn-download ${downloadDisabled}" data-id="${escapeHtml(item.id)}" aria-disabled="${downloadDisabled ? 'true' : 'false'}">
                        <i class="fas fa-download"></i>
                        ${downloadLabel}
                    </a>
                    <a href="docs.html" class="btn btn-ghost">
                        <i class="fas fa-book"></i>
                        راهنما
                    </a>
                </div>
            </div>
        `;
    }

    function renderCards() {
        const container = qs('#downloadCards');
        if (!container || !state.data) return;

        const version = state.data.versions.find(v => v.odoo_major === state.activeMajor);
        const items = version?.items || [];

        if (!items.length) {
            renderEmptyState(container, state.activeMajor);
            return;
        }

        container.innerHTML = items.map(buildCard).join('');

        // copy sha
        qsa('.code-copy', container).forEach(btn => {
            btn.addEventListener('click', async () => {
                const text = btn.getAttribute('data-copy') || '';
                try {
                    await navigator.clipboard.writeText(text);
                    btn.innerHTML = '<i class="fas fa-check"></i> کپی شد';
                    setTimeout(() => (btn.innerHTML = '<i class="fas fa-copy"></i> کپی'), 1500);
                } catch {
                    showToastSafe('کپی انجام نشد (دسترسی Clipboard)', 'error');
                }
            });
        });

        // download
        qsa('.btn-download', container).forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();

                if (btn.classList.contains('disabled')) {
                    showToastSafe('این فایل هنوز منتشر نشده است.', 'error');
                    return;
                }

                const id = btn.getAttribute('data-id');
                const item = items.find(x => x.id === id);
                if (!item) return;

                if (item.requires_login && !getToken()) {
                    if (confirm('برای دانلود این فایل باید وارد شوید. انتقال به صفحه ورود؟')) {
                        window.location.href = 'login.html?redirect=downloads.html';
                    }
                    return;
                }

                // Public item but no file/url configured
                const hasDirectUrl = !!(item.download_url && String(item.download_url).trim());
                const hasReleaseFile = !!(item.file_name && String(item.file_name).trim());
                if (!hasDirectUrl && !hasReleaseFile) {
                    showToastSafe('این فایل هنوز آماده دانلود نیست.', 'error');
                    return;
                }

                // If direct URL is provided (public), use it.
                if (hasDirectUrl && !item.requires_login && !item.requires_purchase) {
                    window.open(String(item.download_url), '_blank', 'noopener');
                    return;
                }

                // Start download via API (signed, short-lived URL)
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال آماده‌سازی...';
                btn.classList.add('disabled');

                (async () => {
                    try {
                        if (typeof API === 'undefined' || !API.requestDownload) {
                            throw new Error('api_not_loaded');
                        }
                        const resp = await API.requestDownload(id);
                        const url = resp && resp.download_url;
                        if (!url) {
                            throw new Error('no_download_url');
                        }
                        btn.innerHTML = '<i class="fas fa-check"></i> شروع شد';
                        window.open(url, '_blank', 'noopener');
                    } catch (e) {
                        // Common cases: 401 needs login, 403 needs purchase, 404 not ready
                        if (e && e.status === 401) {
                            localStorage.removeItem('authToken');
                            localStorage.removeItem('user');
                            if (confirm('برای دانلود باید دوباره وارد شوید. انتقال به صفحه ورود؟')) {
                                window.location.href = 'login.html?redirect=downloads.html';
                                return;
                            }
                        }
                        if (e && e.status === 403) {
                            if (confirm('برای دانلود این فایل نیاز به لایسنس معتبر دارید. انتقال به صفحه خرید؟')) {
                                window.location.href = 'payment.html';
                                return;
                            }
                        }
                        if (e && e.status === 404) {
                            showToastSafe('این فایل هنوز روی سرور قرار نگرفته است.', 'error');
                            btn.innerHTML = '<i class="fas fa-download"></i> به\u200Cزودی';
                            btn.classList.add('disabled');
                            return;
                        }

                        const msg = (e && e.message === 'api_not_loaded')
                            ? 'خطا: فایل api.js لود نشده است.'
                            : (e && e.message === 'no_download_url')
                                ? 'لینک دانلود آماده نشد.'
                                : (e && e.message ? e.message : 'خطا در شروع دانلود');
                        showToastSafe(msg, 'error');
                        btn.innerHTML = '<i class="fas fa-download"></i> ' + (item.requires_login ? 'دانلود (پس از ورود)' : 'دانلود');
                    } finally {
                        btn.classList.remove('disabled');
                    }
                })();
            });
        });
    }

    async function init() {
        try {
            await validateSession();

            const res = await fetch('downloads.json', { cache: 'no-store' });
            if (!res.ok) throw new Error('downloads.json not found');
            state.data = await res.json();

            buildTabs(state.data.versions || []);
            renderCards();

        } catch (e) {
            console.error(e);
            const container = qs('#downloadCards');
            if (container) {
                container.innerHTML = `
                    <div class="download-card" style="grid-column: 1 / -1; text-align: center;">
                        <div class="download-header" style="justify-content:center;">
                            <div class="download-icon"><i class="fas fa-triangle-exclamation"></i></div>
                            <div class="download-info">
                                <h3>خطا در بارگذاری لیست دانلود</h3>
                            </div>
                        </div>
                        <p class="download-desc">فایل downloads.json قابل بارگذاری نیست.</p>
                    </div>
                `;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();
