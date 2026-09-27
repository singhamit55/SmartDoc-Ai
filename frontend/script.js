let authToken = localStorage.getItem('authToken');
let currentChatId = "chat_" + Date.now();

// Global fetch interceptor — auto-logout on any 401 (expired token)
const _originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await _originalFetch.apply(this, args);
    if (response.status === 401 && authToken) {
        // Token expired — clear and force re-login
        localStorage.removeItem('authToken');
        localStorage.removeItem('userName');
        authToken = null;
        // Reload page to show login screen
        location.reload();
    }
    return response;
};

// Restore session on load — validate against an auth-protected endpoint
if (authToken) {
    document.body.classList.add('logged-in');
    fetch('/api/chats', { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(res => {
            if (!res.ok) throw new Error("Token invalid");
            return res.json();
        })
        .then(() => {
            // Token valid — load status info
            return fetch('/api/status').then(r => r.json());
        })
        .then(data => {
            if (data && data.documentCount !== undefined) {
                document.querySelectorAll('.document-count').forEach(el => el.innerText = data.documentCount);
            }
            if (typeof loadChats === 'function' && document.getElementById('chat-history-list')) loadChats();
            if (typeof loadDocuments === 'function' && document.getElementById('docs-list-tbody')) loadDocuments();
            
            const pendingChat = localStorage.getItem('pendingChat');
            if (pendingChat && (window.location.pathname === '/' || window.location.pathname === '/index.html')) {
                localStorage.removeItem('pendingChat');
                // Give the UI a tiny bit of time to settle before opening chat
                setTimeout(() => openChat(pendingChat), 100);
            }
        })
        .catch(() => {
            localStorage.removeItem('authToken');
            authToken = null;
            document.body.classList.remove('logged-in');
        });
}

// Google Identity Callback
function handleCredentialResponse(response) {
    console.log("Encoded JWT ID token: " + response.credential);
    authToken = response.credential;
    localStorage.setItem('authToken', authToken);
    
    const payloadBase64 = response.credential && response.credential.split('.').length === 3
        ? response.credential.split('.')[1]
        : null;
    if (payloadBase64) {
        try {
            const payload = JSON.parse(atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')));
            const userName = payload.name || (payload.email ? payload.email.split('@')[0] : 'User');
            localStorage.setItem('userName', userName);
            updateUserInfo();
        } catch(e) {}
    }
    
    // Switch UI
    document.body.classList.add('logged-in');
    
    // Check backend status
    fetch('/api/status', {
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
    .then(res => res.json())
    .then(data => {
        console.log("Backend Status:", data);
        if (data.documentCount !== undefined) {
            document.querySelectorAll('.document-count').forEach(el => el.innerText = data.documentCount);
        }
        if (typeof loadChats === 'function' && document.getElementById('chat-history-list')) loadChats();
        if (typeof loadDocuments === 'function' && document.getElementById('docs-list-tbody')) loadDocuments();
    })
    .catch(err => console.error("Error connecting to backend:", err));
}


function signOut() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userName');
    authToken = null;
    location.reload();
}

function updateUserInfo() {
    const userName = localStorage.getItem('userName');
    if (userName) {
        document.querySelectorAll('.user-name').forEach(el => el.innerText = userName);
        document.querySelectorAll('.avatar').forEach(el => el.innerText = userName.charAt(0).toUpperCase());
    }
}

// Call on load
updateUserInfo();

/* =========================
   CHAT APP SCRIPTS
========================= */

const input = document.getElementById('messageInput');
const messages = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const fileInput = document.getElementById('fileInput');

async function sendMessage() {
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    if (!authToken) {
        alert("Please login first.");
        return;
    }

    if (welcome) welcome.style.display = 'none';
    if (messages) messages.style.display = 'block';
    
    addMessage(text, 'user');
    input.value = '';
    showTyping();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                message: text,
                chat_id: currentChatId
            })
        });

        removeTyping();

        if (!response.ok) {
            addMessage("Error connecting to backend.", 'ai');
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let aiMessageText = "";
        
        // Add a placeholder message for the AI
        const aiMessageDiv = addMessage("", 'ai', true);
        const bubble = aiMessageDiv.querySelector('.message-bubble');

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            aiMessageText += chunk;
        if (bubble) bubble.innerHTML = typeof marked !== 'undefined'
                ? marked.parse(aiMessageText)
                : escapeHTML(aiMessageText).replace(/\n/g, '<br>');
            scrollChat();
        }
        
        if (document.getElementById('chat-history-list')) loadChats(); // Refresh history sidebar
    } catch (err) {
        removeTyping();
        addMessage("Failed to get response.", 'ai');
        console.error(err);
    }
}

if (input) {
    input.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
}

function addMessage(text, type, returnElement = false) {
    if (!messages) return;
    const message = document.createElement('div');
    message.className = `message ${type === 'user' ? 'user' : ''}`;
    
    message.innerHTML = `
        <div class="message-avatar">
            ${type === 'user' ? 'S' : '🤖'}
        </div>
        <div class="message-bubble">
            ${escapeHTML(text).replace(/\n/g, '<br>')}
        </div>
    `;
    
    messages.appendChild(message);
    scrollChat();
    
    if (returnElement) return message;
}

