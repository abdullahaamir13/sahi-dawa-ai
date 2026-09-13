// Sahi Dawa — thin-client frontend.
// No medicine matching, price arithmetic, history storage, or AI reasoning
// happens here. Every fact on screen comes from the API response below.

const API_BASE = ""; // same-origin: served by the FastAPI backend itself

const state = {
  step: "form",
  response: null,      // last POST /prescription (or resolved-by-id) response
  history: null,       // GET /history/{patient_id} for the FOUND case
};

// ---------- tiny API helper ----------
async function api(path, options) {
  const res = await fetch(API_BASE + path, options);
  let body = null;
  try { body = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok && res.status !== 404) {
    throw new Error(`Backend error ${res.status}`);
  }
  return { ok: res.ok, status: res.status, body };
}

const pkr = (v) => (v === null || v === undefined ? "not available" : `PKR ${Number(v).toFixed(2)}`);
const clean = (manufacturer) => manufacturer.split(" DML")[0].split(" DSL")[0];

// ---------- navigation ----------
function goto(step) {
  state.step = step;
  document.querySelectorAll(".screen").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".step").forEach((el) => el.classList.remove("active", "done"));

  const order = ["form", "results", "explanation", "summary"];
  const idx = order.indexOf(step);
  order.forEach((s, i) => {
    const btn = document.querySelector(`.step[data-step="${s}"]`);
    if (i === idx) btn.classList.add("active");
    else if (i < idx) btn.classList.add("done");
  });

  const screenId = step === "loading" ? "screen-loading" : `screen-${step}`;
  document.getElementById(screenId).classList.add("active");
}

function showLoading(endpointLabel) {
  document.querySelectorAll(".screen").forEach((el) => el.classList.remove("active"));
  document.getElementById("loading-endpoint").textContent = endpointLabel;
  document.getElementById("screen-loading").classList.add("active");
}

// ---------- screen 01: form ----------
const medicineInput = document.getElementById("input-medicine");
const analyzeBtn = document.getElementById("analyze-btn");

function refreshAnalyzeEnabled() {
  analyzeBtn.disabled = !medicineInput.value.trim();
}
medicineInput.addEventListener("input", refreshAnalyzeEnabled);
refreshAnalyzeEnabled();

document.querySelectorAll("[data-fill]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const [medicine, dosage, diagnosis] = btn.dataset.fill.split("|");
    document.getElementById("input-medicine").value = medicine;
    document.getElementById("input-dosage").value = dosage;
    document.getElementById("input-diagnosis").value = diagnosis;
    refreshAnalyzeEnabled();
  });
});

document.getElementById("prescription-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    patient_id: document.getElementById("input-patient-id").value.trim() || "PK-10432",
    diagnosis: document.getElementById("input-diagnosis").value.trim(),
    medicine: document.getElementById("input-medicine").value.trim(),
    dosage: document.getElementById("input-dosage").value.trim() || null,
  };

  showLoading("POST /prescription");
  try {
    const { body } = await api("/prescription", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    state.response = { ...body, source: "PRESCRIPTION" };
    state.history = null;

    if (body.status === "FOUND") {
      const h = await api(`/history/${encodeURIComponent(payload.patient_id)}`);
      state.history = h.body;
    }

    renderResults();
    goto("results");
  } catch (err) {
    alert("Could not reach the backend. Is the API running?\n\n" + err.message);
    goto("form");
  }
});

document.getElementById("new-prescription-btn").addEventListener("click", () => goto("form"));

// ---------- screen 02: results ----------
function renderResults() {
  const r = state.response;
  const found = r.status === "FOUND";

  document.getElementById("status-badge").textContent = "status · " + r.status;
  document.getElementById("status-badge").className = "badge" + (found ? "" : " warn");

  document.getElementById("result-heading").textContent = found
    ? `${r.medicine.brand_name} ${r.medicine.strength} ${r.medicine.dosage_form}`
    : r.status === "AMBIGUOUS"
      ? "More than one record matches"
      : "Not in the verified catalogue";

  document.getElementById("endpoint-line").textContent =
    r.source === "BY_ID"
      ? `GET /medicine/${r.medicine.medicine_id} + GET /alternatives/${r.medicine.medicine_id}`
      : `POST /prescription · medicine: ${r.medicine_query}${r.dosage_query ? " · dosage: " + r.dosage_query : ""}`;

  // message box (NOT_FOUND / AMBIGUOUS)
  const msgBox = document.getElementById("message-box");
  if (r.message) {
    msgBox.hidden = false;
    document.getElementById("message-text").textContent = r.message;
  } else {
    msgBox.hidden = true;
  }

  // candidates (AMBIGUOUS)
  const candCard = document.getElementById("candidates-card");
  const foundBlock = document.getElementById("found-block");
  candCard.hidden = r.status !== "AMBIGUOUS";
  foundBlock.hidden = !found;

  if (r.status === "AMBIGUOUS") {
    const list = document.getElementById("candidates-list");
    list.innerHTML = "";
    r.candidates.forEach((c) => {
      const row = document.createElement("div");
      row.className = "row clickable";
      row.innerHTML = `
        <div class="name"><b>${c.brand_name} · ${c.strength}</b><small>${clean(c.manufacturer)}</small></div>
        <code>${c.dosage_form} · ${c.pack_size}</code>
        <code>${c.medicine_id}</code>`;
      row.addEventListener("click", () => resolveById(c.medicine_id));
      list.appendChild(row);
    });
  }

  if (found) renderFound(r);
}

