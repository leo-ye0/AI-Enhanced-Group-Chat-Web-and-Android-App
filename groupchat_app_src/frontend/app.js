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
const transcriptInput = $("transcriptInput");
const uploadTranscriptBtn = $("uploadTranscriptBtn");
const botToggle = $("botToggle");
const assignModal = $("assignModal");
const closeAssignModal = $("closeAssignModal");
const userCheckboxes = $("userCheckboxes");
const saveAssignBtn = $("saveAssignBtn");
const dueDateModal = $("dueDateModal");
const closeDueDateModal = $("closeDueDateModal");
const dueDateInput = $("dueDateInput");
const saveDueDateBtn = $("saveDueDateBtn");
const taskSortBy = $("taskSortBy");
const taskFilterUser = $("taskFilterUser");
const taskFilterStatus = $("taskFilterStatus");
const attendeesModal = $("attendeesModal");
const closeAttendeesModal = $("closeAttendeesModal");
const attendeeCheckboxes = $("attendeeCheckboxes");
const saveAttendeesBtn = $("saveAttendeesBtn");
const durationModal = $("durationModal");
const closeDurationModal = $("closeDurationModal");
const durationInput = $("durationInput");
const saveDurationBtn = $("saveDurationBtn");
const zoomLinkModal = $("zoomLinkModal");
const closeZoomLinkModal = $("closeZoomLinkModal");
const zoomLinkInput = $("zoomLinkInput");
const saveZoomLinkBtn = $("saveZoomLinkBtn");
let currentMeetingIdForAttendees = null;
let currentMeetingIdForDuration = null;
let currentMeetingIdForZoomLink = null;

