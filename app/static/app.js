let token = localStorage.getItem("campus_token") || "";
let me = null;
const $ = (id) => document.getElementById(id);
const authHeaders = () => ({ "Content-Type": "application/json", ...(token ? { "Authorization": `Bearer ${token}` } : {}) });
async function api(path, options={}) {
  const res = await fetch(path, { ...options, headers: { ...authHeaders(), ...(options.headers || {}) } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token) signOut(false);
    throw new Error(data.detail || "Something went wrong.");
  }
  return data;
}
function toast(message) {
  $("toast").textContent = message; $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 2600);
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function showSection(name) {
  document.querySelectorAll(".section").forEach(s => s.classList.add("hidden"));
  $(name)?.classList.remove("hidden");
  document.querySelectorAll(".nav").forEach(b => b.classList.toggle("active", b.dataset.section === name));
  const titles = {overview:"Overview",announcements:"Announcements",requests:"Campus Requests",assistant:"AI Assistant"};
  $("page-title").textContent = titles[name] || "Overview";
}
document.querySelectorAll(".nav").forEach(b => b.addEventListener("click", () => showSection(b.dataset.section)));
document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => showSection(b.dataset.go)));

function renderAnnouncements(items, target) {
  $(target).innerHTML = items.length ? items.map(a => `<article class="announcement"><span class="tag">CAMPUS UPDATE</span><h4>${escapeHtml(a.title)}</h4><p>${escapeHtml(a.body)}</p><div class="meta">Posted by ${escapeHtml(a.author)} · ${escapeHtml(a.created_at)}</div></article>`).join("") : `<div class="panel">No announcements yet.</div>`;
}
async function loadAnnouncements() {
  const items = await api("/api/announcements");
  $("stat-announcements").textContent = items.length;
  renderAnnouncements(items.slice(0, 2), "overview-announcements");
  renderAnnouncements(items, "announcements-list");
}
async function loadUsers() {
  if (!me || me.role !== "admin") return;
  const items = await api("/api/users");
  $("users-list").innerHTML = items.length ? items.map(u => `<article class="task"><div><h4>${escapeHtml(u.name)}</h4><p>@${escapeHtml(u.username)}</p></div><span class="status ${u.role === "admin" ? "closed" : ""}">${escapeHtml(u.role)}</span></article>`).join("") : '<div class="panel">No users found.</div>';
}
async function loadTasks() {
  const items = await api("/api/tasks");
  $("stat-tasks").textContent = items.length;
  $("task-caption").textContent = me.role === "admin" ? "All campus requests." : "Requests you have created.";
  $("tasks-list").innerHTML = items.length ? items.map(t => `<article class="task"><div><h4>${escapeHtml(t.title)}</h4><p>${escapeHtml(t.description)}</p><small>Submitted by ${escapeHtml(t.owner)} · ${escapeHtml(t.created_at)}</small>${t.status !== "Closed" ? `<button class="small-button" data-close="${t.id}">Mark closed</button>` : ""}</div><span class="status ${t.status === "Closed" ? "closed" : ""}">${escapeHtml(t.status)}</span></article>`).join("") : `<div class="panel">No requests yet. Create one above to get started.</div>`;
  document.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", async () => {
    try { await api(`/api/tasks/${b.dataset.close}/close`, {method:"PATCH"}); await loadTasks(); toast("Request marked as closed."); }
    catch(e) { toast(e.message); }
  }));
}
async function enterApp() {
  try { me = await api("/api/me"); }
  catch { signOut(false); return; }
  $("login-panel").classList.add("hidden"); $("app-panel").classList.remove("hidden"); $("logout").classList.remove("hidden");
  $("user-name").textContent = me.name; $("user-role").textContent = me.role; $("avatar").textContent = me.name.charAt(0).toUpperCase(); $("welcome-name").textContent = me.name.split(" ")[0];
  $("announcement-create").classList.toggle("hidden", !["admin","faculty"].includes(me.role));
  $("nav-users").classList.toggle("hidden", me.role !== "admin");
  await Promise.all([loadAnnouncements(), loadTasks(), ...(me.role === "admin" ? [loadUsers()] : [])]);
  showSection("overview");
}
function signOut(callApi=true) {
  const oldToken = token;
  token = ""; me = null; localStorage.removeItem("campus_token");
  if (callApi && oldToken) fetch("/api/logout", {method:"POST",headers:{"Authorization":`Bearer ${oldToken}`}});
  $("app-panel").classList.add("hidden"); $("login-panel").classList.remove("hidden"); $("logout").classList.add("hidden");
}
$("login-form").addEventListener("submit", async e => {
  e.preventDefault(); $("login-error").textContent = "";
  try {
    const data = await api("/api/login", {method:"POST", body:JSON.stringify({username:$("username").value, password:$("password").value})});
    token = data.token; localStorage.setItem("campus_token", token); await enterApp();
  } catch(err) { $("login-error").textContent = err.message; }
});
$("logout").addEventListener("click", () => signOut());
$("user-form").addEventListener("submit", async e => {
  e.preventDefault();
  const button = e.submitter;
  if (button) button.disabled = true;
  try {
    await api("/api/users", {method:"POST",body:JSON.stringify({
      name:$("new-user-name").value.trim(),
      username:$("new-username").value.trim(),
      password:$("new-user-password").value,
      role:$("new-user-role").value
    })});
    e.target.reset();
    await loadUsers();
    toast("Campus account created.");
  } catch(err) {
    toast(err.message);
  } finally {
    if (button) button.disabled = false;
  }
});
$("announcement-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    await api("/api/announcements", {method:"POST",body:JSON.stringify({title:$("announcement-title").value,body:$("announcement-body").value})});
    e.target.reset(); await loadAnnouncements(); toast("Announcement published.");
  } catch(err) { toast(err.message); }
});
$("task-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    await api("/api/tasks", {method:"POST",body:JSON.stringify({title:$("task-title").value,description:$("task-description").value})});
    e.target.reset(); await loadTasks(); toast("Request submitted.");
  } catch(err) { toast(err.message); }
});
function addMessage(text, who) {
  const div = document.createElement("div"); div.className = `message ${who}`; div.textContent = text;
  $("chat-messages").appendChild(div); $("chat-messages").scrollTop = $("chat-messages").scrollHeight;
}
async function ask(question) {
  addMessage(question, "user");
  try { const data = await api("/api/assistant", {method:"POST",body:JSON.stringify({question})}); addMessage(data.answer, "bot"); }
  catch(err) { addMessage(err.message, "bot"); }
}
$("chat-form").addEventListener("submit", async e => {
  e.preventDefault(); const q = $("chat-question").value.trim(); if (!q) return;
  $("chat-question").value = ""; await ask(q);
});
document.querySelectorAll("[data-question]").forEach(b => b.addEventListener("click", () => ask(b.dataset.question)));
if (token) enterApp();
