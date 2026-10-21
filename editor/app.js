"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const KINDS = [
  ["piece", "Pieces"],
  ["mvs", "Before MVS"],
  ["ligature", "Ligatures"],
  ["char", "Punctuation & digits"],
  ["form", "Whole forms"],
];
const FILTERS = ["open", "all", "todo", "draft", "conflict", "ok", "new", "auto"];
const AUTO_KINDS = ["ligature", "mvs", "form"];
const POSITIONS = { isol: "isolated", init: "initial", medi: "medial", fina: "final" };
const DEFAULT_WORDS = "ᠮᠣᠩᠭᠣᠯ ᠪᠢᠴᠢᠭ ᠰᠠᠮᠪᠠ ᠦᠰᠦᠭ ᠲᠡᠮᠳᠡᠭ ᠬᠠᠭᠠᠨ ᠭᠡᠷ ᠴᠢᠬᠢ ᠵᠢᠯ ᠶᠠᠪᠤ ᠳᠠᠯᠠᠢ ᠺᠢᠨᠣ";

const state = {
  data: null,
  entries: {},
  problems: [],
  builds: {},
  ui: loadUi(),
  targetsByName: {},
  variantsById: {},
  saveTimer: null,
  buildTimer: null,
  building: false,
  buildAgain: false,
  fonts: {},
};

function loadUi() {
  const defaults = { cut: null, current: null, filter: "open", search: "", words: DEFAULT_WORDS };
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem("cmsr.ui") || "{}") };
  } catch {
    return defaults;
  }
}

function saveUi() {
  try {
    localStorage.setItem("cmsr.ui", JSON.stringify(state.ui));
  } catch {}
}

async function boot() {
  const response = await fetch("/api/data");
  const data = await response.json();
  state.data = data;
  state.entries = data.entries;
  state.problems = data.problems;
  state.builds = data.builds || {};
  for (const target of data.targets) state.targetsByName[target.name] = target;
  for (const variant of data.variants) state.variantsById[variant.id] = variant;
  if (!data.cuts.some((cut) => cut.id === state.ui.cut)) state.ui.cut = data.defaultCut;
  const linked = decodeURIComponent(location.hash.slice(1));
  if (state.entries[linked]) state.ui.current = linked;
  if (!state.entries[state.ui.current]) state.ui.current = firstOpen() || data.targets[0].name;

  buildCutSelect();
  buildFilters();
  wire();
  $("#search").value = state.ui.search;
  $("#words-input").value = state.ui.words;
  renderAll();
  if (state.builds[state.ui.cut]) loadBuiltFont(state.builds[state.ui.cut]);
  else scheduleBuild(0);
}

// ---------- model ----------

function entry(name) {
  return state.entries[name];
}

function target(name) {
  if (state.targetsByName[name]) return state.targetsByName[name];
  const using = state.data.variants.filter((variant) => variant.written === name);
  return { name, kind: "form", atoms: using[0]?.atoms || [], usedBy: using.map((variant) => variant.id), required: false };
}

function keysFor(item, cut = state.ui.cut) {
  if (!item) return null;
  return (item.cuts && item.cuts[cut]) ?? item.keys ?? null;
}

function isConflict(item) {
  return item.status !== "ok" && (item.note || "").includes("CONFLICT");
}

function matchesFilter(item) {
  const filter = state.ui.filter;
  if (filter === "all") return true;
  if (filter === "open") return ["todo", "draft"].includes(item.status) || isConflict(item);
  if (filter === "conflict") return isConflict(item);
  return item.status === filter;
}

function matchesSearch(item) {
  const query = state.ui.search.trim().toLowerCase();
  if (!query) return true;
  const info = target(item.name);
  const letters = lettersUsing(info).join(" ");
  return [item.name, info.label, letters, item.keys || "", item.note || ""].join(" ").toLowerCase().includes(query);
}

function visibleNames() {
  return Object.values(state.entries)
    .filter((item) => matchesFilter(item) && matchesSearch(item))
    .map((item) => item.name);
}

function firstOpen() {
  return Object.values(state.entries).find((item) => ["todo", "draft"].includes(item.status))?.name;
}

function lettersUsing(info) {
  const seen = [];
  for (const id of info.usedBy || []) {
    const label = state.variantsById[id].label;
    if (!seen.includes(label)) seen.push(label);
  }
  return seen;
}

// ---------- drawing ----------

function legacy(cut = state.ui.cut) {
  return state.data.legacy[cut];
}

