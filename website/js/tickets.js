// ========================================
// TICKET SYSTEM - Professional JavaScript
// ========================================

let allMyTickets = [];
let allAdminTickets = [];
let currentTicketId = null;
let lastSeenTickets = JSON.parse(localStorage.getItem('lastSeenTickets') || '{}');

// Status names in Persian
const statusNames = {
    'open': 'باز',
    'in_progress': 'در حال بررسی',
    'waiting': 'در انتظار پاسخ',
    'closed': 'بسته شده'
};

const priorityNames = {
    'low': 'پایین',
    'medium': 'متوسط',
    'high': 'بالا',
    'urgent': 'فوری'
};

const categoryNames = {
    'technical': 'فنی',
    'billing': 'مالی',
    'general': 'عمومی',
    'feature': 'درخواست ویژگی'
};

const categoryIcons = {
    'technical': '🔧',
    'billing': '💳',
    'general': '📝',
    'feature': '✨'
};

// Check if ticket has unread messages
function hasUnreadMessages(ticket) {
    const lastSeen = lastSeenTickets[ticket.id] || 0;
    const ticketUpdated = new Date(ticket.updated_at).getTime();
    return ticketUpdated > lastSeen && ticket.status !== 'closed';
}

// Mark ticket as read
function markTicketAsRead(ticketId) {
    lastSeenTickets[ticketId] = Date.now();
    localStorage.setItem('lastSeenTickets', JSON.stringify(lastSeenTickets));
    updateNotificationBadges();
}

// Update notification badges
function updateNotificationBadges() {
    // User tickets
    const unreadUserCount = allMyTickets.filter(t => hasUnreadMessages(t)).length;
    const userBadge = document.getElementById('unreadTicketsBadge');
    const myTicketsCountBadge = document.getElementById('myTicketsCount');
    
    if (userBadge) {
        if (unreadUserCount > 0) {
            userBadge.textContent = unreadUserCount > 9 ? '9+' : unreadUserCount;
            userBadge.classList.remove('hidden');
            if (myTicketsCountBadge) {
                myTicketsCountBadge.classList.add('unread');
            }
        } else {
            userBadge.classList.add('hidden');
            if (myTicketsCountBadge) {
                myTicketsCountBadge.classList.remove('unread');
            }
        }
    }
    
    // Admin tickets
    const unreadAdminCount = allAdminTickets.filter(t => hasUnreadMessages(t)).length;
    const adminBadge = document.getElementById('unreadAdminTicketsBadge');
    const adminTicketsCountBadge = document.getElementById('adminTicketsCount');
    
    if (adminBadge) {
        if (unreadAdminCount > 0) {
            adminBadge.textContent = unreadAdminCount > 9 ? '9+' : unreadAdminCount;
            adminBadge.classList.remove('hidden');
            if (adminTicketsCountBadge) {
                adminTicketsCountBadge.classList.add('unread');
            }
        } else {
            adminBadge.classList.add('hidden');
            if (adminTicketsCountBadge) {
                adminTicketsCountBadge.classList.remove('unread');
            }
        }
    }
}

// Load user's tickets
async function loadMyTickets() {
    try {
        const response = await fetch('/api/tickets');
        const data = await response.json();

        if (!data.success) {
            document.getElementById('myTicketsList').innerHTML = `
                <div class="empty-state">
                    <div class="icon">❌</div>
                    <p style="color: red;">${data.error}</p>
                </div>
            `;
            return;
        }

        allMyTickets = data.tickets;
        displayMyTickets(allMyTickets);
        
        // Update badge count
        const openCount = allMyTickets.filter(t => t.status !== 'closed').length;
        document.getElementById('myTicketsCount').textContent = openCount;
        
        // Update notification badges
        updateNotificationBadges();

    } catch (error) {
        console.error('Error loading tickets:', error);
        document.getElementById('myTicketsList').innerHTML = `
            <div class="empty-state">
                <div class="icon">❌</div>
                <p style="color: red;">خطا در بارگذاری تیکت‌ها</p>
            </div>
        `;
    }
}

