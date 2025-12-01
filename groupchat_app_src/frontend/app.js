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
  loadCurrentUserProfile();
  loadDecisions();
  loadGroupBrain();
  loadSidebarTasks();
  loadNextMeeting();
  loadProjectPulse();
  loadActiveConflicts();
  loadTeamRoles();
  
  setTimeout(() => {
    if ($("expandMeetings")) {
      $("expandMeetings").onclick = () => {
        meetingsExpanded = !meetingsExpanded;
        $("expandMeetings").textContent = meetingsExpanded ? 'Less' : 'All';
        loadNextMeeting();
      };
    }
    if ($("addMeetingSidebar")) {
      $("addMeetingSidebar").onclick = async () => {
        await populateMeetingAttendees();
        meetingModal.classList.remove('hidden');
      };
    }
    if ($("tasksTab")) {
      $("tasksTab").onclick = () => {
        $("tasksTab").classList.add('active');
        $("archivedTab").classList.remove('active');
        $("decisionsTab").classList.remove('active');
        $("tasksContent").classList.remove('hidden');
        $("archivedContent").classList.add('hidden');
        $("decisionsContent").classList.add('hidden');
      };
    }
    if ($("archivedTab")) {
      $("archivedTab").onclick = () => {
        $("archivedTab").classList.add('active');
        $("tasksTab").classList.remove('active');
        $("decisionsTab").classList.remove('active');
        $("archivedContent").classList.remove('hidden');
        $("tasksContent").classList.add('hidden');
        $("decisionsContent").classList.add('hidden');
        loadArchivedTasks();
      };
    }
    if ($("decisionsTab")) {
      $("decisionsTab").onclick = () => {
        $("decisionsTab").classList.add('active');
        $("tasksTab").classList.remove('active');
        $("archivedTab").classList.remove('active');
        $("decisionsContent").classList.remove('hidden');
        $("tasksContent").classList.add('hidden');
        $("archivedContent").classList.add('hidden');
      };
    }
    if ($("addTaskBtnSidebar")) {
      $("addTaskBtnSidebar").onclick = async () => {
        const sidebarTaskInput = $("sidebarTaskInput");
        if (sidebarTaskInput) {
          // Populate assignee dropdown
          try {
            const usersData = await callAPI('/users');
            const assigneeSelect = $("sidebarNewTaskAssignee");
            if (assigneeSelect) {
              assigneeSelect.innerHTML = '<option value="">Unassigned</option>' +
                usersData.users.map(u => `<option value="${u.username}">${u.username}${u.role ? ' (' + u.role + ')' : ''}</option>`).join('');
            }
          } catch (e) {
            console.error('Failed to load users:', e);
          }
          
          sidebarTaskInput.classList.remove('hidden');
          const input = $("sidebarNewTaskContent");
          if (input) setTimeout(() => input.focus(), 50);
        }
      };
    }
    
    // Sidebar save button - will be overridden by editTaskInline for edit mode
    if ($("sidebarSaveTaskBtn")) {
      $("sidebarSaveTaskBtn").onclick = async () => {
        const input = $("sidebarNewTaskContent");
        const dueDateInput = $("sidebarNewTaskDueDate");
        const assigneeInput = $("sidebarNewTaskAssignee");
        const content = input?.value.trim();
        if (!content) return;
        try {
          const payload = {content};
          if (dueDateInput?.value) payload.due_date = dueDateInput.value;
          if (assigneeInput?.value) payload.assigned_to = assigneeInput.value;
          await callAPI('/tasks', 'POST', payload);
          input.value = '';
          dueDateInput.value = '';
          if (assigneeInput) assigneeInput.value = '';
          $("sidebarTaskInput").classList.add('hidden');
          await loadSidebarTasks();
        } catch (e) {
          alert('Failed to add task: ' + e.message);
        }
      };
    }
    
    if ($("sidebarCancelTaskBtn")) {
      $("sidebarCancelTaskBtn").onclick = () => {
        $("sidebarNewTaskContent").value = '';
        $("sidebarNewTaskDueDate").value = '';
        $("sidebarTaskInput").classList.add('hidden');
        delete window.editingTaskId;
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

async function addMessage(m) {
  const el = document.createElement("div");
  el.className = "message" + (m.is_bot ? " bot" : "");
  const meta = document.createElement("div");
  meta.className = "meta";
  
  // Get user role for display
  let displayName = m.username || "unknown";
  if (!m.is_bot && m.username && m.username !== "unknown") {
    try {
      const usersData = await callAPI('/users');
      const user = usersData.users.find(u => u.username === m.username);
      if (user && user.role) {
        const firstRole = user.role.split(',')[0].trim();
        displayName = `${m.username} (${firstRole})`;
      }
    } catch (e) {
      // Fallback to username only if API call fails
    }
  }
  
  meta.textContent = `${displayName} • ${new Date(m.created_at).toLocaleString()}`;
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
  for (const m of data.messages) await addMessage(m);
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

function autoUnfoldFilesSection() {
  const filesSection = $("groupBrain");
  if (filesSection && filesSection.style.display === 'none') {
    filesSection.style.display = '';
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
      if (data.type === "message") {
        addMessage(data.message);
        if (data.message.content && data.message.content.includes('Your role has been set to:')) {
          loadTeamRoles();
          loadCurrentUserProfile();
        }
      }
      if (data.type === "clear") messagesDiv.innerHTML = "";
      if (data.type === "tasks_updated") {
        console.log('Received tasks_updated event, reloading tasks...');
        loadTasks();
        loadSidebarTasks();
        const tasksSection = $("sidebarTasks");
        if (tasksSection && tasksSection.style.display === 'none') {
          tasksSection.style.display = '';
        }
        if ($("tasksTab") && !$("tasksTab").classList.contains('active')) {
          $("tasksTab").click();
        }
      }
      if (data.type === "meetings_updated") {
        console.log('Received meetings_updated event, reloading meetings...');
        loadMeetings();
        loadNextMeeting();
      }
      if (data.type === "milestones_suggested") {
        window.suggestedMilestones = data.milestones;
        displayMilestoneSuggestionsFromWebSocket(data);
      }
      if (data.type === "milestones_updated") {
        loadProjectPulse();
      }
      if (data.type === "meeting_suggestion") showMeetingSuggestion(data.data);
      if (data.type === "open_meeting_modal") meetingModal.classList.remove('hidden');
      if (data.type === "open_assign_modal") openAssignModal(data.task_id, '');
      if (data.type === "new_conflict") {
        loadActiveConflicts();
        // Auto-unfold decisions section
        const decisionsSection = $("activeConflicts");
        if (decisionsSection && decisionsSection.style.display === 'none') {
          decisionsSection.style.display = '';
        }
        // Switch to decisions tab if on tasks tab
        if ($("decisionsTab") && !$("decisionsTab").classList.contains('active')) {
          $("decisionsTab").click();
        }
      }
      if (data.type === "voting_updated") loadActiveConflicts();
      if (data.type === "decisions_updated") loadDecisions();
      if (data.type === "ship_date_updated") loadProjectPulse();
      if (data.type === "file_summary_updated") {
        loadFiles();
        loadGroupBrain();
      }
      if (data.type === "history_compacted") {
        showNotification(data.message, 'info');
        loadMessages();
      }
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
    localStorage.setItem("username", usernameInput.value.trim());
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
    localStorage.setItem("username", usernameInput.value.trim());
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
    const data = await callAPI("/decision-log");
    const log = $("sidebarDecisions");
    if (!log) return;
    log.innerHTML = "";
    if (data.decisions.length === 0) {
      log.innerHTML = '<div class="no-decisions">No decisions yet</div>';
    } else {
      data.decisions.slice(0, 5).forEach(d => {
        const el = document.createElement("div");
        el.className = "sidebar-decision";
        const icon = d.decision_type === 'locked' ? '🔒' : d.decision_type === 'resolved' ? '⚡' : '🤝';
        const date = new Date(d.created_at).toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
        el.innerHTML = `
          <div style="font-size:10px;color:#9ca3af;margin-bottom:2px">${date}</div>
          <div style="font-weight:600;font-size:11px">${icon} ${d.decision_text}</div>
          <div style="font-size:10px;opacity:0.8;margin-top:2px">${d.rationale.substring(0, 50)}...</div>
        `;
        if (d.chat_reference_id) {
          el.style.cursor = 'pointer';
          el.onclick = () => jumpToMessage(d.chat_reference_id);
        }
        log.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load decisions:", e);
  }
}

function jumpToMessage(messageId) {
  // Scroll to message in chat (simplified implementation)
  const messages = document.querySelectorAll('.message');
  messages.forEach(msg => {
    if (msg.dataset.messageId == messageId) {
      msg.scrollIntoView({behavior: 'smooth', block: 'center'});
      msg.style.backgroundColor = '#1e3a8a';
      setTimeout(() => msg.style.backgroundColor = '', 2000);
    }
  });
}

async function editTaskInline(task, taskElement) {
  // Remove any existing edit forms
  document.querySelectorAll('.inline-task-edit').forEach(el => el.remove());
  
  // Get users for assignee dropdown
  const usersData = await callAPI('/users');
  const users = usersData.users;
  
  // Create inline edit form
  const editForm = document.createElement('div');
  editForm.className = 'inline-task-edit';
  editForm.style.cssText = 'margin:4px 0;padding:8px;background:#f0f9ff;border:1px solid #3b82f6;border-radius:4px';
  editForm.innerHTML = `
    <input id="editTaskContent" value="${task.content}" style="width:100%;padding:4px;border:1px solid #ddd;border-radius:3px;font-size:11px;margin-bottom:4px">
    <input type="date" id="editTaskDueDate" value="${task.due_date || ''}" style="width:100%;padding:4px;border:1px solid #ddd;border-radius:3px;font-size:11px;margin-bottom:4px">
    <select id="editTaskAssignee" style="width:100%;padding:4px;border:1px solid #ddd;border-radius:3px;font-size:11px;margin-bottom:4px">
      <option value="">Unassigned</option>
      ${users.map(u => `<option value="${u.username}" ${task.assigned_to === u.username ? 'selected' : ''}>${u.username}${u.role ? ' (' + u.role + ')' : ''}</option>`).join('')}
    </select>
    <div style="display:flex;gap:4px">
      <button class="toggle-btn" style="flex:1;font-size:10px" onclick="saveTaskEdit(${task.id})">Save</button>
      <button class="toggle-btn" style="flex:1;font-size:10px" onclick="cancelTaskEdit()">Cancel</button>
    </div>
  `;
  
  taskElement.after(editForm);
  editForm.querySelector('#editTaskContent').focus();
}

async function saveTaskEdit(taskId) {
  const content = document.getElementById('editTaskContent').value.trim();
  const dueDate = document.getElementById('editTaskDueDate').value;
  const assignee = document.getElementById('editTaskAssignee').value;
  
  if (!content) return;
  
  try {
    const payload = {content};
    if (dueDate) payload.due_date = dueDate;
    if (assignee) payload.assigned_to = assignee;
    await callAPI(`/tasks/${taskId}`, 'PATCH', payload);
    cancelTaskEdit();
    await loadSidebarTasks();
  } catch (e) {
    alert('Failed to update task: ' + e.message);
  }
}

function cancelTaskEdit() {
  document.querySelectorAll('.inline-task-edit').forEach(el => el.remove());
}

window.acceptTask = async function(taskId) {
  try {
    await callAPI('/messages', 'POST', {content: `accept ${taskId}`});
    await loadSidebarTasks();
  } catch (e) {
    alert('Failed to accept task: ' + e.message);
  }
};

window.declineTask = async function(taskId) {
  try {
    await callAPI('/messages', 'POST', {content: `decline ${taskId}`});
    await loadSidebarTasks();
  } catch (e) {
    alert('Failed to decline task: ' + e.message);
  }
};

window.completeTask = async function(taskId) {
  try {
    await callAPI(`/tasks/${taskId}/complete`, 'POST');
    await loadSidebarTasks();
  } catch (e) {
    alert('Failed to complete task: ' + e.message);
  }
};

window.deleteTask = async function(taskId) {
  if (!confirm('Delete this task?')) return;
  try {
    await callAPI(`/tasks/${taskId}`, 'DELETE');
    await loadSidebarTasks();
  } catch (e) {
    alert('Failed to delete task: ' + e.message);
  }
};

async function loadArchivedTasks() {
  try {
    const [tasksData, usersData] = await Promise.all([callAPI("/tasks"), callAPI("/users")]);
    const tasks = tasksData.tasks.filter(t => t.status === 'completed').slice(0, 10);
    const users = usersData.users;
    const list = $("sidebarArchived");
    if (!list) return;
    list.innerHTML = "";
    if (tasks.length === 0) {
      list.innerHTML = '<div class="no-decisions">No completed tasks</div>';
    } else {
      tasks.forEach(t => {
        const el = document.createElement("div");
        el.className = "sidebar-task";
        el.style.background = "#d1fae5";
        const assignees = t.assigned_to ? t.assigned_to.split(',').map(a => a.trim()) : [];
        const assigneeInfo = assignees.map(username => {
          const user = users.find(u => u.username === username);
          const role = user?.role ? ` (${user.role})` : '';
          return `@${username}${role}`;
        }).join(', ');
        const due = t.due_date ? `<div style="font-size:10px;opacity:0.7;margin-top:2px">📅 ${t.due_date}</div>` : '';
        el.innerHTML = `
          <div style="display:flex;gap:4px;align-items:start">
            <span style="flex-shrink:0">✓</span>
            <div style="flex:1">
              <div style="font-size:11px;text-decoration:line-through;opacity:0.7">${t.content.substring(0, 40)}${t.content.length > 40 ? '...' : ''}</div>
              ${assigneeInfo ? `<div style="font-size:10px;opacity:0.6;margin-top:2px">${assigneeInfo}</div>` : ''}
              ${due}
            </div>
            <button onclick="event.stopPropagation();deleteTask(${t.id})" style="padding:2px 4px;font-size:10px;background:#ef4444;color:white;border:none;border-radius:3px;cursor:pointer" title="Delete">×</button>
          </div>
        `;
        list.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load archived tasks:", e);
  }
}

async function loadSidebarTasks() {
  try {
    const [tasksData, usersData] = await Promise.all([callAPI("/tasks"), callAPI("/users")]);
    const tasks = tasksData.tasks.filter(t => t.status === 'pending').slice(0, 5);
    const users = usersData.users;
    const list = $("sidebarTasks");
    if (!list) return;
    list.innerHTML = "";
    if (tasks.length === 0) {
      list.innerHTML = '<div class="no-decisions">No pending tasks</div>';
    } else {
      tasks.forEach(t => {
        const el = document.createElement("div");
        el.className = "sidebar-task";
        el.style.cursor = "pointer";
        el.onclick = () => {
          // If clicking the same task, cancel edit
          if (el.nextElementSibling?.classList.contains('inline-task-edit')) {
            cancelTaskEdit();
          } else {
            editTaskInline(t, el);
          }
        };
        const assignees = t.assigned_to ? t.assigned_to.split(',').map(a => a.trim()) : [];
        const assigneeInfo = assignees.map(username => {
          const user = users.find(u => u.username === username);
          const role = user?.role ? ` (${user.role})` : '';
          return `@${username}${role}`;
        }).join(', ');
        const due = t.due_date ? `<div style="font-size:10px;opacity:0.7;margin-top:2px">📅 ${t.due_date}</div>` : '';
        const isPending = t.pending_assignment === true;
        const isConfirmed = t.assigned_to && !isPending && t.status === 'pending';
        const isCompleted = t.status === 'completed';
        const isUnassigned = !t.assigned_to && !isPending;
        console.log(`Task ${t.id}: pending=${isPending}, confirmed=${isConfirmed}, completed=${isCompleted}, status=${t.status}, pending_assignment=${t.pending_assignment}`);
        const icon = isPending ? '⏳' : (isCompleted ? '✓' : (isConfirmed ? '🔵' : '⬜'));
        const bgColor = isPending ? '#fef3c7' : (isCompleted ? '#d1fae5' : (isConfirmed ? '#dbeafe' : 'transparent'));
        el.style.background = bgColor;
        el.innerHTML = `
          <div style="display:flex;gap:4px;align-items:start">
            <span style="flex-shrink:0">${icon}</span>
            <div style="flex:1">
              <div style="font-size:11px">${t.content.substring(0, 40)}${t.content.length > 40 ? '...' : ''}</div>
              ${assigneeInfo ? `<div style="font-size:10px;opacity:0.8;margin-top:2px">${assigneeInfo}${isPending ? ' (pending)' : ''}</div>` : ''}
              ${due}
            </div>
            <div style="display:flex;gap:2px;flex-shrink:0">
              ${isPending ? `
                <button onclick="event.stopPropagation();acceptTask(${t.id})" style="padding:2px 4px;font-size:10px;background:#3b82f6;color:white;border:none;border-radius:3px;cursor:pointer" title="Accept">✓</button>
                <button onclick="event.stopPropagation();declineTask(${t.id})" style="padding:2px 4px;font-size:10px;background:#ef4444;color:white;border:none;border-radius:3px;cursor:pointer" title="Decline">×</button>
              ` : `
                <button onclick="event.stopPropagation();completeTask(${t.id})" style="padding:2px 4px;font-size:10px;background:#10b981;color:white;border:none;border-radius:3px;cursor:pointer" title="Complete">✓</button>
                <button onclick="event.stopPropagation();deleteTask(${t.id})" style="padding:2px 4px;font-size:10px;background:#ef4444;color:white;border:none;border-radius:3px;cursor:pointer" title="Delete">×</button>
              `}
            </div>
          </div>
        `;
        list.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load sidebar tasks:", e);
  }
}

let meetingsExpanded = false;
let pulseExpanded = false;

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

async function loadProjectPulse() {
  try {
    const tasks = await callAPI("/tasks");
    const milestonesData = await callAPI("/milestones");
    const shipDateData = await callAPI("/project/ship-date");
    
    if (!milestonesData.milestones || milestonesData.milestones.length === 0) {
      const shipDateHtml = `<input type="date" id="shipDateEdit" value="${shipDateData.ship_date || ''}" onchange="updateShipDate(this.value)" placeholder="Set ship date" style="width:100%;padding:6px;margin-bottom:8px;border:1px solid #374151;border-radius:4px;background:#0b1220;color:#e2e8f0;font-size:11px">`;
      $("projectPulse").innerHTML = `<div class="pulse-content">${shipDateHtml}<div style="display:flex;gap:4px"><button onclick="runProjectAnalyze()" class="toggle-btn" style="flex:1;font-size:10px">📋 Analyze</button><button onclick="generateMilestonesDirectly()" class="toggle-btn" style="flex:1;font-size:10px">✨ Generate</button></div></div>`;
      return;
    }
    
    const milestones = milestonesData.milestones;
    const taskData = tasks.tasks.map(t => ({milestone: milestones[0]?.title || "General", status: t.status}));
    const currentDate = new Date().toISOString().split('T')[0];
    
    const pulse = await callAPI("/project-pulse", "POST", {
      current_date: currentDate,
      milestones: milestones,
      tasks: taskData
    });
    
    const container = $("projectPulse");
    const shipDateHtml = shipDateData.ship_date ? `<div style="font-size:10px;margin-bottom:8px;cursor:pointer" onclick="editShipDate()">📅 Ship: ${shipDateData.ship_date}</div>` : '<input type="date" id="shipDateInput" placeholder="Set ship date" style="width:100%;padding:6px;margin-bottom:8px;border:1px solid #374151;border-radius:4px;background:#0b1220;color:#e2e8f0;font-size:11px">';
    container.innerHTML = `${shipDateHtml}<div style="display:flex;gap:4px;margin-bottom:8px"><button onclick="suggestMilestones()" class="toggle-btn" style="flex:1;font-size:10px">✨ Regenerate</button><button onclick="editMilestones()" class="toggle-btn" style="flex:1;font-size:10px">✏️ Edit</button><button onclick="deleteAllMilestones()" class="toggle-btn" style="flex:1;font-size:10px">🗑️ Clear</button></div>`;
    
    const toShow = pulseExpanded ? pulse.phases : pulse.phases.slice(0, 3);
    toShow.forEach((phase, i) => {
      const statusIcon = phase.status === "ACTIVE" ? "🔵" : phase.status === "COMPLETED" ? "✅" : "⏳";
      const urgencyBg = phase.urgency === "CRITICAL" ? "#fecaca" : phase.urgency === "WARNING" ? "#fed7aa" : "#dbeafe";
      const urgencyIcon = phase.urgency === "CRITICAL" ? "🚨" : phase.urgency === "WARNING" ? "⚠️" : "";
      
      const milestoneIndex = pulseExpanded ? i : i;
      const milestone = milestones[milestoneIndex];
      const card = document.createElement("div");
      card.className = "pulse-content";
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="font-weight:600;font-size:12px">${statusIcon} ${phase.title}</div>
          <div style="display:flex;gap:2px">
            <button onclick="editSingleMilestone(${milestone.id})" class="task-complete" style="padding:2px 4px;font-size:9px">✏️</button>
            <button onclick="deleteMilestone(${milestone.id})" class="task-delete" style="padding:2px 4px;font-size:9px">×</button>
          </div>
        </div>
        <div class="progress-bar"><div class="progress" style="width:${phase.progress}%"></div></div>
        <div style="font-size:11px;margin-top:4px">${phase.progress}% Complete</div>
        ${phase.status === "ACTIVE" ? `<div class="pulse-deadline" style="background:${urgencyBg};color:#374151">${urgencyIcon} ${phase.days_remaining} Days Left</div>` : ''}
      `;
      container.appendChild(card);
    });
    
    if (pulse.phases.length > 3) {
      const expandBtn = document.createElement("button");
      expandBtn.className = "toggle-btn";
      expandBtn.style.cssText = "width:100%;margin-top:8px;font-size:10px";
      expandBtn.textContent = pulseExpanded ? '↑ Show Less' : `↓ Show All (${pulse.phases.length})`;
      expandBtn.onclick = () => {
        pulseExpanded = !pulseExpanded;
        loadProjectPulse();
      };
      container.appendChild(expandBtn);
    }
  } catch (e) {
    console.error("Failed to load project pulse:", e);
    $("projectPulse").innerHTML = '<div class="pulse-content"><button onclick="suggestMilestones()" class="toggle-btn" style="width:100%">✨ AI Suggest Milestones</button></div>';
  }
}

// Suggest milestones with accept/reject UI (for chat-based suggestions)
async function suggestMilestones() {
  try {
    const shipDateInput = $("shipDateInput");
    if (shipDateInput && shipDateInput.value) {
      await callAPI("/project/ship-date", "POST", {ship_date: shipDateInput.value});
    }
    
    $("projectPulse").innerHTML = '<div class="pulse-content">AI generating milestones...</div>';
    const suggestions = await callAPI("/milestones/suggest", "POST");
    
    // Display suggestions with accept/reject UI
    const container = $("projectPulse");
    const shipDateHtml = suggestions.ship_date ? `<div style="font-size:10px;margin-bottom:8px">📅 Ship: ${suggestions.ship_date}</div>` : '';
    container.innerHTML = `${shipDateHtml}<div style="font-size:11px;font-weight:600;margin-bottom:8px">✨ AI Suggested Milestones:</div>`;
    
    // Send to chat (sidebar to chat integration)
    await callAPI('/messages', 'POST', {content: '/milestones'});
    
    suggestions.milestones.forEach((m, i) => {
      const card = document.createElement("div");
      card.className = "pulse-content";
      card.style.background = "#f0fdf4";
      card.style.border = "1px solid #10a37f";
      card.innerHTML = `
        <div style="font-weight:600;font-size:11px;color:#374151">${m.title}</div>
        <div style="font-size:10px;opacity:0.8;color:#6b7280">${m.start_date} → ${m.end_date}</div>
        <div style="font-size:10px;margin-top:4px;color:#6b7280">${m.description}</div>
        <div style="display:flex;gap:4px;margin-top:6px">
          <button onclick="acceptMilestone(${i})" class="toggle-btn" style="flex:1;font-size:10px">✓ Accept</button>
          <button onclick="editMilestone(${i})" class="toggle-btn" style="flex:1;font-size:10px">✏️ Edit</button>
        </div>
      `;
      container.appendChild(card);
    });
    
    const buttonContainer = document.createElement("div");
    buttonContainer.style.cssText = "display:flex;gap:4px;margin-top:8px";
    
    const acceptAll = document.createElement("button");
    acceptAll.className = "toggle-btn";
    acceptAll.style.cssText = "flex:1;font-size:10px";
    acceptAll.textContent = "✓ Accept All";
    acceptAll.onclick = () => acceptAllMilestones(suggestions.milestones);
    
    const rejectAll = document.createElement("button");
    rejectAll.className = "toggle-btn";
    rejectAll.style.cssText = "flex:1;font-size:10px";
    rejectAll.textContent = "× Reject All";
    rejectAll.onclick = () => loadProjectPulse();
    
    buttonContainer.appendChild(acceptAll);
    buttonContainer.appendChild(rejectAll);
    container.appendChild(buttonContainer);
    
    window.suggestedMilestones = suggestions.milestones;
  } catch (e) {
    alert('Failed to suggest milestones: ' + e.message);
    loadProjectPulse();
  }
}

// Handle milestone suggestions from WebSocket (triggered by /milestones command)
function displayMilestoneSuggestionsFromWebSocket(data) {
  const suggestions = data.milestones;
  const shipDate = data.ship_date;
  
  // Display suggestions with accept/reject UI
  const container = $("projectPulse");
  const shipDateHtml = shipDate ? `<div style="font-size:10px;margin-bottom:8px">📅 Ship: ${shipDate}</div>` : '';
  container.innerHTML = `${shipDateHtml}<div style="font-size:11px;font-weight:600;margin-bottom:8px">✨ AI Suggested Milestones:</div>`;
  
  suggestions.forEach((m, i) => {
    const card = document.createElement("div");
    card.className = "pulse-content";
    card.style.background = "#f0fdf4";
    card.style.border = "1px solid #10a37f";
    card.innerHTML = `
      <div style="font-weight:600;font-size:11px;color:#374151">${m.title}</div>
      <div style="font-size:10px;opacity:0.8;color:#6b7280">${m.start_date} → ${m.end_date}</div>
      <div style="font-size:10px;margin-top:4px;color:#6b7280">${m.description || ''}</div>
      <div style="display:flex;gap:4px;margin-top:6px">
        <button onclick="acceptMilestone(${i})" class="toggle-btn" style="flex:1;font-size:10px">✓ Accept</button>
        <button onclick="editMilestone(${i})" class="toggle-btn" style="flex:1;font-size:10px">✏️ Edit</button>
      </div>
    `;
    container.appendChild(card);
  });
  
  const buttonContainer = document.createElement("div");
  buttonContainer.style.cssText = "display:flex;gap:4px;margin-top:8px";
  
  const acceptAll = document.createElement("button");
  acceptAll.className = "toggle-btn";
  acceptAll.style.cssText = "flex:1;font-size:10px";
  acceptAll.textContent = "✓ Accept All";
  acceptAll.onclick = () => acceptAllMilestones(suggestions);
  
  const rejectAll = document.createElement("button");
  rejectAll.className = "toggle-btn";
  rejectAll.style.cssText = "flex:1;font-size:10px";
  rejectAll.textContent = "× Reject All";
  rejectAll.onclick = () => loadProjectPulse();
  
  buttonContainer.appendChild(acceptAll);
  buttonContainer.appendChild(rejectAll);
  container.appendChild(buttonContainer);
  
  window.suggestedMilestones = suggestions;
}

async function acceptMilestone(index) {
  const m = window.suggestedMilestones[index];
  try {
    await callAPI('/milestones', 'POST', {title: m.title, start_date: m.start_date, end_date: m.end_date});
    await callAPI('/messages', 'POST', {content: `Added milestone: ${m.title} (${m.start_date} to ${m.end_date})`});
    await loadProjectPulse();
  } catch (e) {
    alert('Failed to add milestone: ' + e.message);
  }
}

async function acceptAllMilestones(milestones) {
  try {
    await callAPI('/milestones/bulk', 'POST', milestones);
    await callAPI('/messages', 'POST', {content: `Accepted all ${milestones.length} suggested milestones`});
    window.suggestedMilestones = null;
  } catch (e) {
    alert('Failed to add milestones: ' + e.message);
  }
}

let currentMilestoneIndex = null;

function editMilestone(index) {
  const m = window.suggestedMilestones[index];
  currentMilestoneIndex = index;
  window.editingExistingMilestone = false;
  $("milestoneTitle").value = m.title;
  $("milestoneStartDate").value = m.start_date;
  $("milestoneEndDate").value = m.end_date;
  $("milestoneModal").classList.remove('hidden');
}

function closeMilestoneModal() {
  $("milestoneModal").classList.add('hidden');
  currentMilestoneIndex = null;
  window.editingExistingMilestone = false;
}

async function saveMilestoneEdit() {
  if (currentMilestoneIndex !== null) {
    if (window.editingExistingMilestone) {
      // Update existing milestone in database
      await callAPI(`/milestones/${currentMilestoneIndex}`, 'PATCH', {
        title: $("milestoneTitle").value,
        start_date: $("milestoneStartDate").value,
        end_date: $("milestoneEndDate").value
      });
      await loadProjectPulse();
    } else {
      // Update suggested milestone
      window.suggestedMilestones[currentMilestoneIndex].title = $("milestoneTitle").value;
      window.suggestedMilestones[currentMilestoneIndex].start_date = $("milestoneStartDate").value;
      window.suggestedMilestones[currentMilestoneIndex].end_date = $("milestoneEndDate").value;
      suggestMilestones();
    }
    closeMilestoneModal();
  }
}

async function editSingleMilestone(milestoneId) {
  try {
    const data = await callAPI('/milestones');
    const milestone = data.milestones.find(m => m.id === milestoneId);
    if (!milestone) return;
    
    currentMilestoneIndex = milestoneId;
    window.editingExistingMilestone = true;
    $("milestoneTitle").value = milestone.title;
    $("milestoneStartDate").value = milestone.start_date;
    $("milestoneEndDate").value = milestone.end_date;
    $("milestoneModal").classList.remove('hidden');
  } catch (e) {
    alert('Failed to load milestone: ' + e.message);
  }
}

async function editMilestones() {
  try {
    const data = await callAPI('/milestones');
    if (data.milestones.length === 0) {
      suggestMilestones();
      return;
    }
    
    const container = $("projectPulse");
    container.innerHTML = '<div style="font-size:11px;font-weight:600;margin-bottom:8px">✏️ Edit Milestones:</div>';
    
    data.milestones.forEach(m => {
      const card = document.createElement("div");
      card.className = "pulse-content";
      card.style.background = "#f0fdf4";
      card.style.border = "1px solid #10a37f";
      card.innerHTML = `
        <div style="font-weight:600;font-size:11px;color:#374151">${m.title}</div>
        <div style="font-size:10px;opacity:0.8;color:#6b7280">${m.start_date} → ${m.end_date}</div>
        <div style="display:flex;gap:4px;margin-top:6px">
          <button onclick="editSingleMilestone(${m.id})" class="toggle-btn" style="flex:1;font-size:10px">✏️ Edit</button>
          <button onclick="deleteMilestone(${m.id})" class="toggle-btn" style="flex:1;font-size:10px">× Delete</button>
        </div>
      `;
      container.appendChild(card);
    });
    
    const backBtn = document.createElement("button");
    backBtn.className = "toggle-btn";
    backBtn.style.width = "100%";
    backBtn.style.marginTop = "8px";
    backBtn.textContent = "← Back";
    backBtn.onclick = () => loadProjectPulse();
    container.appendChild(backBtn);
  } catch (e) {
    alert('Failed to load milestones: ' + e.message);
  }
}

async function deleteMilestone(milestoneId) {
  if (!confirm('Delete this milestone?')) return;
  try {
    await callAPI(`/milestones/${milestoneId}`, 'DELETE');
    await loadProjectPulse();
  } catch (e) {
    alert('Failed to delete milestone: ' + e.message);
  }
}

async function deleteAllMilestones() {
  $("clearMilestonesModal").classList.remove('hidden');
}

function closeClearMilestonesModal() {
  $("clearMilestonesModal").classList.add('hidden');
}

async function confirmClearMilestones() {
  try {
    const data = await callAPI('/milestones');
    for (const m of data.milestones) {
      await callAPI(`/milestones/${m.id}`, 'DELETE');
    }
    closeClearMilestonesModal();
    await loadProjectPulse();
  } catch (e) {
    alert('Failed to delete milestones: ' + e.message);
  }
}

function editShipDate() {
  const currentDate = $("projectPulse").querySelector('div').textContent.replace('📅 Ship: ', '');
  const newDate = prompt('Enter ship date (YYYY-MM-DD):', currentDate);
  if (newDate && newDate !== currentDate) {
    updateShipDate(newDate);
  }
}

async function updateShipDate(shipDate) {
  try {
    await callAPI('/project/ship-date', 'POST', {ship_date: shipDate});
    await loadProjectPulse();
  } catch (e) {
    alert('Failed to update ship date: ' + e.message);
  }
}

async function runProjectAnalyze() {
  try {
    await callAPI('/messages', 'POST', {content: '/project analyze'});
  } catch (e) {
    alert('Failed to run project analyze: ' + e.message);
  }
}

async function generateMilestonesDirectly() {
  // Make Generate work exactly like Regenerate
  await suggestMilestones();
}

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
  
  // Group Brain file upload
  if ($("brainFileInput")) {
    $("brainFileInput").onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const formData = new FormData();
      formData.append('file', file);
      
      try {
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
        showNotification(`File uploaded to Group Brain! Processed ${result.chunks} chunks.`, 'success');
        await loadGroupBrain();
        await loadFiles();
        autoUnfoldFilesSection();
      } catch (e) {
        showNotification('Upload failed: ' + e.message, 'error');
      } finally {
        $("brainFileInput").value = '';
      }
    };
  }
}, 100);

function showNotification(message, type) {
  const notification = document.createElement('div');
  const bgColor = type === 'success' ? '#10b981' : type === 'info' ? '#3b82f6' : '#ef4444';
  notification.style.cssText = `
    position:fixed;top:20px;right:20px;padding:12px 16px;border-radius:8px;
    color:white;font-size:14px;z-index:10000;max-width:300px;
    background:${bgColor};
    box-shadow:0 4px 12px rgba(0,0,0,0.3);
  `;
  notification.textContent = message;
  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 3000);
}

chatInput.oninput = (e) => {
  const text = e.target.value;
  const lastAtPos = text.lastIndexOf('@');
  const lastSlashPos = text.lastIndexOf('/');
  
  if (lastAtPos !== -1 && lastAtPos === text.length - 1) {
    mentionDropdown.innerHTML = '<div class="mention-item" onclick="insertMention(\'bot\')">@bot</div>';
    mentionDropdown.classList.remove('hidden');
  } else if (lastSlashPos !== -1 && lastSlashPos === text.length - 1) {
    mentionDropdown.innerHTML = '<div class="mention-item" onclick="insertCommand(\'role\')">role [your role]</div><div class="mention-item" onclick="insertCommand(\'assign\')">assign [task]</div><div class="mention-item" onclick="insertCommand(\'project analyze\')">project analyze</div><div class="mention-item" onclick="insertCommand(\'project status\')">project status</div><div class="mention-item" onclick="insertCommand(\'tasks\')">tasks</div><div class="mention-item" onclick="insertCommand(\'schedule\')">schedule</div><div class="mention-item" onclick="insertCommand(\'milestones\')">milestones</div><div class="mention-item" onclick="insertCommand(\'decisions\')">decisions</div><div class="mention-item" onclick="insertCommand(\'vote\')">vote [question]</div>';
    mentionDropdown.classList.remove('hidden');
  } else {
    mentionDropdown.classList.add('hidden');
  }
};

chatInput.onkeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendBtn.click();
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

const sendMessage = async () => {
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

sendBtn.onclick = sendMessage;

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
    autoUnfoldFilesSection();
    
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

if (addTaskBtn) {
  addTaskBtn.onclick = () => {
    taskInput.classList.remove('hidden');
    newTaskContent.focus();
  };
} else {
  console.error('addTaskBtn not found');
}

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
  
  // Milestone modal event handlers
  if ($("closeMilestoneModal")) {
    $("closeMilestoneModal").onclick = closeMilestoneModal;
  }
  if ($("saveMilestoneBtn")) {
    $("saveMilestoneBtn").onclick = saveMilestoneEdit;
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

async function loadActiveConflicts() {
  try {
    const data = await callAPI("/active-conflicts");
    const container = $("activeConflicts");
    if (!container) return;
    
    container.innerHTML = "";
    if (data.conflicts.length === 0) {
      container.innerHTML = '<div class="no-decisions">No active votes</div>';
    } else {
      data.conflicts.forEach(c => {
        const el = document.createElement("div");
        el.className = "conflict-item";
        el.style.cssText = "background:#f9fafb;padding:8px;border-radius:6px;margin-bottom:8px;border-left:3px solid #10a37f;border:1px solid #e5e7eb";
        
        const severityColor = c.severity === 'high' ? '#dc2626' : c.severity === 'medium' ? '#d97706' : '#059669';
        const severityIcon = c.severity === 'high' ? '🔴' : c.severity === 'medium' ? '🟡' : '🟢';
        
        // Check if current user has voted
        const currentUser = localStorage.getItem('username') || 'unknown';
        const userVote = c.user_votes[currentUser];
        const hasVoted = !!userVote;
        
        el.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <div style="font-size:10px;color:#9ca3af">${severityIcon} ${c.conflict_id} • ${c.hours_remaining}h left</div>
            <button onclick="endVote('${c.conflict_id}')" class="task-delete" style="padding:2px 6px;font-size:9px">✓ End</button>
          </div>
          <div style="font-weight:600;font-size:11px;margin-bottom:4px">${c.reason}</div>
          <div style="font-size:10px;opacity:0.8;margin-bottom:6px">Source: ${c.source_file}</div>
          <div style="display:flex;gap:4px;margin-bottom:6px">
            <span style="font-size:10px;background:#f3f4f6;color:#374151;padding:2px 6px;border-radius:3px;border:1px solid #d1d5db">A: ${c.vote_counts.A}</span>
            <span style="font-size:10px;background:#f3f4f6;color:#374151;padding:2px 6px;border-radius:3px;border:1px solid #d1d5db">B: ${c.vote_counts.B}</span>
            <span style="font-size:10px;background:#f3f4f6;color:#374151;padding:2px 6px;border-radius:3px;border:1px solid #d1d5db">C: ${c.vote_counts.C}</span>
          </div>
          ${hasVoted ? 
            `<div style="display:flex;justify-content:space-between;align-items:center">
              <div style="font-size:10px;color:#10b981">✓ You voted: ${userVote}</div>
              <button onclick="openVoteModal('${c.conflict_id}', '${userVote}')" class="toggle-btn" style="padding:2px 6px;font-size:9px">Change</button>
            </div>` :
            `<div style="display:flex;gap:2px">
              <button onclick="openVoteModal('${c.conflict_id}', 'A')" class="vote-btn" style="flex:1;padding:4px;font-size:9px;background:#10a37f;border:none;color:white;border-radius:3px;cursor:pointer">A: Accept</button>
              <button onclick="openVoteModal('${c.conflict_id}', 'B')" class="vote-btn" style="flex:1;padding:4px;font-size:9px;background:#ef4444;border:none;color:white;border-radius:3px;cursor:pointer">B: Deny</button>
              <button onclick="openVoteModal('${c.conflict_id}', 'C')" class="vote-btn" style="flex:1;padding:4px;font-size:9px;background:#f59e0b;border:none;color:white;border-radius:3px;cursor:pointer">C: Modify</button>
            </div>`
          }
        `;
        container.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load active conflicts:", e);
  }
}

let currentVoteConflictId = null;
let currentVoteOption = null;

function openVoteModal(conflictId, option) {
  currentVoteConflictId = conflictId;
  currentVoteOption = option;
  $("voteModalTitle").textContent = `Vote ${option} - ${conflictId}`;
  $("voteReasoning").value = '';
  $("voteModal").classList.remove('hidden');
}

async function endVote(conflictId) {
  if (!confirm('End voting for this conflict? This cannot be undone.')) return;
  try {
    await callAPI(`/conflicts/${conflictId}/end`, 'POST');
    await loadActiveConflicts();
  } catch (e) {
    alert('Failed to end vote: ' + e.message);
  }
}

function closeVoteModal() {
  $("voteModal").classList.add('hidden');
  currentVoteConflictId = null;
  currentVoteOption = null;
}

async function submitVote() {
  const reasoning = $("voteReasoning").value.trim();
  if (!reasoning) {
    alert('Reasoning is required for voting.');
    return;
  }
  
  try {
    await callAPI('/vote', 'POST', {
      conflict_id: currentVoteConflictId,
      option: currentVoteOption,
      reasoning: reasoning
    });
    
    // Also send to chat for transparency
    await callAPI('/messages', 'POST', {
      content: `@bot decision ${currentVoteConflictId} ${currentVoteOption} ${reasoning}`
    });
    
    closeVoteModal();
    await loadActiveConflicts();
  } catch (e) {
    alert('Failed to submit vote: ' + e.message);
  }
}

function startManualVote() {
  $("startVoteQuestion").value = '';
  $("startVoteModal").classList.remove('hidden');
}

function closeStartVoteModal() {
  $("startVoteModal").classList.add('hidden');
}

async function submitStartVote() {
  const question = $("startVoteQuestion").value.trim();
  if (!question) {
    alert('Please enter a question for the vote.');
    return;
  }
  
  try {
    await callAPI('/messages', 'POST', {
      content: `/vote ${question}`
    });
    closeStartVoteModal();
  } catch (e) {
    alert('Failed to start vote: ' + e.message);
  }
}

async function loadCurrentUserProfile() {
  const username = localStorage.getItem('username');
  if (!username) return;
  
  try {
    const data = await callAPI('/users');
    const user = data.users.find(u => u.username === username);
    
    // Set username
    $("currentUsername").textContent = username;
    
    // Load saved avatar or show first letter
    const savedAvatar = localStorage.getItem(`avatar_${username}`);
    if (savedAvatar) {
      $("userAvatar").style.backgroundImage = `url(${savedAvatar})`;
      $("userAvatar").textContent = '';
    } else {
      $("userAvatar").textContent = username.charAt(0).toUpperCase();
    }
    
    // Set role
    if (user && user.role) {
      const firstRole = user.role.split(',')[0].trim();
      $("currentUserRole").textContent = firstRole;
    } else {
      $("currentUserRole").textContent = 'No role set';
    }
  } catch (e) {
    console.error('Failed to load user profile:', e);
  }
}

// Avatar upload handler
if ($("avatarInput")) {
  $("avatarInput").onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      const username = localStorage.getItem('username');
      const imageData = event.target.result;
      localStorage.setItem(`avatar_${username}`, imageData);
      $("userAvatar").style.backgroundImage = `url(${imageData})`;
      $("userAvatar").textContent = '';
    };
    reader.readAsDataURL(file);
  };
}

async function loadTeamRoles() {
  try {
    const data = await callAPI('/users');
    const container = $("teamRoles");
    if (!container) return;
    container.innerHTML = "";
    if (data.users.length === 0) {
      container.innerHTML = '<div class="no-decisions">No team members</div>';
    } else {
      data.users.forEach(u => {
        const el = document.createElement("div");
        el.className = "sidebar-task";
        el.style.background = "transparent";
        const roles = u.role ? u.role.split(',').map(r => r.trim()) : [];
        const rolesBadges = roles.length > 0 ? roles.map(r => `<span style="font-size:9px;background:#3b82f6;color:white;padding:2px 4px;border-radius:3px;margin-right:2px">${r}</span>`).join('') : '<span style="font-size:9px;opacity:0.5">No roles</span>';
        el.innerHTML = `
          <div style="display:flex;gap:4px;align-items:center;justify-content:space-between">
            <div style="flex:1">
              <div style="font-size:11px;font-weight:600">${u.username}</div>
              <div style="margin-top:2px">${rolesBadges}</div>
            </div>
          </div>
        `;
        container.appendChild(el);
      });
    }
  } catch (e) {
    console.error("Failed to load team roles:", e);
  }
}

function editMyRoles() {
  const currentUser = localStorage.getItem('username');
  callAPI('/users').then(data => {
    const user = data.users.find(u => u.username === currentUser);
    $("rolesInput").value = user?.role || '';
    $("editRolesModal").classList.remove('hidden');
  });
}

function closeEditRolesModal() {
  $("editRolesModal").classList.add('hidden');
}

async function saveMyRoles() {
  const roles = $("rolesInput").value.trim();
  try {
    await callAPI('/messages', 'POST', {content: `/role ${roles}`});
    closeEditRolesModal();
    await loadTeamRoles();
  } catch (e) {
    alert('Failed to save roles: ' + e.message);
  }
}

function toggleSection(sectionId) {
  const section = $(sectionId);
  if (section) {
    if (section.style.display === 'none') {
      // Show section - restore original display style
      if (sectionId === 'projectPulse') {
        section.style.display = 'flex';
      } else {
        section.style.display = '';
      }
    } else {
      section.style.display = 'none';
    }
  }
}

async function clearDecisions() {
  if (!confirm('Clear all decisions? This cannot be undone.')) return;
  try {
    await callAPI('/decision-log/clear', 'DELETE');
  } catch (e) {
    alert('Failed to clear decisions: ' + e.message);
  }
}

if (token) {
  Promise.all([loadMessages(), loadFiles(), loadTasks(), loadMeetings(), loadUserFilter()]).then(()=>{
    connectWS();
    showChat();
  }).catch(()=>showAuth());
} else {
  showAuth();
}
