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
  groups: {},
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
  let data;
  try {
    const response = await fetch("/api/data");
    if (!response.ok) throw new Error(`the server answered ${response.status}`);
    data = await response.json();
  } catch (error) {
    document.body.innerHTML = `<p style="padding:24px;font:15px sans-serif">The editor could not load its data (${escapeHtml(String(error.message || error))}). Is <code>uv run cmsr editor</code> running? Its terminal shows the error.</p>`;
    return;
  }
  state.data = data;
  state.entries = data.entries;
  state.groups = data.groups || {};
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

function keyParts(keys, cut = state.ui.cut, shift = {}) {
  const glyphs = legacy(cut).keys;
  const drawings = state.data.drawings?.[cut] || {};
  return [...keys].flatMap((key, index) => {
    const redrawn = glyphs[key] && drawings[`cms.${glyphs[key].glyph}`];
    const part = redrawn ? { ...glyphs[key], ...redrawn } : glyphs[key] || { ...placeholderPart(cut), missingKey: key };
    const units = Number(shift[index] || 0);
    return units ? [{ path: "", advance: units, bounds: [0, 0, 0, 0] }, part] : [part];
  });
}

// Marks sit over the keys at an offset from the piece's start and take no advance; a mark
// `on` a key lines up tooth tip to tooth tip with it, as the build does.
function markParts(item, cut, start, keys = "", shift = {}) {
  const glyphs = legacy(cut).keys;
  const origins = [];
  let x = 0;
  [...keys].forEach((key, index) => {
    x += Number(shift[index] || 0);
    origins.push(x);
    x += glyphs[key]?.advance || 0;
  });
  return (item?.marks || [])
    .map((mark) => {
      const glyph = glyphs[mark.key];
      if (!glyph) return null;
      const contours = mark.contours ? mark.contours.map((index) => glyph.contours[index]).filter(Boolean) : [glyph];
      if (!contours.length) return null;
      const low = Math.min(...contours.map((contour) => contour.bounds[1])) + mark.dy;
      const high = Math.max(...contours.map((contour) => contour.bounds[3])) + mark.dy;
      let dx = mark.dx;
      if (mark.on !== undefined && mark.on !== null && glyphs[keys[mark.on]]) dx += origins[mark.on] + glyphs[keys[mark.on]].tip - glyph.tip;
      return { path: contours.map((contour) => contour.path).join(""), advance: 0, dx: dx - start, dy: mark.dy, bounds: [0, low, 0, high] };
    })
    .filter(Boolean);
}

function hasDrawing(item, cut = state.ui.cut) {
  return Boolean(keysFor(item, cut) || item?.marks?.length);
}

// A piece named on its own wins over a group that contains it, as in the build.
function ruleKeys(item, previous) {
  if (!previous || !item?.after) return null;
  if (item.after[previous] !== undefined) return item.after[previous];
  for (const [key, keys] of Object.entries(item.after)) {
    if (key.startsWith("@") && (state.groups[key.slice(1)] || []).includes(previous)) return keys;
  }
  return null;
}

function groupExample(previous) {
  return previous.startsWith("@") ? (state.groups[previous.slice(1)] || [])[0] : previous;
}

// A hand drawing replaces keys, as in the build: for a rule, the piece's own rule drawing
// wins over its group's; then a drawing of the whole piece.
function drawingPart(name, cut, previous, item) {
  const drawings = state.data.drawings?.[cut] || {};
  const names = [];
  if (previous && ruleKeys(item, previous) !== null) {
    names.push(`cmsr.${name}.after.${previous}`);
    if (item.after[previous] === undefined) {
      for (const key of Object.keys(item.after)) {
        if (key.startsWith("@") && (state.groups[key.slice(1)] || []).includes(previous)) names.push(`cmsr.${name}.after.${key}`);
      }
    }
  } else {
    const glyph = target(name)?.glyph;
    if (glyph) names.push(glyph);
  }
  const drawing = names.map((found) => drawings[found]).find(Boolean);
  return drawing ? { path: drawing.path, advance: drawing.advance, bounds: drawing.bounds, drawn: true } : null;
}

