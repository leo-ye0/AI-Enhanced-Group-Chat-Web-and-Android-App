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
const taskPanel = $("taskPanel");
const taskList = $("taskList");
const mentionDropdown = $("mentionDropdown");
const addTaskBtn = $("addTaskBtn");
const taskInput = $("taskInput");
const newTaskContent = $("newTaskContent");
const saveTaskBtn = $("saveTaskBtn");
const cancelTaskBtn = $("cancelTaskBtn");
const meetingModal = $("meetingModal");
const closeMeetingModal = $("closeMeetingModal");
const meetingTitle = $("meetingTitle");
const meetingDatetime = $("meetingDatetime");
const meetingDuration = $("meetingDuration");
const meetingZoomLink = $("meetingZoomLink");
const suggestedTimes = $("suggestedTimes");
const createMeetingBtn = $("createMeetingBtn");
const meetingPanel = $("meetingPanel");
const meetingList = $("meetingList");
const addMeetingBtn = $("addMeetingBtn");

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
  $("rightColumn").classList.remove("hidden");
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
      if (data.type === "tasks_updated") loadTasks();
      if (data.type === "meetings_updated") loadMeetings();
      if (data.type === "meeting_suggestion") showMeetingSuggestion(data.data);
      if (data.type === "open_meeting_modal") meetingModal.classList.remove('hidden');
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
  $("rightColumn").classList.add("hidden");
  showAuth();
};

chatInput.oninput = (e) => {
  const text = e.target.value;
  const lastAtPos = text.lastIndexOf('@');
  const lastSlashPos = text.lastIndexOf('/');
  
  if (lastAtPos !== -1 && lastAtPos === text.length - 1) {
    mentionDropdown.innerHTML = '<div class="mention-item" onclick="insertMention(\'bot\')">@bot</div>';
    mentionDropdown.classList.remove('hidden');
  } else if (lastSlashPos !== -1 && lastSlashPos === text.length - 1) {
    mentionDropdown.innerHTML = '<div class="mention-item" onclick="insertCommand(\'project analyze\')">project analyze</div><div class="mention-item" onclick="insertCommand(\'project status\')">project status</div><div class="mention-item" onclick="insertCommand(\'tasks\')">tasks</div><div class="mention-item" onclick="insertCommand(\'schedule\')">schedule</div>';
    mentionDropdown.classList.remove('hidden');
  } else {
    mentionDropdown.classList.add('hidden');
  }
};

function insertMention(name) {
  const text = chatInput.value;
  const lastAtPos = text.lastIndexOf('@');
  chatInput.value = text.substring(0, lastAtPos) + '@' + name + ' ';
  mentionDropdown.classList.add('hidden');
  chatInput.focus();
}

function insertCommand(cmd) {
  const text = chatInput.value;
  const lastSlashPos = text.lastIndexOf('/');
  chatInput.value = text.substring(0, lastSlashPos) + '/' + cmd;
  mentionDropdown.classList.add('hidden');
  chatInput.focus();
}

