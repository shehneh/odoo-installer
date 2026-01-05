// ========================================
// TICKET SYSTEM - JavaScript Functions
// ========================================

let allMyTickets = [];
let allAdminTickets = [];
let currentTicketId = null;

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

// Display tickets
function displayMyTickets(tickets) {
    const container = document.getElementById('myTicketsList');
    
    if (tickets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <p>هنوز تیکتی ثبت نکرده‌اید</p>
                <button class="btn btn-primary" onclick="openNewTicketModal()" style="margin-top: 16px;">➕ ایجاد تیکت جدید</button>
            </div>
        `;
        return;
    }

    container.innerHTML = tickets.map(ticket => `
        <div class="ticket-card" onclick="openTicketDetail(${ticket.id})">
            <div class="ticket-header">
                <div>
                    <div class="ticket-number">${ticket.ticket_number}</div>
                    <div class="ticket-subject">${ticket.subject}</div>
                </div>
                <span class="ticket-status ${ticket.status}">${statusNames[ticket.status]}</span>
            </div>
            <div class="ticket-meta">
                <span class="ticket-category">${categoryNames[ticket.category]}</span>
                <span class="ticket-priority ${ticket.priority}">${priorityNames[ticket.priority]}</span>
                <span>💬 ${ticket.message_count} پیام</span>
                <span>📅 ${formatDate(ticket.created_at)}</span>
            </div>
        </div>
    `).join('');
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

    } catch (error) {
        console.error('Error loading admin tickets:', error);
    }
}

// Display admin tickets
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

    container.innerHTML = tickets.map(ticket => `
        <div class="ticket-card" onclick="openTicketDetail(${ticket.id})">
            <div class="ticket-header">
                <div>
                    <div class="ticket-number">${ticket.ticket_number}</div>
                    <div class="ticket-subject">${ticket.subject}</div>
                    <div style="font-size: 13px; color: #57606a; margin-top: 4px;">
                        👤 ${ticket.user_name} (${ticket.user_email})
                    </div>
                </div>
                <span class="ticket-status ${ticket.status}">${statusNames[ticket.status]}</span>
            </div>
            <div class="ticket-meta">
                <span class="ticket-category">${categoryNames[ticket.category]}</span>
                <span class="ticket-priority ${ticket.priority}">${priorityNames[ticket.priority]}</span>
                <span>💬 ${ticket.message_count} پیام</span>
                <span>📅 ${formatDate(ticket.created_at)}</span>
                <span>🔄 ${formatDate(ticket.updated_at)}</span>
            </div>
        </div>
    `).join('');
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
            alert(`✅ تیکت با موفقیت ثبت شد!\nشماره تیکت: ${result.ticket_number}`);
            closeTicketModal();
            loadMyTickets();
        } else {
            alert('خطا: ' + result.error);
        }
    } catch (error) {
        console.error('Error creating ticket:', error);
        alert('خطا در ثبت تیکت');
    }
}

// Open ticket detail
async function openTicketDetail(ticketId) {
    currentTicketId = ticketId;
    
    try {
        const response = await fetch(`/api/tickets/${ticketId}`);
        const data = await response.json();
        
        if (!data.success) {
            alert('خطا: ' + data.error);
            return;
        }
        
        displayTicketDetail(data.ticket, data.messages, data.is_admin);
        document.getElementById('ticketDetailModal').style.display = 'block';
        
    } catch (error) {
        console.error('Error loading ticket:', error);
        alert('خطا در بارگذاری تیکت');
    }
}

// Display ticket detail
function displayTicketDetail(ticket, messages, isAdmin) {
    document.getElementById('detailTicketNumber').textContent = ticket.ticket_number;
    document.getElementById('detailTicketSubject').textContent = ticket.subject;
    document.getElementById('detailTicketStatus').className = `ticket-status ${ticket.status}`;
    document.getElementById('detailTicketStatus').textContent = statusNames[ticket.status];
    document.getElementById('detailTicketCategory').textContent = categoryNames[ticket.category];
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
    
    // Messages
    const messagesContainer = document.getElementById('ticketMessages');
    messagesContainer.innerHTML = messages.map(msg => `
        <div class="message-item ${msg.is_admin ? 'admin' : ''}">
            <div class="message-header">
                <span class="message-sender">
                    ${msg.is_admin ? '👨‍💼 ' : '👤 '}${msg.sender_name}
                </span>
                <span class="message-time">${formatDateTime(msg.created_at)}</span>
            </div>
            <div class="message-body">${msg.message}</div>
        </div>
    `).join('');
}

// Close ticket detail
function closeTicketDetail() {
    document.getElementById('ticketDetailModal').style.display = 'none';
    currentTicketId = null;
}

// Send reply
async function sendTicketReply() {
    const message = document.getElementById('replyMessage').value.trim();
    
    if (!message) {
        alert('لطفاً پیام خود را بنویسید');
        return;
    }
    
    try {
        const response = await fetch(`/api/tickets/${currentTicketId}/messages`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message })
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('replyMessage').value = '';
            openTicketDetail(currentTicketId); // Reload
            loadMyTickets();
            loadAdminTickets();
        } else {
            alert('خطا: ' + result.error);
        }
    } catch (error) {
        console.error('Error sending reply:', error);
        alert('خطا در ارسال پیام');
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
            openTicketDetail(currentTicketId); // Reload
            loadAdminTickets();
        } else {
            alert('خطا: ' + result.error);
        }
    } catch (error) {
        console.error('Error updating status:', error);
        alert('خطا در به‌روزرسانی وضعیت');
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
            openTicketDetail(currentTicketId); // Reload
            loadAdminTickets();
        } else {
            alert('خطا: ' + result.error);
        }
    } catch (error) {
        console.error('Error updating priority:', error);
        alert('خطا در به‌روزرسانی اولویت');
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(hours / 24);
    
    if (hours < 1) return 'چند دقیقه پیش';
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