// Display tickets with new professional design
function displayMyTickets(tickets) {
    const container = document.getElementById('myTicketsList');
    
    if (tickets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3 style="margin-bottom: 10px; color: #1e293b;">هنوز تیکتی ثبت نکرده‌اید</h3>
                <p style="color: #64748b; margin-bottom: 20px;">برای ارتباط با پشتیبانی، یک تیکت جدید ایجاد کنید</p>
                <button class="btn btn-primary" onclick="openNewTicketModal()">
                    ➕ ایجاد تیکت جدید
                </button>
            </div>
        `;
        return;
    }

    // Stats
    const openCount = tickets.filter(t => t.status === 'open').length;
    const waitingCount = tickets.filter(t => t.status === 'waiting').length;
    const unreadCount = tickets.filter(t => hasUnreadMessages(t)).length;

    let html = `
        <div class="ticket-stats">
            <div class="ticket-stat-card">
                <div class="ticket-stat-number">${tickets.length}</div>
                <div class="ticket-stat-label">کل تیکت‌ها</div>
            </div>
            <div class="ticket-stat-card open">
                <div class="ticket-stat-number">${openCount}</div>
                <div class="ticket-stat-label">باز</div>
            </div>
            <div class="ticket-stat-card waiting">
                <div class="ticket-stat-number">${waitingCount}</div>
                <div class="ticket-stat-label">در انتظار پاسخ</div>
            </div>
            <div class="ticket-stat-card unread">
                <div class="ticket-stat-number">${unreadCount}</div>
                <div class="ticket-stat-label">خوانده نشده</div>
            </div>
        </div>
        <div class="tickets-container">
    `;

    html += tickets.map(ticket => {
        const isUnread = hasUnreadMessages(ticket);
        return `
            <div class="ticket-card ${isUnread ? 'unread' : ''}" onclick="openTicketDetail(${ticket.id})">
                <div class="ticket-card-inner">
                    <div class="ticket-header">
                        <div class="ticket-header-right">
                            <span class="ticket-number">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"/>
                                </svg>
                                ${ticket.ticket_number}
                            </span>
                            <div class="ticket-subject">${ticket.subject}</div>
                        </div>
                        <span class="ticket-status ${ticket.status}">${statusNames[ticket.status]}</span>
                    </div>
                    
                    <div class="ticket-footer">
                        <div class="ticket-tags">
                            <span class="ticket-category">${categoryIcons[ticket.category] || '📌'} ${categoryNames[ticket.category]}</span>
                            <span class="ticket-priority ${ticket.priority}">${priorityNames[ticket.priority]}</span>
                        </div>
                        <div class="ticket-meta">
                            <span class="ticket-meta-item">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                                </svg>
                                ${ticket.message_count || 0} پیام
                            </span>
                            <span class="ticket-meta-item">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <path d="M12 6v6l4 2"/>
                                </svg>
                                ${formatDate(ticket.created_at)}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    html += '</div>';
    container.innerHTML = html;
}

// Filter my tickets
function filterMyTickets() {
    const statusFilter = document.getElementById('ticketStatusFilter').value;
    const categoryFilter = document.getElementById('ticketCategoryFilter').value;
    
    let filtered = allMyTickets;
    
    if (statusFilter) {
        filtered = filtered.filter(t => t.status === statusFilter);
    }
    
    if (categoryFilter) {
        filtered = filtered.filter(t => t.category === categoryFilter);
    }
    
    displayMyTickets(filtered);
}

// Load admin tickets
async function loadAdminTickets() {
    try {
        const response = await fetch('/api/tickets');
        const data = await response.json();

        if (!data.success || !data.is_admin) {
            return;
        }

        allAdminTickets = data.tickets;
        displayAdminTickets(allAdminTickets);
        
        // Update badge count
        const openCount = allAdminTickets.filter(t => t.status !== 'closed').length;
        document.getElementById('adminTicketsCount').textContent = openCount;
        
        // Update notification badges
        updateNotificationBadges();

    } catch (error) {
        console.error('Error loading admin tickets:', error);
    }
}

// Display admin tickets with professional design
function displayAdminTickets(tickets) {
    const container = document.getElementById('adminTicketsList');
    
    if (tickets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <p>هیچ تیکتی وجود ندارد</p>
            </div>
        `;
        return;
    }

    // Stats for admin
    const openCount = tickets.filter(t => t.status === 'open').length;
    const waitingCount = tickets.filter(t => t.status === 'waiting').length;
    const urgentCount = tickets.filter(t => t.priority === 'urgent' && t.status !== 'closed').length;

    let html = `
        <div class="ticket-stats">
            <div class="ticket-stat-card">
                <div class="ticket-stat-number">${tickets.length}</div>
                <div class="ticket-stat-label">کل تیکت‌ها</div>
            </div>
            <div class="ticket-stat-card open">
                <div class="ticket-stat-number">${openCount}</div>
                <div class="ticket-stat-label">جدید / باز</div>
            </div>
            <div class="ticket-stat-card waiting">
                <div class="ticket-stat-number">${waitingCount}</div>
                <div class="ticket-stat-label">در انتظار</div>
            </div>
            <div class="ticket-stat-card unread">
                <div class="ticket-stat-number">${urgentCount}</div>
                <div class="ticket-stat-label">فوری</div>
            </div>
        </div>
        <div class="tickets-container">
    `;

    html += tickets.map(ticket => {
        const isUnread = hasUnreadMessages(ticket);
        return `
            <div class="ticket-card ${isUnread ? 'unread' : ''}" onclick="openTicketDetail(${ticket.id})">
                <div class="ticket-card-inner">
                    <div class="ticket-header">
                        <div class="ticket-header-right">
                            <span class="ticket-number">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"/>
                                </svg>
                                ${ticket.ticket_number}
                            </span>
                            <div class="ticket-subject">${ticket.subject}</div>
                            <div style="font-size: 13px; color: #64748b; margin-top: 6px; display: flex; align-items: center; gap: 8px;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                                    <circle cx="12" cy="7" r="4"/>
                                </svg>
                                ${ticket.user_name || 'کاربر'} 
                                <span style="color: #94a3b8;">(${ticket.user_email || '-'})</span>
                            </div>
                        </div>
                        <span class="ticket-status ${ticket.status}">${statusNames[ticket.status]}</span>
                    </div>
                    
                    <div class="ticket-footer">
                        <div class="ticket-tags">
                            <span class="ticket-category">${categoryIcons[ticket.category] || '📌'} ${categoryNames[ticket.category]}</span>
                            <span class="ticket-priority ${ticket.priority}">${priorityNames[ticket.priority]}</span>
                        </div>
                        <div class="ticket-meta">
                            <span class="ticket-meta-item">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                                </svg>
                                ${ticket.message_count || 0} پیام
                            </span>
                            <span class="ticket-meta-item">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <path d="M12 6v6l4 2"/>
                                </svg>
                                ${formatDate(ticket.updated_at)}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    html += '</div>';
    container.innerHTML = html;
}

// Filter admin tickets
function filterAdminTickets() {
    const statusFilter = document.getElementById('adminTicketStatusFilter').value;
    const priorityFilter = document.getElementById('adminTicketPriorityFilter').value;
    
    let filtered = allAdminTickets;
    
    if (statusFilter) {
        filtered = filtered.filter(t => t.status === statusFilter);
    }
    
    if (priorityFilter) {
        filtered = filtered.filter(t => t.priority === priorityFilter);
    }
    
    displayAdminTickets(filtered);
}

// Open new ticket modal
function openNewTicketModal() {
    document.getElementById('ticketModal').style.display = 'block';
    document.getElementById('newTicketForm').reset();
}

// Close ticket modal
function closeTicketModal() {
    document.getElementById('ticketModal').style.display = 'none';
}

// Create new ticket
async function createNewTicket(event) {
    event.preventDefault();
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '⏳ در حال ارسال...';
    submitBtn.disabled = true;
    
    const data = {
        subject: document.getElementById('ticketSubject').value.trim(),
        category: document.getElementById('ticketCategory').value,
        priority: document.getElementById('ticketPriority').value,
        message: document.getElementById('ticketMessage').value.trim()
    };
    
    try {
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show success notification
            showNotification('success', `✅ تیکت با موفقیت ثبت شد!`, `شماره تیکت: ${result.ticket_number}`);
            closeTicketModal();
            loadMyTickets();
        } else {
            showNotification('error', 'خطا', result.error);
        }
    } catch (error) {
        console.error('Error creating ticket:', error);
        showNotification('error', 'خطا', 'خطا در ثبت تیکت');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Show notification toast
function showNotification(type, title, message) {
    const toast = document.createElement('div');
    toast.className = `notification-toast ${type}`;
    toast.innerHTML = `
        <div class="notification-content">
            <strong>${title}</strong>
            <p>${message}</p>
        </div>
    `;
    
    // Add styles if not exists
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification-toast {
                position: fixed;
                top: 90px;
                left: 50%;
                transform: translateX(-50%);
                padding: 16px 24px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                z-index: 10000;
                animation: slideDown 0.3s ease;
            }
            .notification-toast.success {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
            }
            .notification-toast.error {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: white;
            }
            .notification-content strong {
                display: block;
                margin-bottom: 4px;
            }
            .notification-content p {
                margin: 0;
                opacity: 0.9;
                font-size: 14px;
            }
            @keyframes slideDown {
                from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
                to { opacity: 1; transform: translateX(-50%) translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideDown 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Open ticket detail
async function openTicketDetail(ticketId) {
    currentTicketId = ticketId;
    
    // Mark as read
    markTicketAsRead(ticketId);
    
    try {
        const response = await fetch(`/api/tickets/${ticketId}`);
        const data = await response.json();
        
        if (!data.success) {
            showNotification('error', 'خطا', data.error);
            return;
        }
        
        displayTicketDetail(data.ticket, data.messages, data.is_admin);
        document.getElementById('ticketDetailModal').style.display = 'block';
        
    } catch (error) {
        console.error('Error loading ticket:', error);
        showNotification('error', 'خطا', 'خطا در بارگذاری تیکت');
    }
}

// Display ticket detail with chat-style messages
function displayTicketDetail(ticket, messages, isAdmin) {
    document.getElementById('detailTicketNumber').textContent = ticket.ticket_number;
    document.getElementById('detailTicketSubject').textContent = ticket.subject;
    document.getElementById('detailTicketStatus').className = `ticket-status ${ticket.status}`;
    document.getElementById('detailTicketStatus').textContent = statusNames[ticket.status];
    document.getElementById('detailTicketCategory').textContent = `${categoryIcons[ticket.category] || '📌'} ${categoryNames[ticket.category]}`;
    document.getElementById('detailTicketPriority').className = `ticket-priority ${ticket.priority}`;
    document.getElementById('detailTicketPriority').textContent = priorityNames[ticket.priority];
    document.getElementById('detailTicketCreated').textContent = formatDateTime(ticket.created_at);
    
    // Admin controls
    if (isAdmin) {
        document.getElementById('adminControls').style.display = 'flex';
        document.getElementById('adminStatusSelect').value = ticket.status;
        document.getElementById('adminPrioritySelect').value = ticket.priority;
    } else {
        document.getElementById('adminControls').style.display = 'none';
    }
    
    // Messages with chat style
    const messagesContainer = document.getElementById('ticketMessages');
    
    if (messages.length === 0) {
        messagesContainer.innerHTML = '<p style="text-align: center; color: #64748b;">هنوز پیامی وجود ندارد</p>';
    } else {
        messagesContainer.innerHTML = messages.map(msg => `
            <div class="message-item ${msg.is_admin ? 'admin' : ''}">
                <div class="message-header">
                    <span class="message-sender">
                        <span class="message-sender-avatar">
                            ${msg.is_admin ? '👨‍💼' : (msg.sender_name ? msg.sender_name[0].toUpperCase() : '👤')}
                        </span>
                        ${msg.is_admin ? 'پشتیبانی' : (msg.sender_name || 'کاربر')}
                    </span>
                    <span class="message-time">${formatDateTime(msg.created_at)}</span>
                </div>
                <div class="message-body">${escapeHtml(msg.message)}</div>
            </div>
        `).join('');
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close ticket detail
function closeTicketDetail() {
    document.getElementById('ticketDetailModal').style.display = 'none';
    currentTicketId = null;
    
    // Refresh lists to update unread status
    loadMyTickets();
    loadAdminTickets();
}

// Send reply
async function sendTicketReply() {
    const messageInput = document.getElementById('replyMessage');
    const message = messageInput.value.trim();
    
    if (!message) {
        showNotification('error', 'خطا', 'لطفاً پیام خود را بنویسید');
        return;
    }
    
    const sendBtn = document.querySelector('.reply-box .btn-primary');
    const originalText = sendBtn.innerHTML;
    sendBtn.innerHTML = '⏳ در حال ارسال...';
    sendBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/tickets/${currentTicketId}/messages`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message })
        });
        
        const result = await response.json();
        
        if (result.success) {
            messageInput.value = '';
            openTicketDetail(currentTicketId); // Reload
            loadMyTickets();
            loadAdminTickets();
        } else {
            showNotification('error', 'خطا', result.error);
        }
    } catch (error) {
        console.error('Error sending reply:', error);
        showNotification('error', 'خطا', 'خطا در ارسال پیام');
    } finally {
        sendBtn.innerHTML = originalText;
        sendBtn.disabled = false;
    }
}

// Update ticket status (admin)
async function updateTicketStatus() {
    const newStatus = document.getElementById('adminStatusSelect').value;
    
    try {
        const response = await fetch(`/api/tickets/${currentTicketId}/status`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ status: newStatus })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('success', '✅ موفق', 'وضعیت تیکت به‌روزرسانی شد');
            openTicketDetail(currentTicketId); // Reload
            loadAdminTickets();
        } else {
            showNotification('error', 'خطا', result.error);
        }
    } catch (error) {
        console.error('Error updating status:', error);
        showNotification('error', 'خطا', 'خطا در به‌روزرسانی وضعیت');
    }
}

// Update ticket priority (admin)
async function updateTicketPriority() {
    const newPriority = document.getElementById('adminPrioritySelect').value;
    
    try {
        const response = await fetch(`/api/tickets/${currentTicketId}/priority`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ priority: newPriority })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('success', '✅ موفق', 'اولویت تیکت به‌روزرسانی شد');
            openTicketDetail(currentTicketId); // Reload
            loadAdminTickets();
        } else {
            showNotification('error', 'خطا', result.error);
        }
    } catch (error) {
        console.error('Error updating priority:', error);
        showNotification('error', 'خطا', 'خطا در به‌روزرسانی اولویت');
    }
}

// Format date - Relative time
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(hours / 24);
    
    if (minutes < 1) return 'همین الان';
    if (minutes < 60) return `${minutes} دقیقه پیش`;
    if (hours < 24) return `${hours} ساعت پیش`;
    if (days < 7) return `${days} روز پیش`;
    
    return date.toLocaleDateString('fa-IR');
}

// Format date time
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('fa-IR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Auto-refresh tickets every 30 seconds
setInterval(() => {
    if (document.getElementById('section-tickets')?.classList.contains('active')) {
        loadMyTickets();
    }
    if (document.getElementById('section-admin-tickets')?.classList.contains('active')) {
        loadAdminTickets();
    }
}, 30000);