// `previous` is the piece right before, for the neighbour rules.
function namedParts(name, cut = state.ui.cut, previous = null) {
  const item = entry(name);
  const drawn = drawingPart(name, cut, previous, item);
  if (drawn) return [drawn];
  const ruleKeys_ = ruleKeys(item, previous);
  if (ruleKeys_ || hasDrawing(item, cut)) {
    const parts = ruleKeys_ ? keyParts(ruleKeys_, cut) : keyParts(keysFor(item, cut) || "", cut, item?.shift || {});
    const advance = parts.reduce((sum, part) => sum + part.advance, 0);
    return [...parts, ...markParts(item, cut, advance, ruleKeys_ ? "" : keysFor(item, cut) || "", ruleKeys_ ? {} : item?.shift || {})];
  }
  const info = target(name);
  if ((item?.status === "auto" || !item) && info.atoms.length) {
    return info.atoms.flatMap((atom) => namedParts(atom, cut));
  }
  return [placeholderPart(cut)];
}

function variantParts(variant, highlight, cut = state.ui.cut) {
  const whole = entry(variant.written);
  if (whole && hasDrawing(whole, cut)) {
    return namedParts(variant.written, cut).map((part) => ({ ...part, highlight: variant.written === highlight }));
  }
  return variant.atoms.flatMap((atom, index) =>
    namedParts(atom, cut, variant.atoms[index - 1]).map((part) => ({ ...part, highlight: atom === highlight })),
  );
}

