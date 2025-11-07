const $ = (id) => document.getElementById(id);

const authPanel = $("auth");
const chatPanel = $("chat");
const messagesDiv = $("messages");
const usernameInput = $("username");
const passwordInput = $("password");
const authMsg = $("authMsg");

const signupBtn = $("signupBtn");
const loginBtn = $("loginBtn");
const logoutBtn = $("logoutBtn");
const clearBtn = $("clearBtn");
const uploadBtn = $("uploadBtn");
const fileInput = $("fileInput");
const chatInput = $("chatInput");
const sendBtn = $("sendBtn");
const fileList = $("fileList");
const filePreview = $("filePreview");
const previewTitle = $("previewTitle");
const previewContent = $("previewContent");
const closePreview = $("closePreview");
const toggleSummaries = $("toggleSummaries");

let summariesVisible = true;

const API = location.origin + "/api";
let token = localStorage.getItem("token") || "";
let ws;

function showAuth() {
  authPanel.classList.remove("hidden");
  chatPanel.classList.add("hidden");
}

function showChat() {
  authPanel.classList.add("hidden");
  chatPanel.classList.remove("hidden");
  $("sidebar").classList.remove("hidden");
}

async function callAPI(path, method = "GET", body) {
  const headers = {"Content-Type": "application/json"};
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(API + path, {
    method, headers, body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error((await res.json()).detail || ("HTTP "+res.status));
  return res.json();
}

function addMessage(m) {
  const el = document.createElement("div");
  el.className = "message" + (m.is_bot ? " bot" : "");
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${m.username || "unknown"} • ${new Date(m.created_at).toLocaleString()}`;
  const body = document.createElement("div");
  body.textContent = m.content;
  el.appendChild(meta);
  el.appendChild(body);
  messagesDiv.appendChild(el);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function loadMessages() {
  const data = await callAPI("/messages");
  messagesDiv.innerHTML = "";
  for (const m of data.messages) addMessage(m);
}

async function loadFiles() {
  try {
    const data = await callAPI("/files");
    console.log("Files loaded:", data);
    console.log("First file:", data.files[0]);
    fileList.innerHTML = "";
    if (data.files.length === 0) {
      fileList.innerHTML = '<div class="no-files">No files uploaded yet</div>';
    } else {
      for (const file of data.files) {
        const fileEl = document.createElement("div");
        fileEl.className = "message";
        const date = new Date(file.created_at);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        fileEl.innerHTML = `
          <div class="meta">
            <span class="filename">${file.filename}</span> • ${file.username || 'unknown'} • ${dateStr}
          </div>
          <div class="file-buttons">
            <button class="delete-btn" onclick="event.stopPropagation(); deleteFile(${file.id});">Delete</button>
            <button class="view-btn" onclick="openFileInNewWindow(${file.id}, '${file.filename}')">View</button>
          </div>
          <div class="summary" ${summariesVisible ? '' : 'style="display:none"'}>${file.summary || 'No summary available'}</div>
        `;
        fileList.appendChild(fileEl);
      }
    }
  } catch (e) {
    console.error("Failed to load files:", e);
    fileList.innerHTML = '<div class="no-files">Error loading files</div>';
  }
}

function openFileInNewWindow(fileId, filename) {
  const url = `/api/files/${fileId}/download?token=${token}`;
  window.open(url, '_blank');
}

async function deleteFile(fileId) {
  if (!confirm('Delete this file?')) return;
  try {
    await callAPI(`/files/delete/${fileId}`, 'DELETE');
    await loadFiles();
  } catch (e) {
    alert('Failed to delete file: ' + e.message);
  }
}

function connectWS() {
  if (ws) ws.close();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.type === "message") addMessage(data.message);
      if (data.type === "clear") messagesDiv.innerHTML = "";
    } catch (e) {}
  };
  ws.onclose = () => {
    if (token) {
      setTimeout(connectWS, 2000);
    }
  };
}

signupBtn.onclick = async () => {
  try {
    const out = await callAPI("/signup", "POST", {
      username: usernameInput.value.trim(),
      password: passwordInput.value
    });
    token = out.token;
    localStorage.setItem("token", token);
    await loadMessages();
    await loadFiles();
    connectWS();
    showChat();
  } catch (e) {
    authMsg.textContent = e.message;
  }
};

loginBtn.onclick = async () => {
  try {
    const out = await callAPI("/login", "POST", {
      username: usernameInput.value.trim(),
      password: passwordInput.value
    });
    token = out.token;
    localStorage.setItem("token", token);
    await loadMessages();
    await loadFiles();
    connectWS();
    showChat();
  } catch (e) {
    authMsg.textContent = e.message;
  }
};

logoutBtn.onclick = () => {
  token = "";
  localStorage.removeItem("token");
  if (ws) {
    ws.close();
    ws = null;
  }
  $("sidebar").classList.add("hidden");
  showAuth();
};

sendBtn.onclick = async () => {
  const text = chatInput.value.trim();
  if (!text || sendBtn.disabled) return;
  chatInput.value = "";
  sendBtn.disabled = true;
  try {
    await callAPI("/messages", "POST", {content: text});
  } finally {
    sendBtn.disabled = false;
  }
};

clearBtn.onclick = async () => {
  console.log("Clear button clicked");
  if (confirm("Clear all chat history?")) {
    try {
      console.log("Calling clear API...");
      await callAPI("/messages", "DELETE");
      console.log("Clear API successful");
    } catch (e) {
      console.error("Clear failed:", e);
      alert("Failed to clear chat: " + e.message);
    }
  }
};

uploadBtn.onclick = () => {
  fileInput.click();
};

fileInput.onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    
    const response = await fetch(API + '/upload', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token },
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }
    
    const result = await response.json();
    alert(`File uploaded successfully! Processed ${result.chunks} chunks.`);
    await loadFiles();
    
    // Check for summary updates every 3 seconds for 30 seconds
    let checkCount = 0;
    const summaryCheck = setInterval(async () => {
      checkCount++;
      if (checkCount > 10) {
        clearInterval(summaryCheck);
        return;
      }
      await loadFiles();
    }, 3000);
  } catch (e) {
    alert('Upload failed: ' + e.message);
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Upload File';
    fileInput.value = '';
  }
};

closePreview.onclick = () => {
  filePreview.classList.add("hidden");
};

toggleSummaries.onclick = () => {
  summariesVisible = !summariesVisible;
  toggleSummaries.textContent = summariesVisible ? 'Hide Summaries' : 'Show Summaries';
  
  const summaries = document.querySelectorAll('.summary');
  summaries.forEach(summary => {
    summary.style.display = summariesVisible ? 'block' : 'none';
  });
};

if (token) {
  Promise.all([loadMessages(), loadFiles()]).then(()=>{
    connectWS();
    showChat();
  }).catch(()=>showAuth());
} else {
  showAuth();
}
