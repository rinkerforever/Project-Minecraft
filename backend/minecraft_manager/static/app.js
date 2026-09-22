const $ = (s) => document.querySelector(s);
const api = { base: localStorage.getItem("blocksmith-url") || "", token: sessionStorage.getItem("blocksmith-token") || "", state: null, filePath: "" };
const toast = (m) => { const n = $("#toast"); n.textContent = m; n.classList.add("show"); setTimeout(() => n.classList.remove("show"), 2800); };
const url = (path) => `${api.base.replace(/\/$/, "")}${path}`;
async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(url(path), { ...options, headers: { Authorization: `Bearer ${api.token}`, ...(options.headers || {}) } });
  } catch (error) {
    throw Error(`${path}: ${error.message}`);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw Error(`${path}: ${body.detail || `Request failed (${response.status})`}`);
  }
  return response;
}
const json = async (path, options) => (await request(path, options)).json();
const bytes = (n) => n == null ? "folder" : n < 1024 ? `${n} B` : `${(n / 1048576).toFixed(1)} MB`;
const args = (value) => value.trim() ? value.trim().split(/\s+/) : [];
const esc = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const duration = (seconds) => { if (seconds == null) return "online"; const hours = Math.floor(seconds / 3600), minutes = Math.floor((seconds % 3600) / 60); return hours ? `${hours}h ${minutes}m online` : `${minutes}m online`; };
const memory = (value) => value == null ? "--" : value < 1073741824 ? `${(value / 1048576).toFixed(0)} MB` : `${(value / 1073741824).toFixed(1)} GB`;

function setConnectionStatus(connected, message = "") {
  const badge = $(".sidebar-status");
  badge.classList.toggle("connected", connected);
  badge.classList.toggle("disconnected", !connected);
  $("#sidebar-status").textContent = connected ? "Manager connected" : "Manager disconnected";
  if (!connected) $("#uptime").textContent = message || "Check the server address and network access";
}