let currentMeetingId = null;
let currentTaskId = null;
let summariesVisible = true;
let botAlwaysOn = localStorage.getItem("botAlwaysOn") === "true";

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
  $("leftNav").classList.remove("hidden");
  $("rightSidebar").classList.remove("hidden");
  loadDecisions();
  loadGroupBrain();
  loadSidebarTasks();
  loadNextMeeting();
  
  setTimeout(() => {
    if ($("expandMeetings")) {
      $("expandMeetings").onclick = () => {
        meetingsExpanded = !meetingsExpanded;
        $("expandMeetings").textContent = meetingsExpanded ? 'Less' : 'All';
        loadNextMeeting();
      };
    }
    if ($("tasksTab")) {
      $("tasksTab").onclick = () => {
        $("tasksTab").classList.add('active');
        $("decisionsTab").classList.remove('active');
        $("tasksContent").classList.remove('hidden');
        $("decisionsContent").classList.add('hidden');
      };
    }
    if ($("decisionsTab")) {
      $("decisionsTab").onclick = () => {
        $("decisionsTab").classList.add('active');
        $("tasksTab").classList.remove('active');
        $("decisionsContent").classList.remove('hidden');
        $("tasksContent").classList.add('hidden');
      };
    }
    if ($("addTaskBtnSidebar")) {
      $("addTaskBtnSidebar").onclick = () => {
        taskInput.classList.remove('hidden');
        newTaskContent.focus();
      };
    }
  }, 100);
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
  body.style.whiteSpace = "pre-wrap";
  if (m.is_bot) {
    body.innerHTML = m.content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');
  } else {
    body.textContent = m.content;
  }
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
    fileList.innerHTML = "";
    if (data.files.length === 0) {
      fileList.innerHTML = '<div class="no-files">No files uploaded yet</div>';
    } else {
      for (const file of data.files) {
        const fileEl = document.createElement("div");
        fileEl.className = "file-item";
        const date = new Date(file.created_at);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        fileEl.innerHTML = `
          <div class="file-name">${file.filename}</div>
          <div class="file-meta">${file.username || 'unknown'} • ${dateStr}</div>
          <div class="file-summary" ${summariesVisible ? '' : 'style="display:none"'}>${file.summary || 'No summary available'}</div>
          <div class="file-actions">
            <button class="task-complete" onclick="openFileInNewWindow(${file.id}, '${file.filename}')">View</button>
            <button class="task-delete" onclick="deleteFile(${file.id})">×</button>
          </div>
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
      if (data.type === "tasks_updated") {
        console.log('Received tasks_updated event, reloading tasks...');
        loadTasks();
        loadSidebarTasks();
      }
      if (data.type === "meetings_updated") {
        console.log('Received meetings_updated event, reloading meetings...');
        loadMeetings();
        loadNextMeeting();
      }
      if (data.type === "meeting_suggestion") showMeetingSuggestion(data.data);
      if (data.type === "open_meeting_modal") meetingModal.classList.remove('hidden');
      if (data.type === "open_assign_modal") openAssignModal(data.task_id, '');
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
  $("leftNav").classList.add("hidden");
  $("rightSidebar").classList.add("hidden");
  showAuth();
};

async function loadDecisions() {
  try {
    const data = await callAPI("/decisions");
    const log = $("sidebarDecisions");
    if (!log) return;
    log.innerHTML = "";
    if (data.decisions.length === 0) {
      log.innerHTML = '<div class="no-decisions">No decisions yet</div>';
    } else {
      data.decisions.slice(0, 5).forEach(d => {
        const el = document.createElement("div");
        el.className = "sidebar-decision";
        el.innerHTML = `<strong>Option ${d.selected_option}</strong><br><small>${d.reasoning.substring(0, 40)}...</small>`;
        log.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load decisions:", e);
  }
}

async function loadSidebarTasks() {
  try {
    const data = await callAPI("/tasks");
    const tasks = data.tasks.filter(t => t.status === 'pending').slice(0, 5);
    const list = $("sidebarTasks");
    if (!list) return;
    list.innerHTML = "";
    if (tasks.length === 0) {
      list.innerHTML = '<div class="no-decisions">No pending tasks</div>';
    } else {
      tasks.forEach(t => {
        const el = document.createElement("div");
        el.className = "sidebar-task";
        const assignees = t.assigned_to ? t.assigned_to.split(',').map(a => `@${a.trim()}`).join(', ') : '';
        const due = t.due_date ? `(Due ${t.due_date})` : '';
        el.innerHTML = `⬜ ${assignees ? assignees + ': ' : ''}${t.content.substring(0, 30)}... ${due}`;
        list.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load sidebar tasks:", e);
  }
}

let meetingsExpanded = false;

async function loadNextMeeting() {
  try {
    const data = await callAPI("/meetings");
    const now = new Date();
    const upcoming = data.meetings.filter(m => new Date(m.datetime) > now).sort((a,b) => new Date(a.datetime) - new Date(b.datetime));
    const container = $("sidebarMeetings");
    if (!container) return;
    container.innerHTML = "";
    if (upcoming.length === 0) {
      container.innerHTML = '<div class="no-decisions">No upcoming meetings</div>';
    } else {
      const toShow = meetingsExpanded ? upcoming : upcoming.slice(0, 3);
      toShow.forEach(m => {
        const el = document.createElement("div");
        el.className = "sidebar-meeting";
        const dt = new Date(m.datetime);
        const day = dt.toLocaleDateString([], {month: 'short', day: 'numeric'});
        const time = dt.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
        const attendeeList = m.attendees ? m.attendees.split(',').map(a => a.trim()) : [];
        const attendees = attendeeList.length > 2 ? `@${attendeeList[0]}, @${attendeeList[1]} +${attendeeList.length - 2}` : attendeeList.map(a => `@${a}`).join(', ');
        el.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:start">
            <div style="flex:1;cursor:pointer" onclick="window.open('${m.zoom_link}', '_blank')">
              <div style="font-weight:600">${m.title}</div>
              <div style="font-size:10px;margin-top:2px">${time} (${day})</div>
              ${attendees ? `<div style="font-size:10px;margin-top:2px;opacity:0.8">${attendees}</div>` : ''}
            </div>
            <div style="display:flex;gap:2px">
              <button class="task-complete" onclick="editMeetingSidebar(${m.id})" style="padding:2px 6px;font-size:10px">✏️</button>
              <button class="task-delete" onclick="deleteMeetingSidebar(${m.id})" style="padding:2px 6px;font-size:10px">×</button>
            </div>
          </div>
        `;
        container.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load meetings:", e);
  }
}