function showTyping() {
    if (!messages) return;
    const typing = document.createElement('div');
    typing.id = 'typing';
    typing.className = 'message';
    typing.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-bubble">Thinking...</div>
    `;
    messages.appendChild(typing);
    scrollChat();
}

function removeTyping() {
    const typing = document.getElementById('typing');
    if (typing) typing.remove();
}

function quickPrompt(text) {
    if (input) {
        input.value = text;
        sendMessage();
    }
}

function newChat() {
    currentChatId = "chat_" + Date.now();
    if (messages) {
        messages.innerHTML = '';
        messages.style.display = 'none';
    }
    if (welcome) welcome.style.display = 'block';
    if (input) {
        input.value = '';
        input.focus();
    }
}

function attachFile() {
    if(fileInput) fileInput.click();
}

if (fileInput) {
    fileInput.addEventListener('change', async function() {
        const file = this.files[0];
        if (!file) return;
        
        if (!authToken) {
            alert("Please login first.");
            return;
        }

        const MAX_SIZE_MB = 25;
        const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
        const extension = file.name.split('.').pop().toLowerCase();

        if (extension !== 'pdf') {
            alert('Currently only PDF files are supported by the backend.');
            this.value = null;
            return;
        }

        if (file.size > MAX_SIZE_BYTES) {
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
            alert(`File too large! "${file.name}" is ${fileSizeMB} MB.\nMaximum allowed size is ${MAX_SIZE_MB} MB.`);
            this.value = null;
            return;
        }
        
        if (input) {
            input.value = `Uploading ${file.name}...`;
            input.disabled = true;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                },
                body: formData
            });
            
            if (res.ok) {
                if (input) input.value = '';
                alert("Document successfully uploaded and processed by AI!");
                if (document.getElementById('docs-list-tbody')) {
                    loadDocuments();
                }
            } else {
                const errData = await res.json();
                alert(`Upload failed: ${errData.detail}`);
                if (input) input.value = '';
            }
        } catch (err) {
            console.error(err);
            alert("Failed to upload document.");
            if (input) input.value = '';
        } finally {
            if (input) input.disabled = false;
            this.value = null; // reset file input
        }
    });
}


function scrollChat() {
    const chat = document.querySelector('.chat');
    if (chat) chat.scrollTop = chat.scrollHeight;
}

function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* =========================
   DOCUMENTS PAGE
========================= */

async function loadDocuments() {
    const listContainer = document.getElementById('docs-list-tbody');
    if (!listContainer) return;
    listContainer.innerHTML = '<tr><td colspan="6" class="loading-docs" style="text-align:center; padding: 20px;">Loading...</td></tr>';
    
    try {
        const res = await fetch('/api/documents', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        if (!res.ok) throw new Error("Failed to fetch");
        
        const docs = await res.json();
        
        if (docs.length === 0) {
            listContainer.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 20px; color: #64748b; font-size:14px;">No documents found.</td></tr>';
            document.getElementById('stat-pdf').innerText = '0';
            document.getElementById('stat-docx').innerText = '0';
            document.getElementById('stat-xlsx').innerText = '0';
            document.getElementById('stat-txt').innerText = '0';
            document.getElementById('stat-total').innerText = '0';
            document.querySelectorAll('.document-count').forEach(el => el.innerText = '0');
            return;
        }
        
        listContainer.innerHTML = '';
        
        let pdfCount = 0;
        let docxCount = 0;
        let xlsxCount = 0;
        let txtCount = 0;
        
        docs.forEach(doc => {
            const sizeMB = doc.size / (1024 * 1024);
            const sizeStr = sizeMB > 1 ? sizeMB.toFixed(1) + ' MB' : (doc.size / 1024).toFixed(1) + ' KB';
            
            const ext = doc.filename.split('.').pop().toLowerCase();
            let typeColor = '#ef4444';
            let typeLabel = 'PDF';
            let iconClass = 'fa-file-pdf';
            
            if (ext === 'pdf') {
                pdfCount++;
            } else if (ext === 'doc' || ext === 'docx') {
                docxCount++;
                typeColor = '#3b82f6'; typeLabel = 'DOCX'; iconClass = 'fa-file-word';
            } else if (ext === 'xls' || ext === 'xlsx') {
                xlsxCount++;
                typeColor = '#10b981'; typeLabel = 'XLSX'; iconClass = 'fa-file-excel';
            } else if (ext === 'txt') {
                txtCount++;
                typeColor = '#64748b'; typeLabel = 'TXT'; iconClass = 'fa-file-lines';
            } else {
                typeColor = '#64748b'; typeLabel = ext.toUpperCase(); iconClass = 'fa-file';
            }
            
            const dateStr = new Date(doc.uploaded * 1000).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><input type="checkbox"></td>
                <td>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <div style="width:28px; height:28px; background:${typeColor}; color:white; display:flex; align-items:center; justify-content:center; border-radius:6px; font-size:12px;">
                            <i class="fa-solid ${iconClass}"></i>
                        </div>
                        <span class="doc-name" style="font-weight: 500; color:#334155; max-width: 250px;" title="${escapeHTML(doc.filename)}">${escapeHTML(doc.filename)}</span>
                    </div>
                </td>
                <td>
                    <span style="color:${typeColor}; font-weight:600; font-size:11px; background:${typeColor}15; padding:4px 8px; border-radius:4px;">${typeLabel}</span>
                </td>
                <td style="color:#64748b; font-size:13px;">${sizeStr}</td>
                <td style="color:#64748b; font-size:13px;">${dateStr}</td>
                <td>
                    <div style="display:flex; gap:8px;">
                        <button class="action-btn" onclick="window.open('/docs/${encodeURIComponent(doc.filename)}', '_blank')" title="View"><i class="fa-regular fa-eye"></i> View</button>
                        <button class="action-btn delete-btn" style="background-color: #ef4444; color: white; border: none; padding: 8px 10px; border-radius: 6px;" onclick="deleteDocument('${doc.filename.replace(/'/g, "\\'")}')" title="Delete"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </td>
            `;
            listContainer.appendChild(tr);
        });
        
        document.getElementById('stat-pdf').innerText = pdfCount;
        document.getElementById('stat-docx').innerText = docxCount;
        document.getElementById('stat-xlsx').innerText = xlsxCount;
        document.getElementById('stat-txt').innerText = txtCount;
        document.getElementById('stat-total').innerText = docs.length;
        document.querySelectorAll('.document-count').forEach(el => el.innerText = docs.length);
        
    } catch (err) {
        console.error(err);
        listContainer.innerHTML = '<tr><td colspan="6" style="color:red; text-align:center; padding: 20px;">Failed to load documents.</td></tr>';
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    
    try {
        const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (res.ok) {
            loadDocuments(); // Refresh list
        } else {
            alert('Failed to delete document');
        }
    } catch (err) {
        console.error(err);
        alert('Error deleting document');
    }
}