function placeholderPart(cut = state.ui.cut) {
  const [bottom, top] = legacy(cut).stem;
  const width = 400;
  const inset = (top - bottom) / 2;
  const boxBottom = bottom - width * 0.75;
  const rect = (x0, y0, x1, y1) => `M${x0} ${y0}L${x0} ${y1}L${x1} ${y1}L${x1} ${y0}Z`;
  return {
    path:
      rect(0, bottom, width, top) +
      rect(inset, boxBottom, width - inset, bottom) +
      rect(inset * 2, boxBottom + inset, width - inset * 2, bottom - inset),
    advance: width,
    bounds: [0, boxBottom, width, top],
    placeholder: true,
  };
}

function keyParts(keys, cut = state.ui.cut) {
  const glyphs = legacy(cut).keys;
  return [...keys].map((key) => glyphs[key] || { ...placeholderPart(cut), missingKey: key });
}

function namedParts(name, cut = state.ui.cut) {
  const item = entry(name);
  const keys = keysFor(item, cut);
  if (keys) return keyParts(keys, cut);
  const info = target(name);
  if ((item?.status === "auto" || !item) && info.atoms.length) {
    return info.atoms.flatMap((atom) => namedParts(atom, cut));
  }
  return [placeholderPart(cut)];
}

function variantParts(variant, highlight, cut = state.ui.cut) {
  const whole = entry(variant.written);
  if (whole && keysFor(whole, cut)) {
    return keyParts(keysFor(whole, cut), cut).map((part) => ({ ...part, highlight: variant.written === highlight }));
  }
  return variant.atoms.flatMap((atom) =>
    namedParts(atom, cut).map((part) => ({ ...part, highlight: atom === highlight })),
  );
}

// Font units to vertical screen space: the run advances down, the font's up points right.
function runSvg(parts, metrics, size, className = "") {
  let x = 0;
  const paths = parts
    .map((part) => {
      const classes = [part.highlight && "hl", part.placeholder && "ph"].filter(Boolean).join(" ");
      const markup = `<path transform="translate(${x} 0)" d="${part.path}" class="${classes}"${part.placeholder ? ' fill-rule="evenodd"' : ""}/>`;
      x += part.advance;
      return markup;
    })
    .join("");
  const length = Math.max(x, metrics.upm * 0.2);
  // Crop across the stem to the ink, but keep one scale per em so sizes stay comparable.
  const pad = metrics.upm * 0.03;
  const low = Math.min(...parts.map((part) => part.bounds?.[1] ?? metrics.descent)) - pad;
  const high = Math.max(...parts.map((part) => part.bounds?.[3] ?? metrics.ascent)) + pad;
  const width = high - low;
  const scale = size / metrics.upm;
  return (
    `<svg class="run ${className}" viewBox="${low} 0 ${width} ${length}" ` +
    `width="${(width * scale).toFixed(1)}" height="${(length * scale).toFixed(1)}">` +
    `<g transform="matrix(0 1 1 0 0 0)">${paths}</g></svg>`
  );
}

function legacySvg(parts, size, className) {
  return runSvg(parts, legacy(), size, className);
}

function referenceSvg(name, size) {
  const reference = state.data.reference;
  const glyph = name && reference.glyphs[name];
  if (!glyph) return `<div class="no-ref">no reference</div>`;
  return runSvg([glyph], reference, size, "ref");
}

// ---------- rendering ----------

function renderAll() {
  renderProgress();
  renderList();
  renderTarget();
  renderUsage();
  renderWords();
  renderProblems();
  renderBuild();
}

function renderProgress() {
  const counts = {};
  for (const item of Object.values(state.entries)) counts[item.status] = (counts[item.status] || 0) + 1;
  const pieces = Object.values(state.entries).filter((item) => item.kind === "piece");
  const done = pieces.filter((item) => ["ok", "new"].includes(item.status)).length;
  $("#progress").innerHTML =
    `<span>pieces <b>${done}</b>/${pieces.length} settled</span>` +
    ["todo", "draft", "ok", "new"].map((status) => `<span class="chip s-${status}">${status} ${counts[status] || 0}</span>`).join("");
}

function renderList() {
  const names = new Set(visibleNames());
  const html = KINDS.map(([kind, title]) => {
    const rows = Object.values(state.entries).filter((item) => item.kind === kind && names.has(item.name));
    if (!rows.length) return "";
    return (
      `<h4>${title} <span>${rows.length}</span></h4>` +
      rows
        .map((item) => {
          const info = target(item.name);
          const hint = info.kind === "char" ? info.label : lettersUsing(info).slice(0, 6).join(" ");
          const flags = [isConflict(item) && "conflict", info.kind === "ligature" && info.required && "req"].filter(Boolean);
          return (
            `<button class="row ${item.name === state.ui.current ? "on" : ""}" data-name="${escapeAttr(item.name)}">` +
            `<i class="dot s-${item.status}"></i><code>${escapeHtml(item.name)}</code>` +
            `<small>${escapeHtml(hint)}</small>${flags.map((flag) => `<em>${flag}</em>`).join("")}</button>`
          );
        })
        .join("")
    );
  }).join("");
  $("#targets").innerHTML = html || `<p class="hint">Nothing matches.</p>`;
  $("#targets .row.on")?.scrollIntoView({ block: "nearest" });
}