async function resolveById(medicineId) {
  showLoading(`GET /medicine/${medicineId} + GET /alternatives/${medicineId}`);
  try {
    const medRes = await api(`/medicine/${medicineId}`);
    const altRes = await api(`/alternatives/${medicineId}`);

    if (!medRes.ok || !altRes.ok) throw new Error("Lookup failed for the selected medicine_id.");

    state.response = {
      source: "BY_ID",
      status: "FOUND",
      message: null,
      medicine: medRes.body,
      candidates: [],
      alternatives: altRes.body.alternatives,
      price_comparison: altRes.body.price_comparison,
      pattern_flags: [],   // this path returns no flags, per the API contract
      explanation: null,   // this path returns no explanation, per the API contract
    };
    state.history = null;

    renderResults();
    goto("results");
  } catch (err) {
    alert("Could not resolve that medicine_id.\n\n" + err.message);
  }
}

function renderFound(r) {
  const med = r.medicine;
  const price = r.price_comparison;

  document.getElementById("med-id-line").textContent = `${med.medicine_id} · reg ${med.registration_number || "—"}`;
  document.getElementById("verified-line").textContent =
    `data_status: ${med.data_status} · last_verified: ${med.last_verified || "—"} · price_effective_date: ${med.price_effective_date || "—"}`;

  const medFields = [
    ["brand_name", med.brand_name],
    ["generic_name", med.generic_name],
    ["active_ingredient", med.active_ingredient],
    ["strength", med.strength],
    ["dosage_form", med.dosage_form],
    ["pack_size", med.pack_size],
    ["manufacturer", clean(med.manufacturer)],
    ["price", pkr(med.price)],
    ["medicine_category", med.medicine_category],
  ];
  document.getElementById("med-fields").innerHTML = medFields
    .map(([k, v]) => `<div class="field"><span class="k">${k}</span><span class="v">${v}</span></div>`)
    .join("");

  // alternatives
  document.getElementById("alt-count-line").textContent = `${r.alternatives.length} record(s) · GET /alternatives/${med.medicine_id}`;
  const altList = document.getElementById("alternatives-list");
  if (r.alternatives.length === 0) {
    altList.innerHTML = `<div class="empty-row">No same-medicine alternatives in the catalogue. This is a normal result.</div>`;
  } else {
    altList.innerHTML = r.alternatives
      .map((a) => {
        const tag =
          a.medicine_id === price.lowest_pack_price_medicine_id ? "lowest pack" :
          a.medicine_id === price.lowest_unit_price_medicine_id ? "lowest unit" : "";
        return `<div class="row">
          <div class="name"><b>${a.brand_name}${tag ? `<span class="tag">${tag}</span>` : ""}</b><small>${clean(a.manufacturer)}</small></div>
          <code>${a.pack_size}</code>
          <span class="price">${pkr(a.price)}</span>
          <span class="unit">${a.unit_price != null ? pkr(a.unit_price) + " / " + a.pack_unit : "unit price null"}</span>
        </div>`;
      })
      .join("");
  }

  // price comparison
  document.getElementById("comparison-basis-line").textContent = "comparison_basis: " + price.comparison_basis;
  const priceFields = [
    ["current_price", pkr(price.current_price), false],
    ["current_pack_size", price.current_pack_size + (price.current_pack_quantity ? ` (${price.current_pack_quantity} ${price.current_pack_unit})` : ""), false],
    ["current_unit_price", price.current_unit_price != null ? pkr(price.current_unit_price) + " / " + price.current_pack_unit : "not available", false],
    ["lowest_pack_price", pkr(price.lowest_pack_price) + (price.lowest_pack_price_medicine_id ? " · " + price.lowest_pack_price_medicine_id : ""), false],
    ["pack_price_difference", pkr(price.pack_price_difference), true],
    ["lowest_unit_price", price.lowest_unit_price != null ? `${pkr(price.lowest_unit_price)} / ${price.lowest_unit_price_unit} · ${price.lowest_unit_price_medicine_id}` : "not available", false],
    ["unit_price_difference", price.unit_price_difference != null ? pkr(price.unit_price_difference) + " / " + price.current_pack_unit : "not available", true],
  ];
  document.getElementById("price-fields").innerHTML = priceFields
    .map(([k, v, hl]) => `<div class="field"><span class="k">${k}</span><span class="v${hl ? " highlight" : ""}">${v}</span></div>`)
    .join("");
  document.getElementById("price-note").textContent = price.note;

  // pattern flags
  const flags = r.pattern_flags || [];
  const flagsCard = document.getElementById("flags-card");
  flagsCard.classList.toggle("has-flags", flags.length > 0);
  document.getElementById("flags-list").innerHTML = flags.length
    ? flags.map((f) => `<div class="flag-item">
        <span class="type">${f.flag_type}</span>
        <span>${f.message}</span>
        <span class="note">${f.safety_note}</span>
      </div>`).join("")
    : `<div class="empty-row">No discussion flags returned for this patient. The array is empty, which is a normal result.</div>`;

  // encounters (bonus panel, from GET /history — only fetched on the direct-prescription path)
  const patientId = r.patient_id || "—";
  document.getElementById("history-endpoint-line").textContent = `GET /history/${patientId}`;
  const encList = document.getElementById("encounters-list");
  if (state.history && state.history.encounters.length) {
    encList.innerHTML = state.history.encounters
      .map((e) => `<div class="row">
        <code>${e.encounter_date}</code>
        <div class="name"><b>${e.medicine_name}</b></div>
        <span class="muted">${e.diagnosis}</span>
        <span class="chip${e.medicine_category === "Antibiotic" ? " antibiotic" : ""}">${e.medicine_category}</span>
      </div>`).join("");
  } else if (r.source === "BY_ID") {
    encList.innerHTML = `<div class="empty-row">Not fetched on this path — resolving an ambiguous pick by medicine_id doesn't call GET /history.</div>`;
  } else {
    encList.innerHTML = `<div class="empty-row">No prior encounters for this patient.</div>`;
  }
}