async function editMeetingSidebar(meetingId) {
  try {
    const data = await callAPI("/meetings");
    const meeting = data.meetings.find(m => m.id === meetingId);
    if (!meeting) return;
    await populateMeetingAttendees();
    meetingTitle.value = meeting.title;
    meetingDatetime.value = meeting.datetime;
    meetingDuration.value = meeting.duration_minutes;
    meetingZoomLink.value = meeting.zoom_link;
    const attendeeList = meeting.attendees ? meeting.attendees.split(',').map(a => a.trim()) : [];
    document.querySelectorAll('#meetingAttendeeCheckboxes input[type="checkbox"]').forEach(cb => {
      cb.checked = attendeeList.includes(cb.value);
    });
    updateAttendeeButtonText();
    currentMeetingId = meetingId;
    createMeetingBtn.textContent = 'Update Meeting';
    createMeetingBtn.onclick = async () => {
      if (!confirm('Do you want to save the changes?')) return;
      const selectedAttendees = Array.from(document.querySelectorAll('#meetingAttendeeCheckboxes input[type="checkbox"]:checked')).map(cb => cb.value).join(',');
      await callAPI(`/meetings/${meetingId}/title`, 'PATCH', {title: meetingTitle.value});
      await callAPI(`/meetings/${meetingId}/datetime`, 'PATCH', {datetime: meetingDatetime.value});
      await callAPI(`/meetings/${meetingId}/duration`, 'PATCH', {duration_minutes: parseInt(meetingDuration.value)});
      await callAPI(`/meetings/${meetingId}/zoom-link`, 'PATCH', {zoom_link: meetingZoomLink.value});
      await callAPI(`/meetings/${meetingId}/attendees`, 'PATCH', {usernames: selectedAttendees});
      meetingModal.classList.add('hidden');
      meetingTitle.value = '';
      meetingDatetime.value = '';
      meetingZoomLink.value = '';
      meetingDuration.value = '30';
      createMeetingBtn.textContent = 'Create Meeting';
      currentMeetingId = null;
      await loadMeetings();
      await loadNextMeeting();
    };
    meetingModal.classList.remove('hidden');
  } catch (e) {
    alert('Failed to edit meeting: ' + e.message);
  }
}

async function deleteMeetingSidebar(meetingId) {
  if (!confirm('Delete this meeting?')) return;
  try {
    await callAPI(`/meetings/${meetingId}`, 'DELETE');
    await loadNextMeeting();
    await loadMeetings();
  } catch (e) {
    alert('Failed to delete meeting: ' + e.message);
  }
}

async function populateMeetingAttendees() {
  try {
    const data = await callAPI("/users");
    const container = $("meetingAttendeeCheckboxes");
    if (!container) return;
    container.innerHTML = "";
    data.users.forEach(u => {
      const label = document.createElement("label");
      label.style.cssText = "display:flex;align-items:center;padding:4px 0;gap:6px;cursor:pointer;justify-content:flex-start";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = u.username;
      checkbox.style.cssText = "margin:0;width:auto;flex-shrink:0";
      const span = document.createElement("span");
      span.textContent = u.username;
      span.style.cssText = "font-size:11px;text-align:left";
      label.appendChild(checkbox);
      label.appendChild(span);
      container.appendChild(label);
    });
  } catch (e) {
    console.error("Failed to load users:", e);
  }
}

function updateAttendeeButtonText() {
  const selected = document.querySelectorAll('#meetingAttendeeCheckboxes input[type="checkbox"]:checked');
  const btn = $("attendeeDropdownBtn");
  if (btn) {
    btn.textContent = selected.length > 0 ? `👥 ${selected.length} Selected` : '👥 Select Attendees';
  }
}

let brainSummariesVisible = true;