/* =========================
   CHAT HISTORY
========================= */

async function loadChats() {
    if (!authToken) return;
    const historyList = document.getElementById('chat-history-list');
    
    try {
        const res = await fetch('/api/chats', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!res.ok) throw new Error('Failed to fetch chats');
        const chats = await res.json();
        
        historyList.innerHTML = '';
        chats.forEach(chat => {
            const item = document.createElement('div');
            item.className = 'history-item';
            if (chat.id === currentChatId) item.classList.add('active');
            
            item.innerHTML = `
                <div class="history-icon"><i class="fa-solid fa-message" style="font-size: 14px;"></i></div>
                <div class="history-content">
                    <div class="history-title" title="${escapeHTML(chat.title)}">${escapeHTML(chat.title)}</div>
                    <div class="history-time">${new Date(parseInt(chat.id.replace('chat_', ''))).toLocaleString('en-US', {month:'short', day:'numeric', hour:'numeric', minute:'2-digit', hour12:true})}</div>
                </div>
            `;
            item.onclick = () => openChat(chat.id, item);
            historyList.appendChild(item);
        });
    } catch (err) {
        console.error('Error loading chats:', err);
    }
}

async function openChat(chatId, element) {
    // If not on the main chat page, redirect first
    if (window.location.pathname !== '/' && window.location.pathname !== '/index.html') {
        localStorage.setItem('pendingChat', chatId);
        window.location.href = '/';
        return;
    }
    
    if (chatId === currentChatId) return;
    currentChatId = chatId;
    
    // Update active class
    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
    if(element) element.classList.add('active');
    
    // Clear and show messages area
    const messages = document.getElementById('messages');
    const welcome = document.getElementById('welcome');
    if (messages) {
        messages.innerHTML = '';
        messages.style.display = 'block';
    }
    if (welcome) welcome.style.display = 'none';
    
    try {
        const res = await fetch(`/api/chats/${chatId}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!res.ok) throw new Error('Failed to fetch chat messages');
        const chatMessages = await res.json();
        
        chatMessages.forEach(msgPair => {
            // Append User message
            if(msgPair.user) {
                const userMsg = document.createElement('div');
                userMsg.className = 'message user';
                userMsg.innerHTML = `
                    <div class="message-bubble">${escapeHTML(msgPair.user)}</div>
                    <div class="message-avatar">U</div>
                `;
                if (messages) messages.appendChild(userMsg);
            }
            
            // Append AI message
            if(msgPair.ai) {
                const aiMsg = document.createElement('div');
                aiMsg.className = 'message';
                aiMsg.innerHTML = `
                    <div class="message-avatar">🤖</div>
                    <div class="message-bubble markdown-body">${typeof marked !== 'undefined' ? marked.parse(msgPair.ai) : escapeHTML(msgPair.ai)}</div>
                `;
                if (messages) messages.appendChild(aiMsg);
            }
        });
        
        if (messages) scrollChat();
    } catch (err) {
        console.error('Error opening chat:', err);
        const errEl = document.createElement('div');
        errEl.style.color = 'red';
        errEl.style.textAlign = 'center';
        errEl.innerText = 'Failed to load chat history.';
        messages.appendChild(errEl);
    }
}
