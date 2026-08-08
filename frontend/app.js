const $ = (id) => document.getElementById(id);
let ITEM_LABELS = { helmet: "Casco", vest: "Chaleco", gloves: "Guantes", glasses: "Lentes", boots: "Botas", mask: "Mascarilla" };
const REQUIRED_DEFAULT = ["helmet", "vest"];
let statusTimer = null;

async function api(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}

function requiredItems() {
  return [...document.querySelectorAll("#checkList input:checked")].map((c) => c.dataset.item);
}

async function loadVideos() {
  const d = await api("/api/videos");
  ITEM_LABELS = d.item_labels || ITEM_LABELS;
  const sel = $("videoSelect");
  sel.innerHTML = d.videos.length
    ? d.videos.map((v) => `<option>${v}</option>`).join("")
    : '<option value="">(coloca videos en /videos)</option>';
  $("conf").value = d.default_conf;
  $("confVal").textContent = d.default_conf;
  $("deviceName").textContent = d.device;
  return d.default_model;
}

async function loadModels(defaultKey) {
  const d = await api("/api/models");
  const sel = $("modelSelect");
  sel.innerHTML = d.models
    .map((m) => `<option value="${m.key}" ${m.available ? "" : "disabled"}>${m.label}${m.available ? "" : (m.trainable ? "" : " (falta descargar)")}</option>`)
    .join("");
  if (defaultKey) sel.value = defaultKey;
  await onModelChange();
}

// Al elegir modelo -> pide sus ítems y arma los checkboxes dinámicos
async function onModelChange() {
  const key = $("modelSelect").value;
  $("modelInfo").textContent = "cargando modelo...";
  const info = await api("/api/models/" + key);
  if (info.error) {
    $("modelInfo").textContent = "⚠ " + info.error;
    return;
  }
  $("modelName").textContent = key;
  const scheme = info.helmet_presence_only ? "presencia (casco por geometría)" : "puesto / no-puesto";
  $("modelInfo").textContent = `${info.items.length} EPP · ${scheme}`;
  $("checkList").innerHTML = info.items
    .map((it) => {
      const on = REQUIRED_DEFAULT.includes(it) ? "checked" : "";
      return `<label><input type="checkbox" data-item="${it}" ${on}/> ${ITEM_LABELS[it] || it}</label>`;
    })
    .join("") || '<span class="hint">este modelo no detecta EPP puntuable</span>';
  document.querySelectorAll("#checkList input").forEach((el) => el.addEventListener("change", pushParams));
}

async function pushParams() {
  await api("/api/params", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conf: parseFloat($("conf").value), required: requiredItems(), strict: $("strict").checked }),
  });
}

async function start() {
  const video = $("videoSelect").value;
  const model = $("modelSelect").value;
  if (!video) return alert("No hay video seleccionado.");
  const res = await api("/api/start", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video, model }),
  });
  if (res.error) return alert(res.error);
  await pushParams();
  $("stream").src = "/stream?t=" + Date.now();
  $("stream").style.display = "block";
  $("placeholder").style.display = "none";
  if (statusTimer) clearInterval(statusTimer);
  statusTimer = setInterval(pollStatus, 500);
}

async function stop() {
  await api("/api/stop", { method: "POST" });
  $("stream").style.display = "none";
  $("stream").src = "";
  $("placeholder").style.display = "block";
  if (statusTimer) clearInterval(statusTimer);
  $("people").innerHTML = "";
}

function barColor(pct, ready) {
  if (ready) return "#22c55e";
  if (pct >= 50) return "#eab308";
  return "#ef4444";
}

async function pollStatus() {
  const s = await api("/api/status");
  $("fps").textContent = s.fps ?? 0;
  const req = requiredItems();
  $("people").innerHTML = (s.people || [])
    .map((p, i) => {
      const chips = req.map((it) => {
        const cls = p.worn.includes(it) ? "has" : (p.not_worn.includes(it) ? "miss" : "unk");
        return `<span class="chip ${cls}">${ITEM_LABELS[it] || it}</span>`;
      }).join("");
      return `<div class="person-card">
        <div class="top"><span>Persona ${i + 1}</span>
          <span class="badge ${p.ready ? "ok" : "no"}">${p.ready ? "LISTO" : "NO LISTO"}</span></div>
        <div class="pct" style="color:${barColor(p.pct, p.ready)}">${p.pct}%</div>
        <div class="bar"><span style="width:${p.pct}%;background:${barColor(p.pct, p.ready)}"></span></div>
        <div class="chips">${chips}</div></div>`;
    }).join("");
}

$("conf").addEventListener("input", (e) => { $("confVal").textContent = e.target.value; pushParams(); });
$("strict").addEventListener("change", pushParams);
$("modelSelect").addEventListener("change", onModelChange);
$("startBtn").addEventListener("click", start);
$("stopBtn").addEventListener("click", stop);

(async () => {
  const def = await loadVideos();
  await loadModels(def);
})();