document.getElementById("read-explanation-btn").addEventListener("click", () => {
  renderExplanation();
  goto("explanation");
});

// ---------- screen 03: explanation ----------
function renderExplanation() {
  const r = state.response;
  const card = document.getElementById("explanation-card");
  const empty = document.getElementById("no-explanation-box");

  if (r && r.explanation) {
    card.hidden = false;
    empty.hidden = true;
    document.getElementById("explanation-text").innerHTML = r.explanation
      .split("\n\n")
      .map((p) => `<p>${p}</p>`)
      .join("");
  } else {
    card.hidden = true;
    empty.hidden = false;
  }
}

document.getElementById("back-to-results-btn").addEventListener("click", () => goto("results"));
document.getElementById("goto-summary-btn").addEventListener("click", async () => {
  await loadSummary();
  goto("summary");
});
document.getElementById("analyze-another-btn").addEventListener("click", () => goto("form"));

// ---------- screen 04: summary ----------
async function loadSummary() {
  const patientId = (state.response && state.response.patient_id) || document.getElementById("input-patient-id").value.trim() || "PK-10432";
  showLoading(`GET /summary/${patientId}`);
  try {
    const { body } = await api(`/summary/${encodeURIComponent(patientId)}`);
    renderSummary(patientId, body);
    goto("summary");
  } catch (err) {
    alert("Could not load the summary.\n\n" + err.message);
    goto("results");
  }
}

function renderSummary(patientId, s) {
  document.getElementById("summary-endpoint-line").textContent = `GET /summary/${patientId}`;

  document.getElementById("summary-stats").innerHTML = [
    ["patient_id", s.patient_id],
    ["total_encounters", s.total_encounters],
    ["first_encounter_date", s.first_encounter_date || "null"],
    ["last_encounter_date", s.last_encounter_date || "null"],
  ].map(([k, v]) => `<div class="stat"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("");

  document.getElementById("summary-diagnoses").textContent = s.diagnoses_recorded.length ? s.diagnoses_recorded.join(" · ") : "—";

  const medsBox = document.getElementById("summary-medications");
  medsBox.innerHTML = s.medications_recorded.length
    ? s.medications_recorded.map((m) => `<div class="row">
        <code>${m.encounter_date}</code>
        <div class="name"><b>${m.medicine_name}</b></div>
        <span class="muted">${m.dosage_form} · ${m.dosage || "—"}</span>
        <span class="chip${m.medicine_category === "Antibiotic" ? " antibiotic" : ""}">${m.medicine_category}</span>
      </div>`).join("")
    : `<div class="empty-row">No medications recorded yet for this patient.</div>`;

  document.getElementById("summary-transparency-note").textContent = s.transparency_note;
}

document.getElementById("print-btn").addEventListener("click", () => window.print());

// ---------- top nav (manual step clicks, only when data is available) ----------
document.getElementById("steps").addEventListener("click", (e) => {
  const btn = e.target.closest(".step");
  if (!btn) return;
  const target = btn.dataset.step;
  if (target === "form") return goto("form");
  if (!state.response) return; // nothing to show yet
  if (target === "results") return goto("results");
  if (target === "explanation") { renderExplanation(); return goto("explanation"); }
  if (target === "summary") return loadSummary();
});

goto("form");