// Font units to vertical screen space: the run advances down, the font's up points right.
function runSvg(parts, metrics, size, className = "") {
  let x = 0;
  const paths = parts
    .map((part) => {
      const classes = [part.highlight && "hl", part.placeholder && "ph"].filter(Boolean).join(" ");
      const markup = `<path transform="translate(${x + (part.dx || 0)} ${part.dy || 0})" d="${part.path}" class="${classes}"${part.placeholder ? ' fill-rule="evenodd"' : ""}/>`;
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
    ["new", "Needs drawing", ""],
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
    <div id="spacing" class="spacing"></div>
    <div id="marks" class="marks"></div>
    <div id="rules" class="marks"></div>
    <div id="stage" class="stage"></div>
    <div id="palette" class="palette"></div>
    <textarea id="note" rows="2" placeholder="Note">${escapeHtml(item.note || "")}</textarea>
    <p class="hint">↵ confirm · Tab / ⇧Tab move · Esc reverts keys · click a form to map it whole · marks: ↑/↓ in dx, dy nudge by 5</p>`;
  renderSpacing();
  renderMarks();
  renderRules();
  renderStage();
  renderPalette();
  $("#keys").focus();
}

function usedKeys() {
  const used = new Set();
  for (const item of Object.values(state.entries)) {
    for (const keys of [item.keys, ...Object.values(item.cuts || {}), ...Object.values(item.after || {})]) {
      for (const key of keys || "") used.add(key);
    }
    for (const mark of item.marks || []) used.add(mark.key);
  }
  return used;
}

function renderPalette() {
  const used = usedKeys();
  const keys = Object.keys(legacy().keys).filter((key) => key !== " ");
  const tile = (key) =>
    `<button class="pkey${used.has(key) ? "" : " unused"}" data-key="${escapeAttr(key)}" title="add ${escapeAttr(key)}">` +
    `${legacySvg(keyParts(key), 56)}<code>${escapeHtml(key)}</code></button>`;
  $("#palette").innerHTML =
    `<h3>Not used anywhere yet</h3><div class="pkeys">${keys.filter((key) => !used.has(key)).map(tile).join("")}</div>` +
    `<details><summary>All keys</summary><div class="pkeys">${keys.map(tile).join("")}</div></details>`;
}

function addKey(key) {
  const input = $("#keys");
  const start = input.selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? start;
  input.value = input.value.slice(0, start) + key + input.value.slice(end);
  input.focus();
  input.setSelectionRange(start + key.length, start + key.length);
  editKeys(input.value);
}

function renderStatus() {
  const item = entry(state.ui.current);
  const chip = $("#target .t-head .chip");
  if (chip) {
    chip.className = `chip s-${item.status}`;
    chip.textContent = item.status;
  }
  for (const button of document.querySelectorAll("#target [data-status]")) {
    button.classList.toggle("on", button.dataset.status === item.status);
  }
}

function renderStage() {
  const name = state.ui.current;
  const info = target(name);
  const cut = state.ui.cut;
  const drawn = hasDrawing(entry(name));
  $("#stage").innerHTML = `
    <div class="main-figures">
      <figure><figcaption>CMs ${escapeHtml(cutName(cut))}</figcaption>${legacySvg(namedParts(name), 150, "big")}</figure>
      ${info.reference ? `<figure><figcaption>Unicode</figcaption>${referenceSvg(info.reference, 150)}</figure>` : ""}
      ${Object.keys(entry(name).after || {})
        .filter((previous) => groupExample(previous))
        .map(
          (previous) =>
            `<figure><figcaption>after ${escapeHtml(previous)}${previous.startsWith("@") ? `<br>(${escapeHtml(groupExample(previous))})` : ""}</figcaption>${legacySvg(
              [...namedParts(groupExample(previous)), ...namedParts(name, cut, groupExample(previous)).map((part) => ({ ...part, highlight: true }))],
              150,
              "big",
            )}</figure>`,
        )
        .join("")}
      ${
        AUTO_KINDS.includes(info.kind) && drawn
          ? `<figure><figcaption>From parts</figcaption>${legacySvg(info.atoms.flatMap((atom) => namedParts(atom)), 150, "big")}</figure>`
          : ""
      }
    </div>
    <div id="forms" class="forms"></div>`;
  renderUsage();
}

function renderMarks() {
  const item = entry(state.ui.current);
  const glyphs = legacy().keys;
  const rows = (item.marks || []).map((mark, index) => {
    const glyph = glyphs[mark.key];
    const contours = (glyph?.contours || [])
      .map((contour, contourIndex) => {
        const on = !mark.contours || mark.contours.includes(contourIndex);
        return `<button class="contour ${on ? "on" : ""}" data-contour="${contourIndex}" title="contour ${contourIndex}">${runSvg([{ ...contour, advance: glyph.advance }], legacy(), 34)}</button>`;
      })
      .join("");
    return `<div class="mark" data-index="${index}">
      <label>Mark from <input class="m-key" value="${escapeAttr(mark.key)}" maxlength="1" spellcheck="false"></label>
      <span class="contours">${contours || `<span class="hint">no such key</span>`}</span>
      <label>on <select class="m-on"><option value="">—</option>${[...(keysFor(item) || "")]
        .map((key, keyIndex) => `<option value="${keyIndex}" ${mark.on === keyIndex ? "selected" : ""}>${keyIndex + 1}: ${escapeHtml(key)}</option>`)
        .join("")}</select></label>
      <label>dx <input class="m-dx" type="number" step="5" value="${mark.dx}"></label>
      <label>dy <input class="m-dy" type="number" step="5" value="${mark.dy}"></label>
      <button class="m-del" title="Remove mark">×</button>
    </div>`;
  });
  $("#marks").innerHTML = rows.join("") + `<button id="add-mark" class="add-mark">+ Mark</button>`;
}

function renderSpacing() {
  const item = entry(state.ui.current);
  const keys = keysFor(item) || "";
  if (keys.length < 2) {
    $("#spacing").innerHTML = "";
    return;
  }
  $("#spacing").innerHTML =
    `<span class="hint">Spacing before</span>` +
    [...keys]
      .map((key, index) =>
        index
          ? `<label><kbd>${escapeHtml(key)}</kbd><input class="s-shift" type="number" step="10" data-index="${index}" value="${Number(item.shift?.[index] || 0)}"></label>`
          : "",
      )
      .join("");
}

function renderRules() {
  const item = entry(state.ui.current);
  if (item.kind !== "piece") {
    $("#rules").innerHTML = "";
    return;
  }
  const pieces = state.data.targets.filter((info) => info.kind === "piece").map((info) => info.name);
  const rows = Object.entries(item.after || {}).map(
    ([previous, keys], index) => `<div class="mark rule" data-index="${index}">
      <label>After <input class="r-prev" list="piece-names" value="${escapeAttr(previous)}" spellcheck="false"></label>
      <label>type <input class="r-keys" value="${escapeAttr(keys)}" spellcheck="false"></label>
      <button class="r-del" title="Remove rule">×</button>
    </div>`,
  );
  $("#rules").innerHTML =
    rows.join("") +
    `<datalist id="piece-names">${[...Object.keys(state.groups).map((group) => `@${group}`), ...pieces].map((piece) => `<option value="${escapeAttr(piece)}">`).join("")}</datalist>` +
    `<button id="add-rule" class="add-mark">+ After rule</button>`;
}

function editRules(change, { rerender = false } = {}) {
  const item = entry(state.ui.current);
  const rules = Object.entries(item.after || {});
  change(rules);
  item.after = Object.fromEntries(rules.filter(([previous]) => previous));
  if (["todo", "ok"].includes(item.status) && hasDrawing(item)) item.status = "draft";
  if (rerender) renderRules();
  renderStage();
  renderStatus();
  scheduleSave(item.name);
}

function editMarks(change, { rerenderMarks = false } = {}) {
  const item = entry(state.ui.current);
  item.marks = item.marks ? item.marks.map((mark) => ({ ...mark })) : [];
  change(item.marks);
  if (hasDrawing(item) && ["todo", "ok"].includes(item.status)) item.status = "draft";
  if (rerenderMarks) renderMarks();
  renderStage();
  renderStatus();
  renderProgress();
  scheduleSave(item.name);
}

function useChip(variant) {
  const code = `U+${variant.codePoint.toString(16).toUpperCase()}${variant.fvs ? ` + FVS${variant.fvs}` : ""}`;
  const fvs = variant.fvs ? ` <b>fvs${variant.fvs}</b>` : "";
  return `<i class="use ${variant.default ? "" : "alt"}" title="${code}${variant.default ? "" : " (variant)"}">${escapeHtml(variant.label)} ${variant.position}${fvs}</i>`;
}

// One card per written form: the drawing depends only on it, not on which letter uses it.
function renderUsage() {
  const element = $("#forms");
  if (!element) return;
  const name = state.ui.current;
  const groups = new Map();
  for (const id of target(name).usedBy || []) {
    const variant = state.variantsById[id];
    if (!groups.has(variant.written)) groups.set(variant.written, []);
    groups.get(variant.written).push(variant);
  }
  if (!groups.size) {
    element.innerHTML = "";
    return;
  }
  const cards = [...groups].map(([written, uses]) => {
    const first = uses[0];
    const onlyVariants = uses.every((variant) => !variant.default);
    return `<div class="card ${onlyVariants ? "alt" : ""}${written === name ? " self" : ""}" data-written="${escapeAttr(written)}" title="Map ${escapeAttr(written)} as a whole form">
      <header><code>${escapeHtml(written)}</code></header>
      <div class="pair">${referenceSvg(first.reference, 64)}${legacySvg(variantParts(first, name), 64)}</div>
      <footer>${uses.map(useChip).join("")}</footer>
    </div>`;
  });
  const total = target(name).usedBy.length;
  element.innerHTML = `<h3>${groups.size} written forms <span class="hint">used by ${total} letter forms · Unicode left · CMs right, this piece highlighted</span></h3><div class="cards">${cards.join("")}</div>`;
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
  const hasKeys = hasDrawing(item);
  if (hasKeys && ["todo", "ok", "auto"].includes(item.status)) item.status = "draft";
  if (!hasKeys && item.status === "draft") item.status = AUTO_KINDS.includes(item.kind) ? "auto" : "todo";
  renderSpacing();
  renderStage();
  renderStatus();
  renderProgress();
  scheduleSave(item.name);
}

function setStatus(status) {
  const item = entry(state.ui.current);
  if (status === "ok" && !hasDrawing(item)) {
    flash("Nothing to confirm: type the keys first, or mark it Not in CMs.");
    return;
  }
  if (status === "auto") {
    item.keys = null;
    item.cuts = {};
    item.marks = [];
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
    body: JSON.stringify({ name, keys: item.keys, status: item.status, note: item.note, cuts: item.cuts || {}, marks: item.marks || [], after: item.after || {}, shift: item.shift || {}, trim: item.trim || "" }),
  });
  const result = await response.json();
  if (result.error) {
    flash(`Not saved: ${result.error}`);
    return;
  }
  state.entries = result.entries;
  state.groups = result.groups || state.groups;
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
    if (event.target.classList.contains("s-shift")) {
      const item = entry(state.ui.current);
      const index = event.target.dataset.index;
      item.shift = { ...(item.shift || {}), [index]: Math.round(Number(event.target.value) || 0) };
      if (!item.shift[index]) delete item.shift[index];
      if (["todo", "ok"].includes(item.status)) item.status = "draft";
      renderStage();
      renderStatus();
      scheduleSave(item.name);
      return;
    }
    const rule = event.target.closest(".rule");
    if (rule) {
      const index = Number(rule.dataset.index);
      if (event.target.classList.contains("r-keys")) editRules((rules) => (rules[index][1] = event.target.value));
      return;
    }
    const row = event.target.closest(".mark");
    if (row) {
      const index = Number(row.dataset.index);
      if (event.target.classList.contains("m-key")) {
        const key = event.target.value;
        if (!key) return;
        editMarks((marks) => (marks[index] = { ...marks[index], key, contours: null }), { rerenderMarks: true });
        $(`.mark[data-index="${index}"] .m-key`)?.focus();
      } else if (event.target.classList.contains("m-dx") || event.target.classList.contains("m-dy")) {
        const field = event.target.classList.contains("m-dx") ? "dx" : "dy";
        const value = Math.round(Number(event.target.value) || 0);
        editMarks((marks) => (marks[index] = { ...marks[index], [field]: value }));
      }
      return;
    }
    if (event.target.id === "keys") editKeys(event.target.value);
    if (event.target.id === "note") {
      entry(state.ui.current).note = event.target.value;
      scheduleSave(state.ui.current, 800);
    }
  });
  work.addEventListener("change", (event) => {
    if (event.target.classList.contains("m-on")) {
      const index = Number(event.target.closest(".mark").dataset.index);
      const value = event.target.value === "" ? null : Number(event.target.value);
      editMarks((marks) => (marks[index] = { ...marks[index], on: value }));
      return;
    }
    if (event.target.classList.contains("r-prev")) {
      const index = Number(event.target.closest(".rule").dataset.index);
      editRules((rules) => (rules[index][0] = event.target.value.trim()), { rerender: true });
      return;
    }
    if (event.target.id !== "cut-only") return;
    const item = entry(state.ui.current);
    if (event.target.checked) item.cuts = { ...(item.cuts || {}), [state.ui.cut]: item.keys || "" };
    else if (item.cuts) delete item.cuts[state.ui.cut];
    renderTarget();
    renderUsage();
    scheduleSave(item.name, 0);
  });
  work.addEventListener("click", (event) => {
    const paletteKey = event.target.closest(".pkey")?.dataset.key;
    if (paletteKey) {
      addKey(paletteKey);
      return;
    }
    if (event.target.closest("#add-rule")) {
      const pieces = state.data.targets.filter((info) => info.kind === "piece").map((info) => info.name);
      const used = Object.keys(entry(state.ui.current).after || {});
      const previous = pieces.find((piece) => !used.includes(piece));
      editRules((rules) => rules.push([previous, keysFor(entry(state.ui.current)) || ""]), { rerender: true });
      $(`.rule[data-index="${Object.keys(entry(state.ui.current).after || {}).length - 1}"] .r-prev`)?.select();
      return;
    }
    if (event.target.closest(".r-del")) {
      const index = Number(event.target.closest(".rule").dataset.index);
      editRules((rules) => rules.splice(index, 1), { rerender: true });
      return;
    }
    if (event.target.closest("#add-mark")) {
      editMarks((marks) => marks.push({ key: "N", contours: [1], dx: 0, dy: 0 }), { rerenderMarks: true });
      return;
    }
    const row = event.target.closest(".mark");
    if (row) {
      const index = Number(row.dataset.index);
      if (event.target.closest(".m-del")) {
        editMarks((marks) => marks.splice(index, 1), { rerenderMarks: true });
        return;
      }
      const contour = event.target.closest(".contour");
      if (contour) {
        const contourIndex = Number(contour.dataset.contour);
        editMarks(
          (marks) => {
            const mark = marks[index];
            const count = legacy().keys[mark.key]?.contours.length || 0;
            const current = mark.contours ?? [...Array(count).keys()];
            const next = current.includes(contourIndex) ? current.filter((value) => value !== contourIndex) : [...current, contourIndex].sort();
            mark.contours = next.length === count ? null : next;
          },
          { rerenderMarks: true },
        );
      }
      return;
    }
    const status = event.target.closest("[data-status]")?.dataset.status;
    if (status) setStatus(status);
  });

  document.addEventListener("keydown", (event) => {
    const inText =
      event.target.tagName === "TEXTAREA" || event.target.id === "search" || Boolean(event.target.closest?.(".marks, .spacing"));
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
  state.data.drawings = data.drawings;
  renderAll();
}

boot();