async function loadGroupBrain() {
  try {
    const data = await callAPI("/files");
    const brain = $("groupBrain");
    brain.innerHTML = "";
    if (data.files.length === 0) {
      brain.innerHTML = '<div class="no-files">No files uploaded</div>';
    } else {
      data.files.forEach(f => {
        const el = document.createElement("div");
        el.className = "brain-file";
        el.style.flexDirection = "column";
        el.style.alignItems = "flex-start";
        el.innerHTML = `
          <div style="display:flex;align-items:center;gap:6px;width:100%">
            <span style="cursor:pointer;flex:1" onclick="openFileInNewWindow(${f.id}, '${f.filename}')">📂 ${f.filename}</span>
            <button class="task-delete" onclick="deleteBrainFile(${f.id})" style="padding:2px 6px;font-size:10px">×</button>
          </div>
          <div class="brain-summary" style="font-size:10px;opacity:0.7;margin-top:4px;line-height:1.3;display:${brainSummariesVisible ? 'block' : 'none'}">${f.summary || 'No summary'}</div>
        `;
        brain.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load group brain:", e);
  }
}

async function deleteBrainFile(fileId) {
  if (!confirm('Delete this file?')) return;
  try {
    await callAPI(`/files/delete/${fileId}`, 'DELETE');
    await loadGroupBrain();
    await loadFiles();
  } catch (e) {
    alert('Failed to delete file: ' + e.message);
  }
}

setTimeout(() => {
  if ($("toggleBrainSummaries")) {
    $("toggleBrainSummaries").onclick = () => {
      brainSummariesVisible = !brainSummariesVisible;
      $("toggleBrainSummaries").textContent = brainSummariesVisible ? 'Hide' : 'Show';
      document.querySelectorAll('.brain-summary').forEach(s => {
        s.style.display = brainSummariesVisible ? 'block' : 'none';
      });
    };
  }
}, 100);

chatInput.oninput = (e) => {
  const text = e.target.value;
  const lastAtPos = text.lastIndexOf('@');
  const lastSlashPos = text.lastIndexOf('/');
  
  if (lastAtPos !== -1 && lastAtPos === text.length - 1) {
    mentionDropdown.innerHTML = '<div class="mention-item" onclick="insertMention(\'bot\')">@bot</div>';
    mentionDropdown.classList.remove('hidden');
  } else if (lastSlashPos !== -1 && lastSlashPos === text.length - 1) {
    mentionDropdown.innerHTML = '<div class="mention-item" onclick="insertCommand(\'project analyze\')">project analyze</div><div class="mention-item" onclick="insertCommand(\'project status\')">project status</div><div class="mention-item" onclick="insertCommand(\'tasks\')">tasks</div><div class="mention-item" onclick="insertCommand(\'assign\')">assign</div><div class="mention-item" onclick="insertCommand(\'schedule\')">schedule</div>';
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

botToggle.onclick = () => {
  botAlwaysOn = !botAlwaysOn;
  localStorage.setItem("botAlwaysOn", botAlwaysOn);
  botToggle.style.opacity = botAlwaysOn ? "1" : "0.4";
  chatInput.placeholder = botAlwaysOn ? "Bot is always listening..." : "Type a message… (use @bot or / for commands)";
};

if (botAlwaysOn) {
  botToggle.style.opacity = "1";
  chatInput.placeholder = "Bot is always listening...";
}

sendBtn.onclick = async () => {
  const text = chatInput.value.trim();
  if (!text || sendBtn.disabled) return;
  chatInput.value = "";
  mentionDropdown.classList.add('hidden');
  sendBtn.disabled = true;
  try {
    const content = botAlwaysOn && !text.startsWith("/") && !text.includes("@bot") ? "@bot " + text : text;
    await callAPI("/messages", "POST", {content});
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
    await loadGroupBrain();
    
    // Check for summary updates every 3 seconds for 30 seconds
    let checkCount = 0;
    const summaryCheck = setInterval(async () => {
      checkCount++;
      if (checkCount > 10) {
        clearInterval(summaryCheck);
        return;
      }
      await loadFiles();
      await loadGroupBrain();
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
  
  const summaries = document.querySelectorAll('.file-summary');
  summaries.forEach(summary => {
    summary.style.display = summariesVisible ? 'block' : 'none';
  });
};

async function loadTasks() {
  try {
    console.log('loadTasks() called');
    const data = await callAPI("/tasks");
    console.log('Received tasks:', data.tasks.length);
    let tasks = data.tasks;
    
    // Filter by status
    const statusFilter = taskFilterStatus.value;
    if (statusFilter !== 'all') {
      tasks = tasks.filter(t => t.status === statusFilter);
    }
    
    // Filter by user
    const userFilter = taskFilterUser.value;
    if (userFilter !== 'all') {
      tasks = tasks.filter(t => t.assigned_to && t.assigned_to.includes(userFilter));
    }
    
    // Sort tasks
    const sortBy = taskSortBy.value;
    if (sortBy === 'due_date') {
      tasks.sort((a, b) => {
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return a.due_date.localeCompare(b.due_date);
      });
    } else if (sortBy === 'status') {
      tasks.sort((a, b) => a.status.localeCompare(b.status));
    }
    
    taskList.innerHTML = "";
    if (tasks.length === 0) {
      taskList.innerHTML = '<div class="no-tasks">No tasks match the filters</div>';
    } else {
      for (const task of tasks) {
        const taskEl = document.createElement("div");
        taskEl.className = "task-item" + (task.status === "completed" ? " completed" : "");
        const assignees = task.assigned_to ? task.assigned_to.split(',').map(u => u.trim()) : [];
        const assignedBadge = assignees.length > 0 ? `<span style="font-size:10px;color:#10b981;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px" onclick="openAssignModal(${task.id}, '${task.assigned_to}')"><span>👤</span><span>${assignees[0]}${assignees.length > 1 ? ` +${assignees.length - 1}` : ''}</span></span>` : `<button class="task-complete" onclick="openAssignModal(${task.id}, '')" style="font-size:10px">Assign</button>`;
        const dueDateBadge = task.due_date ? `<span style="font-size:10px;color:#f59e0b;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px" onclick="setDueDate(${task.id}, '${task.due_date}')"><span>📅</span><span>${task.due_date}</span></span>` : `<span style="font-size:10px;color:#6b7280;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px" onclick="setDueDate(${task.id}, '')"><span>📅</span><span>No date</span></span>`;
        taskEl.innerHTML = `
          <div class="task-content" style="word-wrap:break-word;overflow-wrap:break-word;min-height:40px;display:flex;align-items:center;cursor:pointer" onclick="editTaskContent(${task.id}, this)" title="Click to edit">${task.content}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:4px">
            <div>${assignedBadge}</div>
            <div>${dueDateBadge}</div>
          </div>
          <div style="display:flex;gap:4px;margin-top:4px">
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

async function setDueDate(taskId, currentDueDate) {
  currentTaskId = taskId;
  dueDateInput.value = currentDueDate || '';
  dueDateModal.classList.remove('hidden');
}

closeDueDateModal.onclick = () => {
  dueDateModal.classList.add('hidden');
};

saveDueDateBtn.onclick = async () => {
  try {
    await callAPI(`/tasks/${currentTaskId}/due-date`, 'PATCH', {due_date: dueDateInput.value});
    dueDateModal.classList.add('hidden');
    await loadTasks();
  } catch (e) {
    alert('Failed to set due date: ' + e.message);
  }
};

async function openAssignModal(taskId, currentAssignees) {
  currentTaskId = taskId;
  const data = await callAPI("/users");
  const assignedList = currentAssignees ? currentAssignees.split(',').map(u => u.trim()) : [];
  userCheckboxes.innerHTML = '<div style="display:flex;flex-direction:column;align-items:flex-start">' + data.users.map(u => `
    <label style="display:flex;align-items:center;padding:6px 0;gap:8px;cursor:pointer">
      <input type="checkbox" value="${u.username}" ${assignedList.includes(u.username) ? 'checked' : ''} style="margin:0;width:auto">
      <span>${u.username}</span>
    </label>
  `).join('') + '</div>';
  assignModal.classList.remove('hidden');
}

closeAssignModal.onclick = () => {
  assignModal.classList.add('hidden');
};

saveAssignBtn.onclick = async () => {
  const checked = Array.from(userCheckboxes.querySelectorAll('input:checked')).map(cb => cb.value);
  try {
    await callAPI(`/tasks/${currentTaskId}/assign`, 'PATCH', {usernames: checked.join(',')});
    assignModal.classList.add('hidden');
    await loadTasks();
  } catch (e) {
    alert('Failed to assign task: ' + e.message);
  }
};

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
        const transcriptBadge = meeting.transcript_filename ? `<span style="font-size:10px;color:#10b981">📄 ${meeting.transcript_filename}</span>` : `<button class="task-complete" onclick="uploadTranscript(${meeting.id})" style="font-size:10px">+ Transcript</button>`;
        const attendees = meeting.attendees ? meeting.attendees.split(',').map(u => u.trim()) : [];
        const attendeesBadge = attendees.length > 2 ? `<span style="font-size:10px;color:#10b981;cursor:pointer" onclick="openAttendeesModal(${meeting.id}, '${meeting.attendees}')">👥 ${attendees[0]}, ${attendees[1]} +${attendees.length - 2}</span>` : attendees.length > 0 ? `<span style="font-size:10px;color:#10b981;cursor:pointer" onclick="openAttendeesModal(${meeting.id}, '${meeting.attendees}')">👥 ${attendees.join(', ')}</span>` : `<button class="task-complete" onclick="openAttendeesModal(${meeting.id}, '')" style="font-size:10px">+ Attendees</button>`;
        const durationBadge = `<span style="font-size:10px;color:#f59e0b;cursor:pointer" onclick="setMeetingDuration(${meeting.id}, ${meeting.duration_minutes})">⏱️ ${meeting.duration_minutes}min</span>`;
        meetingEl.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div class="meeting-title" style="cursor:pointer" onclick="editMeetingTitle(${meeting.id}, this)" title="Click to edit">${meeting.title}</div>
            <button class="task-delete" onclick="deleteMeeting(${meeting.id})" style="margin:0">×</button>
          </div>
          <div class="meeting-time" style="cursor:pointer" onclick="editMeetingDatetime(${meeting.id}, '${meeting.datetime}', this)" title="Click to edit">${formattedTime}</div>
          <div style="display:flex;gap:4px;align-items:center">
            <a href="${meeting.zoom_link}" target="_blank" class="meeting-link" style="flex:1">Zoom link</a>
            <button class="task-complete" onclick="updateZoomLink(${meeting.id}, '${meeting.zoom_link.replace(/'/g, "\\'")}')">Update</button>
          </div>
          <div style="margin-top:4px">${durationBadge}</div>
          <div style="margin-top:4px">${transcriptBadge}</div>
          <div style="margin-top:4px">${attendeesBadge}</div>
        `;
        meetingList.appendChild(meetingEl);
      }
    }
  } catch (e) {
    console.error("Failed to load meetings:", e);
  }
}

async function openAttendeesModal(meetingId, currentAttendees) {
  currentMeetingIdForAttendees = meetingId;
  const data = await callAPI("/users");
  const attendeeList = currentAttendees ? currentAttendees.split(',').map(u => u.trim()) : [];
  attendeeCheckboxes.innerHTML = '<div style="display:flex;flex-direction:column;align-items:flex-start">' + data.users.map(u => `
    <label style="display:flex;align-items:center;padding:6px 0;gap:8px;cursor:pointer">
      <input type="checkbox" value="${u.username}" ${attendeeList.includes(u.username) ? 'checked' : ''} style="margin:0;width:auto">
      <span>${u.username}</span>
    </label>
  `).join('') + '</div>';
  attendeesModal.classList.remove('hidden');
}

closeAttendeesModal.onclick = () => {
  attendeesModal.classList.add('hidden');
};

async function setMeetingDuration(meetingId, currentDuration) {
  currentMeetingIdForDuration = meetingId;
  durationInput.value = currentDuration || 60;
  durationModal.classList.remove('hidden');
}

closeDurationModal.onclick = () => {
  durationModal.classList.add('hidden');
};

saveDurationBtn.onclick = async () => {
  try {
    await callAPI(`/meetings/${currentMeetingIdForDuration}/duration`, 'PATCH', {duration_minutes: parseInt(durationInput.value)});
    durationModal.classList.add('hidden');
    await loadMeetings();
  } catch (e) {
    alert('Failed to set duration: ' + e.message);
  }
};

saveAttendeesBtn.onclick = async () => {
  const checked = Array.from(attendeeCheckboxes.querySelectorAll('input:checked')).map(cb => cb.value);
  try {
    await callAPI(`/meetings/${currentMeetingIdForAttendees}/attendees`, 'PATCH', {usernames: checked.join(',')});
    attendeesModal.classList.add('hidden');
    await loadMeetings();
  } catch (e) {
    alert('Failed to set attendees: ' + e.message);
  }
};

function uploadTranscript(meetingId) {
  currentMeetingId = meetingId;
  transcriptInput.click();
}

function showMeetingSuggestion(data) {
  meetingTitle.value = data.title;
  meetingDuration.value = data.duration;
  suggestedTimes.innerHTML = `<div>AI Suggested Times: ${data.suggested_times}</div>`;
  meetingModal.classList.remove('hidden');
}

closeMeetingModal.onclick = () => {
  meetingModal.classList.add('hidden');
  $("meetingAttendeeCheckboxes").classList.add('hidden');
  meetingTitle.value = '';
  meetingDatetime.value = '';
  meetingZoomLink.value = '';
  meetingDuration.value = '30';
  createMeetingBtn.textContent = 'Create Meeting';
  currentMeetingId = null;
};

transcriptInput.onchange = async (e) => {
  const file = e.target.files[0];
  if (!file || !currentMeetingId) return;
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch(API + `/meetings/${currentMeetingId}/transcript`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token },
      body: formData
    });
    
    if (!response.ok) throw new Error('Upload failed');
    
    alert('Transcript uploaded!');
    await loadMeetings();
  } catch (e) {
    alert('Failed to upload transcript: ' + e.message);
  } finally {
    transcriptInput.value = '';
    currentMeetingId = null;
  }
};

addMeetingBtn.onclick = async () => {
  await populateMeetingAttendees();
  meetingModal.classList.remove('hidden');
};

setTimeout(() => {
  const dropdownBtn = $("attendeeDropdownBtn");
  const dropdown = $("meetingAttendeeCheckboxes");
  if (dropdownBtn && dropdown) {
    dropdownBtn.onclick = (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('hidden');
    };
    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target) && e.target !== dropdownBtn) {
        dropdown.classList.add('hidden');
      }
    });
    dropdown.addEventListener('change', updateAttendeeButtonText);
  }
}, 100);

createMeetingBtn.onclick = async () => {
  if (currentMeetingId && createMeetingBtn.textContent === 'Update Meeting') {
    return;
  }
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
    currentMeetingId = result.id;
    
    const selectedAttendees = Array.from($("meetingAttendeeCheckboxes").querySelectorAll('input:checked')).map(cb => cb.value);
    if (selectedAttendees.length > 0) {
      await callAPI(`/meetings/${result.id}/attendees`, 'PATCH', {usernames: selectedAttendees.join(',')});
    }
    
    uploadTranscriptBtn.style.display = 'block';
    createMeetingBtn.textContent = 'Done';
    createMeetingBtn.onclick = () => {
      meetingModal.classList.add('hidden');
      meetingTitle.value = '';
      meetingDatetime.value = '';
      meetingZoomLink.value = '';
      suggestedTimes.innerHTML = '';
      uploadTranscriptBtn.style.display = 'none';
      createMeetingBtn.textContent = 'Create Meeting';
      createMeetingBtn.onclick = arguments.callee.caller;
      currentMeetingId = null;
    };
    await loadMeetings();
    await loadNextMeeting();
  } catch (e) {
    alert('Failed to create meeting: ' + e.message);
  }
};