function renderTarget() {
  const name = state.ui.current;
  const item = entry(name);
  const info = target(name);
  const cut = state.ui.cut;
  const keys = keysFor(item) || "";
  const cutOnly = Boolean(item.cuts && item.cuts[cut] !== undefined);
  const parts = namedParts(name);
  const letters = lettersUsing(info);
  const description =
    info.kind === "piece"
      ? `${POSITIONS[name.split(".")[1]]} written unit · used by ${info.usedBy.length} forms of ${letters.join(", ") || "—"}`
      : info.kind === "ligature"
        ? `${info.required ? "required" : "optional"} ligature of ${info.atoms.join(" + ")}`
        : info.kind === "mvs"
          ? `shape before a narrow MVS (chachlag), instead of ${info.atoms.join(" + ")}`
          : info.kind === "char"
            ? info.label
            : `whole written form, instead of ${info.atoms.join(" + ")}`;

  const statusButtons = [
    ["ok", "Confirm", "↵"],
    ["draft", "Draft", ""],
    ["new", "Not in CMs", ""],
    ["todo", "Todo", ""],
    ...(AUTO_KINDS.includes(info.kind) ? [["auto", "Use parts", ""]] : []),
  ];

  $("#target").innerHTML = `
    <div class="t-head">
      <h2><code>${escapeHtml(name)}</code> <i class="chip s-${item.status}">${item.status}</i></h2>
      <p>${escapeHtml(description)}</p>
    </div>
    <div class="controls">
      <label class="keys">Keys <input id="keys" value="${escapeAttr(keys)}" spellcheck="false" autocomplete="off"></label>
      <label class="small"><input id="cut-only" type="checkbox" ${cutOnly ? "checked" : ""}> only ${escapeHtml(cutName(cut))}</label>
      <div class="actions">
        ${statusButtons
          .map(
            ([status, label, key]) =>
              `<button data-status="${status}" class="${item.status === status ? "on" : ""}">${label}${key ? ` <kbd>${key}</kbd>` : ""}</button>`,
          )
          .join("")}
      </div>
    </div>
    <div class="stage">
      <div class="main-figures">
        <figure><figcaption>CMs ${escapeHtml(cutName(cut))}</figcaption>${legacySvg(parts, 150, "big")}</figure>
        ${info.reference ? `<figure><figcaption>Unicode</figcaption>${referenceSvg(info.reference, 150)}</figure>` : ""}
        ${
          AUTO_KINDS.includes(info.kind) && keys
            ? `<figure><figcaption>From parts</figcaption>${legacySvg(info.atoms.flatMap((atom) => namedParts(atom)), 150, "big")}</figure>`
            : ""
        }
      </div>
      <div id="forms" class="forms"></div>
    </div>
    <textarea id="note" rows="2" placeholder="Note">${escapeHtml(item.note || "")}</textarea>
    <p class="hint">↵ confirm · Tab / ⇧Tab move · Esc reverts keys · click a form to map it whole</p>`;
  renderUsage();
  $("#keys").focus();
}

function codeChips(variant) {
  const chips = [`U+${variant.codePoint.toString(16).toUpperCase()}`];
  if (variant.fvs) chips.push(`FVS${variant.fvs}`);
  return chips.map((chip) => `<i class="cp">${chip}</i>`).join("");
}

function renderUsage() {
  const element = $("#forms");
  if (!element) return;
  const name = state.ui.current;
  const ids = target(name).usedBy || [];
  if (!ids.length) {
    element.innerHTML = "";
    return;
  }
  const cards = ids.map((id) => {
    const variant = state.variantsById[id];
    return `<div class="card ${variant.default ? "" : "alt"}${variant.written === name ? " self" : ""}" data-written="${escapeAttr(variant.written)}" title="Map ${escapeAttr(variant.written)} as a whole form">
      <header>${escapeHtml(variant.label)} · ${POSITIONS[variant.position]} ${codeChips(variant)}</header>
      <div class="pair">${referenceSvg(variant.reference, 64)}${legacySvg(variantParts(variant, name), 64)}</div>
      <footer><code>${escapeHtml(variant.written)}</code>${variant.default ? "" : " · variant"}</footer>
    </div>`;
  });
  element.innerHTML = `<h3>${ids.length} forms <span class="hint">Unicode left · CMs right, this piece highlighted</span></h3><div class="cards">${cards.join("")}</div>`;
}