function stateView(state) {
  api.state = state; const status = state.server_status || "stopped";
  $("#health-status").textContent = status; $("#health-profile").textContent = state.active_profile || "None"; $("#profile-caption").textContent = state.active_profile || "No profile selected"; $("#uptime").textContent = state.last_started_at ? `Started ${new Date(state.last_started_at).toLocaleString()}` : "Minecraft server stopped";
  modsView(); settingsView();
}
function playersView(players) { $("#player-count").textContent = `${players.length} online`; $("#player-list").innerHTML = players.length ? players.map((p) => `<div class="player"><span class="avatar"><img src="https://mc-heads.net/avatar/${encodeURIComponent(p.name)}/48" alt="" onerror="this.remove()"><b>${esc(p.name.slice(0,2).toUpperCase())}</b></span><div><strong>${esc(p.name)}</strong><small>${duration(p.online_seconds)}</small></div></div>`).join("") : '<p class="empty">No players currently detected.</p>'; }
function healthView(health) { $("#health-cpu").textContent = health.cpu_percent == null ? "--" : `${health.cpu_percent.toFixed(1)}%`; $("#health-memory").textContent = memory(health.memory_bytes); $("#health-tps").textContent = health.tick_rate == null ? "--" : `${health.tick_rate.toFixed(1)} TPS`; $("#health-source").textContent = health.tick_source; }
function modsView() { const mods = api.state?.mods || []; $("#mod-list").innerHTML = mods.length ? mods.map((m) => `<div class="data-row"><strong>${esc(m.filename)}</strong><span>Uploaded by ${esc(m.uploaded_by)}</span><span>${new Date(m.uploaded_at).toLocaleString()}</span><span>Enabled</span></div>`).join("") : '<p class="empty">No mods uploaded for this profile.</p>'; }
function settingsView() { if (!api.state) return; const picker = $("#settings-profile"), chosen = picker.value || api.state.active_profile; picker.innerHTML = api.state.profiles.map((p) => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join(""); picker.value = chosen || ""; loadProfile(); $("#notes").value = api.state.notes || ""; }
function loadProfile() { const profile = api.state?.profiles.find((p) => p.name === $("#settings-profile").value); if (!profile) return; $("#settings-jar").value = profile.server_jar; $("#settings-directory").value = profile.working_directory; $("#settings-runtime").innerHTML = api.state.java_runtimes.map((r) => `<option value="${r.name}">${r.name} (${r.version})</option>`).join(""); $("#settings-runtime").value = profile.java_runtime; $("#settings-jvm").value = profile.jvm_args.join(" "); $("#settings-server-args").value = profile.server_args.join(" "); $("#settings-mod-directory").value = profile.mod_directory; }
async function refresh(throwOnFailure = false) {
  try {
    const state = await json("/api/server/state");
    const logs = await json("/api/server/logs?lines=500");
    const players = await json("/api/server/players");
    const health = await json("/api/server/health");
    stateView(state);
    setConnectionStatus(true);
    $("#console-log").textContent = logs.lines.join("\n") || "No server output yet.";
    $("#console-log").scrollTop = $("#console-log").scrollHeight;
    playersView(players.players);
    healthView(health);
    if ($("#files-view").classList.contains("active")) files();
    if ($("#backups-view").classList.contains("active")) backups();
    return true;
  } catch (e) {
    setConnectionStatus(false, e.message);
    toast(e.message);
    if (throwOnFailure) throw e;
    return false;
  }
}
async function action(name, body) { try { await json(`/api/server/${name}`, { method:"POST", headers: body ? {"Content-Type":"application/json"} : {}, body: body ? JSON.stringify(body) : undefined }); toast(`Server ${name} requested.`); refresh(); } catch(e) { toast(e.message); } }
async function files(path = api.filePath) { try { const data = await json(`/api/server/files?path=${encodeURIComponent(path)}`); api.filePath = data.path; $("#file-breadcrumb").textContent = `/${data.path}`; $("#file-list").innerHTML = data.items.length ? data.items.map((i) => `<div class="data-row"><button class="file-item" data-path="${esc(i.path)}" data-kind="${esc(i.kind)}">${i.kind === "folder" ? "[folder]" : "[file]"} ${esc(i.name)}</button><span>${bytes(i.size)}</span><span>${new Date(i.modified_at).toLocaleString()}</span><button class="danger delete-file" data-path="${esc(i.path)}" ${i.kind === "folder" ? "hidden" : ""}>Delete</button></div>`).join("") : '<p class="empty">This folder is empty.</p>'; } catch(e) { toast(e.message); } }
async function download(path, backup=false) { try { const r = await request(`${backup ? "/api/server/backups/download?name=" : "/api/server/files/download?path="}${encodeURIComponent(path)}`); const a = document.createElement("a"); a.href = URL.createObjectURL(await r.blob()); a.download = path.split("/").pop(); a.click(); URL.revokeObjectURL(a.href); } catch(e) { toast(e.message); } }
async function backups() { try { const data = await json("/api/server/backups"); $("#backup-list").innerHTML = data.backups.length ? data.backups.map((b) => `<div class="data-row"><strong>${esc(b.name)}</strong><span>${bytes(b.size)}</span><span>${new Date(b.created_at).toLocaleString()}</span><span><button class="backup-download" data-name="${esc(b.name)}">Download</button> <button class="danger backup-delete" data-name="${esc(b.name)}">Delete</button></span></div>`).join("") : '<p class="empty">No backups have been created yet.</p>'; } catch(e) { toast(e.message); } }
function view(name) { document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === name)); document.querySelectorAll(".view").forEach((n) => n.classList.toggle("active", n.id === `${name}-view`)); $("#view-title").textContent = name[0].toUpperCase()+name.slice(1); if(name === "files") files(); if(name === "backups") backups(); }

