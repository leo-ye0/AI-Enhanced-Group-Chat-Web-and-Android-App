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
    // try to reconnect after a delay
    setTimeout(connectWS, 2000);
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
  showAuth();
};

sendBtn.onclick = async () => {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  await callAPI("/messages", "POST", {content: text});
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

if (token) {
  loadMessages().then(()=>{
    connectWS();
    showChat();
  }).catch(()=>showAuth());
} else {
  showAuth();
}