uploadTranscriptBtn.onclick = () => {
  transcriptInput.click();
};

async function deleteMeeting(meetingId) {
  try {
    await callAPI(`/meetings/${meetingId}`, 'DELETE');
    await loadMeetings();
  } catch (e) {
    alert('Failed to delete meeting: ' + e.message);
  }
}

async function loadUserFilter() {
  try {
    const data = await callAPI("/users");
    taskFilterUser.innerHTML = '<option value="all">All Users</option>' + 
      data.users.map(u => `<option value="${u.username}">${u.username}</option>`).join('');
  } catch (e) {
    console.error("Failed to load users:", e);
  }
}

taskSortBy.onchange = loadTasks;
taskFilterUser.onchange = loadTasks;
taskFilterStatus.onchange = loadTasks;

async function editTaskContent(taskId, element) {
  const currentText = element.textContent;
  const input = document.createElement('input');
  input.type = 'text';
  input.value = currentText;
  input.style.cssText = 'width:100%;padding:4px;border:1px solid #3b82f6;border-radius:4px';
  element.replaceWith(input);
  input.focus();
  input.select();
  
  const save = async () => {
    const newText = input.value.trim();
    if (newText && newText !== currentText) {
      try {
        await callAPI(`/tasks/${taskId}/content`, 'PATCH', {content: newText});
        await loadTasks();
      } catch (e) {
        alert('Failed to update task: ' + e.message);
        await loadTasks();
      }
    } else {
      await loadTasks();
    }
  };
  
  input.onblur = save;
  input.onkeydown = (e) => {
    if (e.key === 'Enter') save();
    if (e.key === 'Escape') loadTasks();
  };
}