document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => view(b.dataset.view)));
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = $("#connect-button");
  api.base = $("#server-url").value.trim();
  $("#login-error").textContent = "";
  button.disabled = true;
  button.textContent = "Connecting...";
  try {
    const response = await fetch(url("/api/auth/login"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: $("#username").value, password: $("#password").value }) });
    if (!response.ok) throw Error((await response.json()).detail || "Login failed");
    api.token = (await response.json()).access_token;
    await refresh(true);
    localStorage.setItem("blocksmith-url", api.base);
    sessionStorage.setItem("blocksmith-token", api.token);
    $("#login-dialog").close();
  } catch (err) {
    api.token = "";
    sessionStorage.removeItem("blocksmith-token");
    setConnectionStatus(false, err.message);
    $("#login-error").textContent = err.message;
  } finally {
    button.disabled = false;
    button.textContent = "Connect";
  }
});
$("#refresh-button").onclick = refresh; $("#signout-button").onclick = () => { api.token=""; sessionStorage.removeItem("blocksmith-token"); setConnectionStatus(false, "Sign in to connect"); $("#login-dialog").showModal(); }; $("#send-command").onclick = () => { const value=$("#command-input").value.trim(); if(value) { action("command",{command:value}); $("#command-input").value=""; }}; $("#command-input").onkeydown=(e)=>{if(e.key === "Enter") $("#send-command").click();}; document.querySelectorAll("[data-action]").forEach((b)=>b.onclick=()=>action(b.dataset.action));
$("#files-up").onclick=()=>{api.filePath=api.filePath.split("/").slice(0,-1).join("/");files();}; $("#file-list").onclick=async(e)=>{const item=e.target.closest(".file-item"),del=e.target.closest(".delete-file");if(item){item.dataset.kind==="folder"?files(item.dataset.path):download(item.dataset.path);}if(del&&confirm(`Delete ${del.dataset.path}?`)){try{await json(`/api/server/files?path=${encodeURIComponent(del.dataset.path)}`,{method:"DELETE"});toast("File deleted.");files();}catch(err){toast(err.message);}}};
$("#file-upload").onchange=async(e)=>{const file=e.target.files[0];if(!file)return;const body=new FormData();body.append("directory",api.filePath);body.append("file",file);try{await json("/api/server/files",{method:"POST",body});toast("File uploaded.");files();}catch(err){toast(err.message);}e.target.value="";}; $("#mod-upload").onchange=async(e)=>{const file=e.target.files[0];if(!file)return;const body=new FormData();body.append("file",file);try{await json("/api/server/mods",{method:"POST",body});toast("Mod uploaded.");refresh();}catch(err){toast(err.message);}e.target.value="";};
$("#create-backup").onclick=async()=>{const label=prompt("Backup label (optional):","snapshot");if(label===null)return;try{await json("/api/server/backups",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({label})});toast("Backup created.");backups();}catch(err){toast(err.message);}}; $("#backup-list").onclick=async(e)=>{const down=e.target.closest(".backup-download"),del=e.target.closest(".backup-delete");if(down)download(down.dataset.name,true);if(del&&confirm(`Delete ${del.dataset.name}?`)){try{await json(`/api/server/backups?name=${encodeURIComponent(del.dataset.name)}`,{method:"DELETE"});toast("Backup deleted.");backups();}catch(err){toast(err.message);}}};
$("#settings-profile").onchange=loadProfile; $("#profile-form").onsubmit=async(e)=>{e.preventDefault();const name=$("#settings-profile").value,body={name,server_jar:$("#settings-jar").value,working_directory:$("#settings-directory").value,java_runtime:$("#settings-runtime").value,jvm_args:args($("#settings-jvm").value),server_args:args($("#settings-server-args").value),mod_directory:$("#settings-mod-directory").value};try{await json(`/api/server/profiles/${encodeURIComponent(name)}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});toast("Profile saved.");refresh();}catch(err){toast(err.message);}}; $("#save-notes").onclick=async()=>{try{await json("/api/server/notes",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({notes:$("#notes").value})});toast("Notes saved.");}catch(err){toast(err.message);}};
$("#server-url").value = api.base || window.location.origin;
setConnectionStatus(false, "Sign in to connect");
if(api.token&&api.base)refresh();else $("#login-dialog").showModal();setInterval(()=>{if(api.token)refresh();},12000);
