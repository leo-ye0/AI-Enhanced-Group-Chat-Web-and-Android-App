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
  } catch (e) {
    alert('Upload failed: ' + e.message);
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Upload File';
    fileInput.value = '';
  }
};

if (token) {
  loadMessages().then(()=>{
    connectWS();
    showChat();
  }).catch(()=>showAuth());
} else {
  showAuth();
}