function renderWords() {
  const build = state.builds[state.ui.cut];
  const family = build && state.fonts[build.revision];
  const words = state.ui.words.split(/\s+/).filter(Boolean);
  $("#words").innerHTML = words
    .map(
      (word) =>
        `<div class="word"><span class="v ref-font">${escapeHtml(word)}</span>` +
        `<span class="v" style="font-family:'${family || "none"}'">${escapeHtml(word)}</span></div>`,
    )
    .join("");
}

function renderProblems() {
  const failures = state.builds[state.ui.cut]?.failures || [];
  const lines = [...state.problems, ...failures.map((failure) => `${failure.index}: got ${failure.got}, want ${failure.want}`)];
  $("#problems").innerHTML = lines.length ? `<h3>Problems</h3><ul>${lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>` : "";
}

function renderBuild() {
  const element = $("#build");
  const build = state.builds[state.ui.cut];
  element.className = "build";
  if (state.building) {
    element.textContent = "building…";
    element.classList.add("busy");
  } else if (!build) {
    element.textContent = "not built";
  } else if (build.error) {
    element.textContent = `build failed: ${build.error}`;
    element.classList.add("bad");
  } else {
    const passed = build.cases - build.failures.length;
    element.textContent = `built · shaping ${passed}/${build.cases} · ${build.placeholders} placeholders`;
    if (build.failures.length) element.classList.add("bad");
  }
}

function cutName(id) {
  return state.data.cuts.find((cut) => cut.id === id).name;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/'/g, "&#39;");
}

// ---------- actions ----------

function select(name) {
  if (!state.entries[name]) return;
  flushSave();
  state.ui.current = name;
  saveUi();
  history.replaceState(null, "", `#${encodeURIComponent(name)}`);
  renderList();
  renderTarget();
  renderUsage();
}

function move(step) {
  const names = visibleNames();
  if (!names.length) return;
  const index = names.indexOf(state.ui.current);
  select(names[(index + step + names.length) % names.length]);
}

function editKeys(value) {
  const item = entry(state.ui.current);
  const cut = state.ui.cut;
  if ($("#cut-only")?.checked) {
    item.cuts = { ...(item.cuts || {}), [cut]: value };
  } else {
    item.keys = value || null;
  }
  const hasKeys = Boolean(keysFor(item));
  if (hasKeys && ["todo", "ok", "auto"].includes(item.status)) item.status = "draft";
  if (!hasKeys && item.status === "draft") item.status = AUTO_KINDS.includes(item.kind) ? "auto" : "todo";
  const caret = $("#keys").selectionStart;
  renderTarget();
  $("#keys").setSelectionRange(caret, caret);
  renderUsage();
  renderProgress();
  scheduleSave(item.name);
}

function setStatus(status) {
  const item = entry(state.ui.current);
  if (status === "ok" && !keysFor(item)) {
    flash("Nothing to confirm: type the keys first, or mark it Not in CMs.");
    return;
  }
  if (status === "auto") {
    item.keys = null;
    item.cuts = {};
  }
  item.status = status;
  scheduleSave(item.name, 0);
  if (status === "ok" || status === "new") {
    const names = visibleNames();
    const index = names.indexOf(item.name);
    const next = names.slice(index + 1).find((name) => name !== item.name) || names.find((name) => name !== item.name);
    renderProgress();
    if (next) return select(next);
  }
  renderAll();
}

function scheduleSave(name, delay = 500) {
  clearTimeout(state.saveTimer);
  state.pendingSave = name;
  state.saveTimer = setTimeout(flushSave, delay);
}

async function flushSave() {
  clearTimeout(state.saveTimer);
  const name = state.pendingSave;
  if (!name) return;
  state.pendingSave = null;
  const item = entry(name);
  const response = await fetch("/api/entry", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, keys: item.keys, status: item.status, note: item.note, cuts: item.cuts || {} }),
  });
  const result = await response.json();
  if (result.error) {
    flash(`Not saved: ${result.error}`);
    return;
  }
  state.entries = result.entries;
  state.problems = result.problems;
  renderProblems();
  renderList();
  scheduleBuild();
}

function scheduleBuild(delay = 1200) {
  clearTimeout(state.buildTimer);
  state.buildTimer = setTimeout(runBuild, delay);
}