sendBtn.onclick = async () => {
  const text = chatInput.value.trim();
  if (!text || sendBtn.disabled) return;
  chatInput.value = "";
  mentionDropdown.classList.add('hidden');
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

async function loadTasks() {
  try {
    const data = await callAPI("/tasks");
    taskList.innerHTML = "";
    if (data.tasks.length === 0) {
      taskList.innerHTML = '<div class="no-tasks">No tasks yet. AI will auto-detect tasks from your messages!</div>';
    } else {
      for (const task of data.tasks) {
        const taskEl = document.createElement("div");
        taskEl.className = "task-item" + (task.status === "completed" ? " completed" : "");
        taskEl.innerHTML = `
          <div class="task-content">${task.content}</div>
          <div class="task-actions">
            ${task.status === "pending" ? `<button class="task-complete" onclick="completeTask(${task.id})">✓</button>` : ''}
            <button class="task-delete" onclick="deleteTask(${task.id})">×</button>
          </div>
        `;
        taskList.appendChild(taskEl);
      }
    }
  } catch (e) {
    console.error("Failed to load tasks:", e);
  }
}

async function completeTask(taskId) {
  try {
    await callAPI(`/tasks/${taskId}/complete`, 'PATCH');
    await loadTasks();
  } catch (e) {
    alert('Failed to complete task: ' + e.message);
  }
}

async function deleteTask(taskId) {
  try {
    await callAPI(`/tasks/${taskId}`, 'DELETE');
    await loadTasks();
  } catch (e) {
    alert('Failed to delete task: ' + e.message);
  }
}

addTaskBtn.onclick = () => {
  taskInput.classList.remove('hidden');
  newTaskContent.focus();
};

cancelTaskBtn.onclick = () => {
  taskInput.classList.add('hidden');
  newTaskContent.value = '';
};

saveTaskBtn.onclick = async () => {
  const content = newTaskContent.value.trim();
  if (!content) return;
  try {
    await callAPI('/tasks', 'POST', {content});
    taskInput.classList.add('hidden');
    newTaskContent.value = '';
    await loadTasks();
  } catch (e) {
    alert('Failed to add task: ' + e.message);
  }
};

async function loadMeetings() {
  try {
    const data = await callAPI("/meetings");
    meetingList.innerHTML = "";
    if (data.meetings.length === 0) {
      meetingList.innerHTML = '<div class="no-meetings">No meetings scheduled</div>';
    } else {
      for (const meeting of data.meetings) {
        const meetingEl = document.createElement("div");
        meetingEl.className = "meeting-item";
        const formattedTime = meeting.datetime.replace('T', ' ');
        meetingEl.innerHTML = `
          <div class="meeting-title">${meeting.title}</div>
          <div class="meeting-time">${formattedTime} (${meeting.duration_minutes}min)</div>
          <a href="${meeting.zoom_link}" target="_blank" class="meeting-link">Join Zoom</a>
          <button class="task-delete" onclick="deleteMeeting(${meeting.id})">×</button>
        `;
        meetingList.appendChild(meetingEl);
      }
    }
  } catch (e) {
    console.error("Failed to load meetings:", e);
  }
}

function showMeetingSuggestion(data) {
  meetingTitle.value = data.title;
  meetingDuration.value = data.duration;
  suggestedTimes.innerHTML = `<div>AI Suggested Times: ${data.suggested_times}</div>`;
  meetingModal.classList.remove('hidden');
}

closeMeetingModal.onclick = () => {
  meetingModal.classList.add('hidden');
};

addMeetingBtn.onclick = () => {
  meetingModal.classList.remove('hidden');
};

createMeetingBtn.onclick = async () => {
  const title = meetingTitle.value.trim();
  const datetime = meetingDatetime.value;
  const duration = parseInt(meetingDuration.value);
  const zoom_link = meetingZoomLink.value.trim() || null;
  if (!title || !datetime) {
    alert('Please fill in title and time');
    return;
  }
  if (!zoom_link) {
    alert('Please add your Zoom link. Get it from: https://zoom.us/profile');
    return;
  }
  try {
    const result = await callAPI('/meetings', 'POST', {title, datetime, duration_minutes: duration, zoom_link});
    alert('Meeting created!');
    meetingModal.classList.add('hidden');
    meetingTitle.value = '';
    meetingDatetime.value = '';
    meetingZoomLink.value = '';
    suggestedTimes.innerHTML = '';
    await loadMeetings();
  } catch (e) {
    alert('Failed to create meeting: ' + e.message);
  }
};

async function deleteMeeting(meetingId) {
  try {
    await callAPI(`/meetings/${meetingId}`, 'DELETE');
    await loadMeetings();
  } catch (e) {
    alert('Failed to delete meeting: ' + e.message);
  }
}

if (token) {
  Promise.all([loadMessages(), loadFiles(), loadTasks(), loadMeetings()]).then(()=>{
    connectWS();
    showChat();
  }).catch(()=>showAuth());
} else {
  showAuth();
}
