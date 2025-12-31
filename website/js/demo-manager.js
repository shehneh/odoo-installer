/**
 * OdooMaster - Online Demo Management
 * Handles creating and managing online Odoo demo instances
 */

const DemoManager = {
    instances: [],
    maxInstances: 3,

    init() {
        this.loadInstances();
        this.attachEventListeners();
    },

    attachEventListeners() {
        const createBtn = document.getElementById('createDemoBtn');
        const newTicketBtn = document.getElementById('newTicketBtn');

        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCreateDemoDialog());
        }

        if (newTicketBtn) {
            newTicketBtn.addEventListener('click', () => this.showNewTicketDialog());
        }
    },

    loadInstances() {
        // Load from localStorage or API
        const stored = localStorage.getItem('demoInstances');
        if (stored) {
            this.instances = JSON.parse(stored);
            this.renderInstances();
        }
    },

    saveInstances() {
        localStorage.setItem('demoInstances', JSON.stringify(this.instances));
    },

    renderInstances() {
        const container = document.getElementById('instancesList');
        const countBadge = document.querySelector('.instances-count');

        if (!container) return;

        if (countBadge) {
            countBadge.textContent = `${toPersianNum(this.instances.length)} از ${toPersianNum(this.maxInstances)}`;
        }

        if (this.instances.length === 0) {
            container.innerHTML = `
                <div class="no-instances">
                    <i class="fas fa-box-open"></i>
                    <p>هنوز دمویی ندارید</p>
                    <small>اولین دموی آنلاین خود را بسازید</small>
                </div>
            `;
            return;
        }

        container.innerHTML = this.instances.map(instance => `
            <div class="instance-card" data-id="${instance.id}">
                <div class="instance-icon">
                    <i class="fas fa-server"></i>
                </div>
                <div class="instance-info">
                    <h5>${instance.name}</h5>
                    <div class="instance-meta">
                        <span><i class="fas fa-clock"></i> ${this.getTimeRemaining(instance.expiresAt)}</span>
                        <span><i class="fas fa-database"></i> ${instance.database}</span>
                    </div>
                </div>
                <div class="instance-actions">
                    <a href="${instance.url}" target="_blank" class="btn btn-primary btn-sm">
                        <i class="fas fa-external-link-alt"></i>
                        باز کردن
                    </a>
                    <button class="btn btn-outline btn-sm" onclick="DemoManager.deleteInstance('${instance.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    },

    getTimeRemaining(expiresAt) {
        const now = new Date();
        const expiry = new Date(expiresAt);
        const diff = expiry - now;

        if (diff <= 0) return 'منقضی شده';

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

        if (days > 0) {
            return `${toPersianNum(days)} روز و ${toPersianNum(hours)} ساعت`;
        } else {
            return `${toPersianNum(hours)} ساعت`;
        }
    },

    async showCreateDemoDialog() {
        const result = await this.showDialog({
            title: 'ساخت دمو آنلاین رایگان',
            html: `
                <div style="text-align: right;">
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">
                        یک نسخه کامل Odoo با تمام ماژول‌ها برای ۱۴ روز رایگان بسازید.
                    </p>
                    <div class="form-group">
                        <label>نام دمو</label>
                        <input type="text" id="demoName" class="form-input" 
                               placeholder="مثال: شرکت تست من" value="دموی من">
                    </div>
                    <div class="form-group">
                        <label>نام دیتابیس (فقط حروف انگلیسی)</label>
                        <input type="text" id="demoDb" class="form-input" 
                               placeholder="my_company" value="demo_${Date.now()}">
                    </div>
                    <div class="form-group">
                        <label>زبان</label>
                        <select id="demoLang" class="form-input">
                            <option value="fa_IR">فارسی</option>
                            <option value="en_US">English</option>
                        </select>
                    </div>
                    <div style="background: rgba(113, 75, 103, 0.1); padding: 16px; border-radius: 12px; margin-top: 20px;">
                        <p style="font-size: 0.9rem; color: var(--text-secondary); margin: 0;">
                            <i class="fas fa-info-circle"></i>
                            دمو پس از ۱۴ روز به صورت خودکار حذف می‌شود. در صورت نیاز می‌توانید backup بگیرید.
                        </p>
                    </div>
                </div>
            `,
            confirmText: 'ساخت دمو',
            cancelText: 'انصراف'
        });

        if (result.confirmed) {
            const name = document.getElementById('demoName').value;
            const database = document.getElementById('demoDb').value;
            const lang = document.getElementById('demoLang').value;

            await this.createInstance(name, database, lang);
        }
    },

    async createInstance(name, database, lang) {
        if (this.instances.length >= this.maxInstances) {
            this.showToast('حداکثر تعداد دمو محدود است!', 'error');
            return;
        }

        this.showLoadingDialog('در حال ساخت دمو...');

        try {
            // Simulate API call - Replace with actual API
            await this.delay(2000);

            const instance = {
                id: this.generateId(),
                name: name || 'دمو من',
                database: database || `demo_${Date.now()}`,
                lang: lang || 'fa_IR',
                url: `https://demo.odoomaster.com/${database}`,
                createdAt: new Date().toISOString(),
                expiresAt: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString()
            };

            this.instances.push(instance);
            this.saveInstances();
            this.renderInstances();

            this.hideDialog();
            this.showToast('دمو با موفقیت ساخته شد! 🎉', 'success');

            // Open demo in new tab after 1 second
            setTimeout(() => {
                window.open(instance.url, '_blank');
            }, 1000);

        } catch (error) {
            this.hideDialog();
            this.showToast('خطا در ساخت دمو. لطفا دوباره تلاش کنید.', 'error');
            console.error('Demo creation error:', error);
        }
    },

    deleteInstance(id) {
        if (!confirm('آیا از حذف این دمو اطمینان دارید؟')) return;

        this.instances = this.instances.filter(inst => inst.id !== id);
        this.saveInstances();
        this.renderInstances();
        this.showToast('دمو حذف شد', 'success');
    },

    async showNewTicketDialog() {
        const result = await this.showDialog({
            title: 'تیکت جدید',
            html: `
                <div style="text-align: right;">
                    <div class="form-group">
                        <label>موضوع</label>
                        <input type="text" id="ticketSubject" class="form-input" 
                               placeholder="موضوع تیکت خود را وارد کنید">
                    </div>
                    <div class="form-group">
                        <label>دسته‌بندی</label>
                        <select id="ticketCategory" class="form-input">
                            <option value="technical">مشکل فنی</option>
                            <option value="billing">مالی و پرداخت</option>
                            <option value="license">لایسنس</option>
                            <option value="general">سوال عمومی</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>توضیحات</label>
                        <textarea id="ticketMessage" class="form-input" rows="5" 
                                  placeholder="توضیحات کامل مشکل یا سوال خود را بنویسید..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="ticketUrgent">
                            <span style="margin-right: 8px;">فوری است</span>
                        </label>
                    </div>
                </div>
            `,
            confirmText: 'ارسال تیکت',
            cancelText: 'انصراف'
        });

        if (result.confirmed) {
            const subject = document.getElementById('ticketSubject').value;
            const category = document.getElementById('ticketCategory').value;
            const message = document.getElementById('ticketMessage').value;
            const urgent = document.getElementById('ticketUrgent').checked;

            if (!subject || !message) {
                this.showToast('لطفا موضوع و توضیحات را پر کنید', 'error');
                return;
            }

            await this.submitTicket({ subject, category, message, urgent });
        }
    },

    async submitTicket(data) {
        this.showLoadingDialog('در حال ارسال تیکت...');

        try {
            // Simulate API call
            await this.delay(1500);

            this.hideDialog();
            this.showToast('تیکت با موفقیت ثبت شد! تیم پشتیبانی به زودی پاسخ می‌دهد.', 'success');

        } catch (error) {
            this.hideDialog();
            this.showToast('خطا در ارسال تیکت', 'error');
        }
    },

    // Dialog System
    showDialog({ title, html, confirmText, cancelText }) {
        return new Promise((resolve) => {
            const dialog = document.createElement('div');
            dialog.className = 'demo-dialog-overlay';
            dialog.innerHTML = `
                <div class="demo-dialog glass">
                    <div class="demo-dialog-header">
                        <h3>${title}</h3>
                        <button class="dialog-close">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="demo-dialog-body">
                        ${html}
                    </div>
                    <div class="demo-dialog-footer">
                        <button class="btn btn-ghost dialog-cancel">${cancelText}</button>
                        <button class="btn btn-primary dialog-confirm">${confirmText}</button>
                    </div>
                </div>
            `;

            document.body.appendChild(dialog);

            setTimeout(() => dialog.classList.add('show'), 10);

            const close = () => {
                dialog.classList.remove('show');
                setTimeout(() => dialog.remove(), 300);
            };

            dialog.querySelector('.dialog-close').onclick = () => {
                close();
                resolve({ confirmed: false });
            };

            dialog.querySelector('.dialog-cancel').onclick = () => {
                close();
                resolve({ confirmed: false });
            };

            dialog.querySelector('.dialog-confirm').onclick = () => {
                resolve({ confirmed: true, dialog });
            };

            dialog.onclick = (e) => {
                if (e.target === dialog) {
                    close();
                    resolve({ confirmed: false });
                }
            };
        });
    },

    showLoadingDialog(message) {
        const dialog = document.createElement('div');
        dialog.className = 'demo-dialog-overlay show';
        dialog.id = 'loadingDialog';
        dialog.innerHTML = `
            <div class="demo-dialog glass loading-dialog">
                <div class="loading-spinner">
                    <i class="fas fa-circle-notch fa-spin"></i>
                </div>
                <p>${message}</p>
            </div>
        `;
        document.body.appendChild(dialog);
    },

    hideDialog() {
        const dialog = document.getElementById('loadingDialog');
        if (dialog) {
            dialog.classList.remove('show');
            setTimeout(() => dialog.remove(), 300);
        }
    },

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `message-toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toast-slide-out 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    // Helper functions
    generateId() {
        return 'demo_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => DemoManager.init());
} else {
    DemoManager.init();
}

// Helper function for Persian numbers (if not already defined)
function toPersianNum(num) {
    const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
    return String(num).replace(/\d/g, d => persianDigits[d]);
}