async function runBuild() {
  if (state.building) {
    state.buildAgain = true;
    return;
  }
  state.building = true;
  renderBuild();
  const cut = state.ui.cut;
  try {
    const response = await fetch("/api/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cut }),
    });
    const result = await response.json();
    state.builds[cut] = result.error ? { error: result.error } : result;
    if (!result.error) await loadBuiltFont(result);
  } catch (error) {
    state.builds[cut] = { error: String(error) };
  }
  state.building = false;
  renderBuild();
  renderProblems();
  if (state.buildAgain) {
    state.buildAgain = false;
    scheduleBuild(0);
  }
}

async function loadBuiltFont(build) {
  const family = `built-${build.revision}`;
  if (!state.fonts[build.revision]) {
    const face = new FontFace(family, `url(${build.font}?v=${build.revision})`);
    await face.load();
    document.fonts.add(face);
    state.fonts[build.revision] = family;
  }
  renderWords();
}

function flash(message) {
  const element = document.createElement("div");
  element.className = "flash";
  element.textContent = message;
  document.body.append(element);
  setTimeout(() => element.remove(), 2600);
}

// ---------- wiring ----------

function buildCutSelect() {
  $("#cut").innerHTML = state.data.cuts.map((cut) => `<option value="${cut.id}">${cut.name}</option>`).join("");
  $("#cut").value = state.ui.cut;
}

function buildFilters() {
  $("#filters").innerHTML = FILTERS.map((filter) => `<button data-filter="${filter}">${filter}</button>`).join("");
  markFilter();
}

function markFilter() {
  for (const button of document.querySelectorAll("#filters button")) {
    button.classList.toggle("on", button.dataset.filter === state.ui.filter);
  }
}

function wire() {
  $("#cut").addEventListener("change", (event) => {
    state.ui.cut = event.target.value;
    saveUi();
    renderAll();
    if (state.builds[state.ui.cut]) loadBuiltFont(state.builds[state.ui.cut]);
    else scheduleBuild(0);
  });
  $("#search").addEventListener("input", (event) => {
    state.ui.search = event.target.value;
    saveUi();
    renderList();
  });
  $("#filters").addEventListener("click", (event) => {
    const filter = event.target.closest("button")?.dataset.filter;
    if (!filter) return;
    state.ui.filter = filter;
    saveUi();
    markFilter();
    renderList();
  });
  $("#targets").addEventListener("click", (event) => {
    const name = event.target.closest(".row")?.dataset.name;
    if (name) select(name);
  });
  $("#build").addEventListener("click", () => scheduleBuild(0));
  $("#target").addEventListener("click", (event) => {
    const written = event.target.closest(".card")?.dataset.written;
    if (!written || written === state.ui.current) return;
    if (!state.entries[written]) state.entries[written] = { name: written, kind: "form", status: "auto", note: "" };
    if (state.ui.filter !== "all" && !matchesFilter(state.entries[written])) {
      state.ui.filter = "all";
      markFilter();
    }
    select(written);
  });
  $("#words-input").addEventListener("input", (event) => {
    state.ui.words = event.target.value;
    saveUi();
    renderWords();
  });

  const work = $("#target");
  work.addEventListener("input", (event) => {
    if (event.target.id === "keys") editKeys(event.target.value);
    if (event.target.id === "note") {
      entry(state.ui.current).note = event.target.value;
      scheduleSave(state.ui.current, 800);
    }
  });
  work.addEventListener("change", (event) => {
    if (event.target.id !== "cut-only") return;
    const item = entry(state.ui.current);
    if (event.target.checked) item.cuts = { ...(item.cuts || {}), [state.ui.cut]: item.keys || "" };
    else if (item.cuts) delete item.cuts[state.ui.cut];
    renderTarget();
    renderUsage();
    scheduleSave(item.name, 0);
  });
  work.addEventListener("click", (event) => {
    const status = event.target.closest("[data-status]")?.dataset.status;
    if (status) setStatus(status);
  });

  document.addEventListener("keydown", (event) => {
    const inText = event.target.tagName === "TEXTAREA" || event.target.id === "search";
    if (event.key === "Tab" && !inText) {
      event.preventDefault();
      move(event.shiftKey ? -1 : 1);
    } else if (event.key === "Enter" && !inText && !event.isComposing) {
      event.preventDefault();
      setStatus("ok");
    } else if (event.key === "Escape" && event.target.id === "keys") {
      revertKeys();
    }
  });
  window.addEventListener("beforeunload", flushSave);
}

async function revertKeys() {
  clearTimeout(state.saveTimer);
  state.pendingSave = null;
  const response = await fetch("/api/data");
  const data = await response.json();
  state.entries = data.entries;
  renderAll();
}

boot();
