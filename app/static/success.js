(() => {
  const $ = (id) => document.getElementById(id);
  const state = { token: sessionStorage.getItem("successToken") || "", user: null, overview: null, students: [], plan: null };
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const initials = (name) => String(name || "?").split(/\s+/).slice(0,2).map(s => s[0] || "").join("").toUpperCase();
  let toastTimer;
  function toast(message) {
    const node = $("toast"); node.textContent = message; node.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => node.classList.remove("show"), 3000);
  }
  async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (state.token) headers.Authorization = "Bearer " + state.token;
    if (options.body) headers["Content-Type"] = "application/json";
    const response = await fetch(path, { ...options, headers });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 && path !== "/api/login") signOut(false);
      throw new Error(payload.detail || "Something went wrong. Please try again.");
    }
    return payload;
  }
  function setScreen(isLoggedIn) {
    $("login-screen").hidden = isLoggedIn;
    $("app-screen").hidden = !isLoggedIn;
  }
  function setRoleUI() {
    const role = state.user.role;
    const isStudent = role === "student";
    $("students-nav").hidden = isStudent;
    $("view-students-button").hidden = isStudent;
    $("risk-card").querySelector(".metric-top span").textContent = isStudent ? "Your support level" : "Students needing support";
    $("profile-name").textContent = state.user.name;
    $("profile-role").textContent = role.charAt(0).toUpperCase() + role.slice(1);
    $("avatar").textContent = initials(state.user.name);
    $("welcome-title").textContent = "Welcome back, " + state.user.name.split(" ")[0] + ".";
    $("welcome-copy").textContent = isStudent ? "Here is your latest learning snapshot and recommended next step." : "Review your cohort's progress and spot where support may help.";
  }
  async function loadApp() {
    state.overview = await api("/api/analytics/overview");
    state.students = state.overview.students || [];
    setScreen(true); setRoleUI(); renderOverview();
    showView("overview");
  }
  async function signIn(event) {
    event.preventDefault();
    const error = $("login-error"); error.hidden = true;
    const button = $("login-submit"); button.disabled = true; button.textContent = "Signing in…";
    try {
      const result = await api("/api/login", { method:"POST", body:JSON.stringify({ username:$("username").value.trim(), password:$("password").value }) });
      state.token = result.token; state.user = result.user; sessionStorage.setItem("successToken", state.token);
      await loadApp();
    } catch (err) {
      error.textContent = err.message; error.hidden = false;
    } finally { button.disabled = false; button.innerHTML = 'Sign in <span>→</span>'; }
  }
  async function signOut(callApi = true) {
    const token = state.token;
    state.token = ""; state.user = null; state.overview = null; state.students = []; state.plan = null;
    sessionStorage.removeItem("successToken");
    if (callApi && token) { try { await fetch("/api/logout", { method:"POST", headers:{Authorization:"Bearer "+token} }); } catch (_) {} }
    setScreen(false); $("login-form").reset();
  }
  function showView(view) {
    if (view === "students" && state.user?.role === "student") view = "overview";
    document.querySelectorAll(".view").forEach(el => el.hidden = el.id !== "view-" + view);
    document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));
    const title = view === "plan" ? "Study plan" : view === "students" ? "Student records" : "Overview";
    $("page-title").textContent = title; $("crumb").textContent = title;
    if (view === "students") renderStudents();
    if (view === "plan") loadPlan();
  }
  function pct(value) { return Math.max(0, Math.min(100, Number(value) || 0)); }
  function riskClass(risk) { return risk === "High" ? "high" : risk === "Medium" ? "medium" : "low"; }
  function riskLabel(risk) { return risk === "High" ? "High priority" : risk === "Medium" ? "Monitor" : "On track"; }
  function renderOverview() {
    const o = state.overview; if (!o) return;
    $("attendance-value").textContent = o.average_attendance;
    $("marks-value").textContent = o.average_marks;
    $("assignments-value").textContent = o.assignment_completion;
    $("risk-value").textContent = o.high_risk_count;
    $("risk-note").textContent = state.user.role === "student" ? "Based on your current metrics" : "Based on simple demo thresholds";
    $("attendance-note").textContent = state.user.role === "student" ? "Your attendance rate" : "Across tracked students";
    $("attendance-bar").style.width = pct(o.average_attendance) + "%";
    $("marks-bar").style.width = pct(o.average_marks) + "%";
    $("assignments-bar").style.width = pct(o.assignment_completion) + "%";
    const ranked = [...state.students].sort((a,b) => a.average_marks - b.average_marks);
    $("performance-chart").innerHTML = ranked.length ? ranked.map(s => `
      <div class="chart-row"><span class="chart-name" title="${esc(s.full_name)}">${esc(s.full_name.split(" ")[0])}</span><div class="chart-track"><span style="width:${pct(s.average_marks)}%"></span></div><span class="chart-score">${s.average_marks}</span></div>`).join("") : '<p>No performance records yet.</p>';
    const support = [...state.students].filter(s => s.risk !== "Low").sort((a,b) => (a.risk === "High" ? 0 : 1) - (b.risk === "High" ? 0 : 1)).slice(0,4);
    $("support-list").innerHTML = support.length ? support.map(s => `
      <div class="support-item"><div class="support-avatar">${esc(initials(s.full_name))}</div><div class="support-copy"><strong>${esc(s.full_name)}</strong><small>${s.attendance_rate}% attendance · ${s.average_marks} avg marks</small></div><span class="risk-pill ${riskClass(s.risk)}">${esc(riskLabel(s.risk))}</span></div>`).join("") : '<p>Everyone is on track in this snapshot.</p>';
    const cohort = [
      ["Attendance",o.average_attendance,"Average attendance"],
      ["Academic performance",o.average_marks,"Average marks"],
      ["Assignments",o.assignment_completion,"Completion rate"]
    ];
    $("cohort-bars").innerHTML = cohort.map(c => `<div class="cohort-item"><strong>${c[1]}%</strong><span>${c[2]}</span><div class="cohort-track"><i style="width:${pct(c[1])}%"></i></div></div>`).join("");
    $("updated-label").textContent = "Updated " + new Date().toLocaleDateString(undefined,{day:"numeric",month:"short",year:"numeric"});
  }
  function filteredStudents() {
    const q = $("student-search").value.trim().toLowerCase();
    const risk = $("risk-filter").value;
    return state.students.filter(s => (!q || s.full_name.toLowerCase().includes(q) || s.username.toLowerCase().includes(q)) && (risk === "all" || s.risk === risk));
  }
  function renderStudents() {
    const list = filteredStudents();
    $("students-table").innerHTML = list.map(s => `
      <tr><td><div class="student-cell"><span class="student-mini">${esc(initials(s.full_name))}</span><span>${esc(s.full_name)}<small>@${esc(s.username)} · ${esc(s.section)}</small></span></div></td>
      <td>${s.attendance_rate}%</td><td>${s.average_marks}/100</td><td>${s.assignments_done}/${s.assignments_total} (${s.assignment_rate}%)</td>
      <td><span class="risk-pill ${riskClass(s.risk)}">${esc(riskLabel(s.risk))}</span></td><td><button class="table-action" data-edit="${esc(s.username)}">Edit record</button></td></tr>`).join("");
    $("empty-state").hidden = list.length > 0;
    $("students-table").querySelectorAll("[data-edit]").forEach(button => button.addEventListener("click", () => openEditor(button.dataset.edit)));
  }
  function openEditor(username) {
    const s = state.students.find(item => item.username === username); if (!s) return;
    $("editor-panel").hidden = false;
    $("edit-username").value = s.username; $("edit-name").value = s.full_name; $("edit-section").value = s.section;
    $("edit-present").value = s.attendance_present; $("edit-total").value = s.attendance_total;
    $("edit-done").value = s.assignments_done; $("edit-assign-total").value = s.assignments_total;
    $("edit-marks").value = s.marks.join(", ");
    $("editor-panel").scrollIntoView({behavior:"smooth",block:"start"});
  }
  async function saveStudent(event) {
    event.preventDefault();
    const username = $("edit-username").value;
    const marks = $("edit-marks").value.split(",").map(v => Number(v.trim()));
    if (!marks.length || marks.some(v => !Number.isInteger(v) || v < 0 || v > 100)) { toast("Enter marks as comma-separated whole numbers from 0 to 100."); return; }
    const payload = { full_name:$("edit-name").value.trim(), section:$("edit-section").value.trim(),
      attendance_present:Number($("edit-present").value), attendance_total:Number($("edit-total").value),
      assignments_done:Number($("edit-done").value), assignments_total:Number($("edit-assign-total").value), marks };
    if (payload.attendance_present > payload.attendance_total || payload.assignments_done > payload.assignments_total) { toast("Completed counts cannot exceed totals."); return; }
    try {
      await api("/api/analytics/students/" + encodeURIComponent(username), {method:"PUT",body:JSON.stringify(payload)});
      state.overview = await api("/api/analytics/overview"); state.students = state.overview.students || [];
      renderOverview(); renderStudents(); $("editor-panel").hidden = true; toast("Student record saved.");
    } catch (err) { toast(err.message); }
  }
  async function loadPlan() {
    $("study-plan-list").innerHTML = '<div class="loading">Building your plan…</div>';
    try {
      const plan = await api("/api/analytics/study-plan"); state.plan = plan;
      const student = state.students[0] || {};
      $("plan-summary").innerHTML = `
        <span class="summary-chip">Attendance <strong>${student.attendance_rate ?? "—"}%</strong></span>
        <span class="summary-chip">Average marks <strong>${student.average_marks ?? "—"}/100</strong></span>
        <span class="summary-chip">Assignments <strong>${student.assignment_rate ?? "—"}%</strong></span>`;
      $("study-plan-list").innerHTML = plan.tasks.map((t,i) => `
        <article class="plan-card"><div class="plan-number">${String(i+1).padStart(2,"0")}</div><div><span class="risk-pill ${t.priority === "High" ? "high" : t.priority === "Medium" ? "medium" : "low"}">${esc(t.priority)} priority</span><h3>${esc(t.title)}</h3><p>${esc(t.detail)}</p></div></article>`).join("");
    } catch (err) { $("study-plan-list").innerHTML = '<div class="panel"><p>' + esc(err.message) + '</p></div>'; }
  }
  function exportCSV() {
    const rows = [["Username","Name","Section","Attendance %","Average marks","Assignments done","Assignments total","Risk"]];
    filteredStudents().forEach(s => rows.push([s.username,s.full_name,s.section,s.attendance_rate,s.average_marks,s.assignments_done,s.assignments_total,s.risk]));
    const csv = rows.map(row => row.map(cell => '"' + String(cell ?? "").replace(/"/g,'""') + '"').join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8;"}));
    const a = document.createElement("a"); a.href = url; a.download = "student-analytics.csv"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }
  $("login-form").addEventListener("submit", signIn);
  document.querySelectorAll(".demo-account").forEach(button => button.addEventListener("click", () => { $("username").value = button.dataset.user; $("password").value = button.dataset.pass; $("login-error").hidden = true; }));
  document.querySelectorAll(".nav-item").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
  $("logout-button").addEventListener("click", () => signOut(true));
  $("student-search").addEventListener("input", renderStudents);
  $("risk-filter").addEventListener("change", renderStudents);
  $("export-button").addEventListener("click", exportCSV);
  $("student-editor").addEventListener("submit", saveStudent);
  $("close-editor").addEventListener("click", () => $("editor-panel").hidden = true);
  $("cancel-editor").addEventListener("click", () => $("editor-panel").hidden = true);
  $("view-students-button").addEventListener("click", () => showView("students"));
  if (state.token) {
    api("/api/me").then(user => { state.user = user; return loadApp(); }).catch(() => signOut(false));
  }
})();