async function editMeetingTitle(meetingId, element) {
  const currentText = element.textContent;
  const input = document.createElement('input');
  input.type = 'text';
  input.value = currentText;
  input.style.cssText = 'width:100%;padding:4px;border:1px solid #3b82f6;border-radius:4px;font-weight:600';
  element.replaceWith(input);
  input.focus();
  input.select();
  
  const save = async () => {
    const newText = input.value.trim();
    if (newText && newText !== currentText) {
      try {
        await callAPI(`/meetings/${meetingId}/title`, 'PATCH', {title: newText});
        await loadMeetings();
      } catch (e) {
        alert('Failed to update title: ' + e.message);
        await loadMeetings();
      }
    } else {
      await loadMeetings();
    }
  };
  
  input.onblur = save;
  input.onkeydown = (e) => {
    if (e.key === 'Enter') save();
    if (e.key === 'Escape') loadMeetings();
  };
}

async function editMeetingDatetime(meetingId, currentDatetime, element) {
  const input = document.createElement('input');
  input.type = 'datetime-local';
  input.value = currentDatetime;
  input.style.cssText = 'width:100%;padding:4px;border:1px solid #3b82f6;border-radius:4px';
  element.replaceWith(input);
  input.focus();
  
  const save = async () => {
    const newDatetime = input.value;
    if (newDatetime && newDatetime !== currentDatetime) {
      try {
        await callAPI(`/meetings/${meetingId}/datetime`, 'PATCH', {datetime: newDatetime});
        await loadMeetings();
      } catch (e) {
        alert('Failed to update datetime: ' + e.message);
        await loadMeetings();
      }
    } else {
      await loadMeetings();
    }
  };
  
  input.onblur = save;
  input.onkeydown = (e) => {
    if (e.key === 'Enter') save();
    if (e.key === 'Escape') loadMeetings();
  };
}

async function updateZoomLink(meetingId, currentLink) {
  currentMeetingIdForZoomLink = meetingId;
  zoomLinkInput.value = currentLink || '';
  zoomLinkModal.classList.remove('hidden');
}

closeZoomLinkModal.onclick = () => {
  zoomLinkModal.classList.add('hidden');
};

saveZoomLinkBtn.onclick = async () => {
  try {
    await callAPI(`/meetings/${currentMeetingIdForZoomLink}/zoom-link`, 'PATCH', {zoom_link: zoomLinkInput.value.trim()});
    zoomLinkModal.classList.add('hidden');
    await loadMeetings();
  } catch (e) {
    alert('Failed to update zoom link: ' + e.message);
  }
};

if (token) {
  Promise.all([loadMessages(), loadFiles(), loadTasks(), loadMeetings(), loadUserFilter()]).then(()=>{
    connectWS();
    showChat();
  }).catch(()=>showAuth());
} else {
  showAuth();
}
