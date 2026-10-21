"use strict";

/* ------------------------------------------------------------------ *
 * CMs ↔ Unicode — form elicitation editor
 *
 * The page never writes a file itself: every change is POSTed to the
 * little local server (server.py), which writes state/state.json and
 * state/latest.md.  Nothing needs to be copied or saved by hand.
 * ------------------------------------------------------------------ */

const $ = (sel, root = document) => root.querySelector(sel);

const POSITION_NAMES = {
  isol: "isolated",
  init: "initial",
  medi: "medial",
  fina: "final",
};

const INVISIBLE = new Set([0x180b, 0x180c, 0x180d, 0x180e, 0x180f, 0x202f, 0x200c, 0x200d, 0xfeff]);

let FORMS = null;
let CMS = null;

const state = {
  version: 1,
  family: "CMSUG",
  current: null,
  items: {},
  free: { unicode: "ᠮᠣᠩᠭᠣᠯ", legacy: "" },
  freePairs: [],
  ui: {
    tab: "forms",
    defaultsOnly: true,
    hideDone: false,
    search: "",
    topToBottom: true,
    zoom: 1.25,
  },
  revision: 0,
  updated: null,
};

const els = {};

/* ------------------------------------------------------------------ *
 * boot
 * ------------------------------------------------------------------ */

async function boot() {
  cacheElements();

  const [forms, cms, saved] = await Promise.all([
    fetch("data/forms.json").then((r) => r.json()),
    fetch("data/cms-glyphs.json").then((r) => r.json()),
    fetch("api/state").then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]);

  FORMS = forms;
  CMS = cms;
  mergeSaved(saved);

  buildFamilySelect();
  syncControls();
  wireEvents();
  if (!state.current) state.current = defaultStartItem();

  renderAll();
  els.legacy.focus();
}

function cacheElements() {
  Object.assign(els, {
    progress: $("#progress"),
    saved: $("#saved"),
    search: $("#search"),
    defaultsOnly: $("#defaults-only"),
    hideDone: $("#hide-done"),
    list: $("#list"),
    sideFoot: $("#side-foot"),
    formsView: $("#forms-view"),
    freeView: $("#free-view"),
    refStage: $("#ref-stage"),
    refPos: $("#ref-pos"),
    refMeta: $("#ref-meta"),
    refCodepoints: $("#ref-codepoints"),
    family: $("#family"),
    cmsStage: $("#cms-stage"),
    legacy: $("#legacy"),
    keys: $("#keys"),
    order: $("#order"),
    showInvisibles: $("#show-invisibles"),
    clear: $("#clear"),
    note: $("#note"),
    prev: $("#prev"),
    next: $("#next"),
    freeUnicode: $("#free-unicode"),
    freeLegacy: $("#free-legacy"),
    freeUnicodeStage: $("#free-unicode-stage"),
    freeLegacyStage: $("#free-legacy-stage"),
    freeFamilyLabel: $("#free-family-label"),
    savePair: $("#save-pair"),
    freeSaved: $("#free-saved"),
    pairs: $("#pairs"),
  });
}

function mergeSaved(saved) {
  if (!saved || typeof saved !== "object") return;
  state.family = saved.family || state.family;
  state.current = saved.current || null;
  state.items = saved.items || {};
  state.free = { ...state.free, ...(saved.free || {}) };
  state.freePairs = Array.isArray(saved.freePairs) ? saved.freePairs : [];
  state.ui = { ...state.ui, ...(saved.ui || {}) };
  state.revision = saved.revision || 0;
}

function syncControls() {
  els.defaultsOnly.checked = state.ui.defaultsOnly;
  els.hideDone.checked = state.ui.hideDone;
  els.order.checked = state.ui.topToBottom;
  els.showInvisibles.checked = Boolean(state.ui.showInvisibles);
  els.search.value = state.ui.search || "";
}

function buildFamilySelect() {
  els.family.innerHTML = "";
  for (const [stem, family] of Object.entries(CMS.families)) {
    const option = document.createElement("option");
    option.value = stem;
    option.textContent = `${family.label} · regular`;
    els.family.append(option);
  }
  els.family.value = state.family;
  els.family.title = "Regular cut (CMS*.TTF), not the DP letterpress cut";
  $("#free-family-label").textContent = CMS.families[state.family]?.label || "";
}

/* ------------------------------------------------------------------ *
 * items
 * ------------------------------------------------------------------ */

function visibleItems() {
  const query = state.ui.search.trim().toLowerCase();
  return FORMS.items.filter((item) => {
    if (state.ui.defaultsOnly && !item.default) return false;
    if (state.ui.hideDone && state.items[item.id]?.verdict) return false;
    if (!query) return true;
    const haystack = [item.letter, item.charName, item.position, item.gb, item.id]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function defaultStartItem() {
  const items = visibleItems();
  const firstOpen =
    items.find((item) => item.default && !state.items[item.id]?.verdict) ||
    items.find((item) => !state.items[item.id]?.verdict);
  return (firstOpen || items[0] || FORMS.items[0]).id;
}

function currentItem() {
  return FORMS.items.find((item) => item.id === state.current) || null;
}

function record(id) {
  if (!state.items[id]) state.items[id] = {};
  return state.items[id];
}

function fvsLabel(item) {
  if (item.default) return "";
  if (item.fvs === "0") return " · context";
  return ` · FVS${item.fvs}`;
}

function labelOf(item) {
  return `${item.letter} · ${POSITION_NAMES[item.position]}${fvsLabel(item)}`;
}

function stats() {
  let doneAll = 0;
  let doneDefaults = 0;
  for (const item of FORMS.items) {
    if (state.items[item.id]?.verdict) {
      doneAll += 1;
      if (item.default) doneDefaults += 1;
    }
  }
  return {
    all: FORMS.items.length,
    defaults: FORMS.items.filter((item) => item.default).length,
    doneAll,
    doneDefaults,
  };
}

/* ------------------------------------------------------------------ *
 * svg
 * ------------------------------------------------------------------ */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function referenceSvg(item, viewBox) {
  return `<svg viewBox="${viewBox.join(" ")}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><path d="${item.path}"/></svg>`;
}

function boundsViewBox(bounds, padding = 40) {
  const [x0, y0, x1, y1] = bounds;
  const width = Math.max(x1 - x0, 1) + padding * 2;
  const height = Math.max(y1 - y0, 1) + padding * 2;
  return [x0 - padding, y0 - padding, width, height];
}

function zoomedViewBox(item) {
  const [x, y, width, height] = FORMS.meta.viewBox;
  const zoom = state.ui.zoom || 1;
  const [x0, y0, x1, y1] = item.bounds;
  const centerX = (x0 + x1) / 2;
  const centerY = (y0 + y1) / 2;
  const w = width / zoom;
  const h = height / zoom;
  return [centerX - w / 2, centerY - h / 2, w, h];
}

/**
 * Lay a typed legacy string out the way the 1998 font was set: glyphs side by
 * side in font space, advancing by their own widths, then the whole run turned
 * 90° clockwise.  The outlines were drawn rotated counter-clockwise, so this
 * puts them upright and turns the run into a vertical column reading top to
 * bottom in typing order.  The font's horizontal advance is the vertical step.
 */
function legacyRun(text, family) {
  const glyphs = CMS.families[family].glyphs;
  const characters = [...text];
  const sequence = state.ui.topToBottom ? characters : characters.slice().reverse();

  let advance = 0;
  let box = null;
  const parts = [];

  for (const character of sequence) {
    const glyph = glyphs[character];
    if (!glyph) {
      if (state.ui.showInvisibles) {
        parts.push(
          `<rect x="${advance + 40}" y="880" width="420" height="240" rx="18" class="unmapped"/>`
        );
      }
      advance += 500;
      continue;
    }
    parts.push(`<path d="${glyph.d}" transform="translate(${advance} 0)"/>`);
    const [x0, y0, x1, y1] = glyph.bounds;
    const gx0 = advance + x0;
    const gx1 = advance + x1;
    box = box
      ? [Math.min(box[0], gx0), Math.min(box[1], y0), Math.max(box[2], gx1), Math.max(box[3], y1)]
      : [gx0, y0, gx1, y1];
    advance += glyph.advance;
  }

  if (!box) return null;

  // rotate(90): (x, y) -> (-y, x)
  const rotated = [-box[3], box[0], -box[1], box[2]];
  return { parts, box: rotated };
}

function legacySvg(run, viewBox) {
  const [vx, vy, vw, vh] = viewBox;
  const [x0, y0, x1, y1] = run.box;
  const tx = vx + vw / 2 - (x0 + x1) / 2;
  const ty = vy + vh / 2 - (y0 + y1) / 2;
  return `<svg viewBox="${viewBox.join(" ")}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><g transform="translate(${tx} ${ty}) rotate(90)">${run.parts.join("")}</g></svg>`;
}

function legacySvgFitted(run) {
  const [x0, y0, x1, y1] = run.box;
  const padding = 50;
  const viewBox = [x0 - padding, y0 - padding, x1 - x0 + padding * 2, y1 - y0 + padding * 2];
  const pxPerUnit = Math.min(0.13, 340 / viewBox[3], 420 / viewBox[2]);
  const width = Math.round(viewBox[2] * pxPerUnit);
  const height = Math.round(viewBox[3] * pxPerUnit);
  return `<svg width="${width}" height="${height}" viewBox="${viewBox.join(" ")}" aria-hidden="true"><g transform="rotate(90)">${run.parts.join("")}</g></svg>`;
}

/* ------------------------------------------------------------------ *
 * render
 * ------------------------------------------------------------------ */

function renderAll() {
  const tab = state.ui.tab || "forms";
  els.formsView.hidden = tab !== "forms";
  els.freeView.hidden = tab !== "free";
  document.querySelectorAll(".tabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tab);
  });

  renderProgress();
  renderList();
  if (tab === "forms") renderPanes();
  else renderFree();
}

function renderProgress() {
  const { doneDefaults, defaults, doneAll, all } = stats();
  els.progress.textContent = `${doneDefaults} / ${defaults} default  ·  ${doneAll} / ${all} all`;
}

function renderList() {
  const items = visibleItems();
  const fragment = document.createDocumentFragment();

  for (const item of items) {
    const status = state.items[item.id]?.verdict || "";
    const row = document.createElement("div");
    row.className = "row" + (item.id === state.current ? " active" : "");
    row.dataset.id = item.id;
    row.setAttribute("role", "option");
    row.setAttribute("aria-selected", item.id === state.current ? "true" : "false");

    row.innerHTML = `
      <div class="row-glyph">${referenceSvg(item, boundsViewBox(item.bounds, 30))}</div>
      <div class="row-main">
        <div class="row-title"><span class="alias">${escapeHtml(item.letter)}</span> <span class="pos">· ${POSITION_NAMES[item.position]}${fvsLabel(item)}</span></div>
        <div class="row-sub">U+${item.codePoints[0].toString(16).toUpperCase().padStart(4, "0")}${item.default ? " · default" : ""}${item.archaic ? " · archaic" : ""}</div>
      </div>
      <div class="dot ${status}" title="${status || "unconfirmed"}"></div>`;
    fragment.append(row);
  }

  els.list.replaceChildren(fragment);

  const { doneDefaults, defaults, doneAll, all } = stats();
  els.sideFoot.innerHTML = `<span>${doneDefaults}/${defaults} default</span><span>${doneAll}/${all} all</span>`;
}

function renderPanes() {
  const item = currentItem();
  if (!item) return;

  const viewBox = zoomedViewBox(item);
  els.refStage.innerHTML = referenceSvg(item, viewBox);
  els.refPos.textContent = POSITION_NAMES[item.position];
  els.refMeta.innerHTML = `
    <div><span class="name">${escapeHtml(item.charName.replace("MONGOLIAN LETTER ", ""))}</span>
    <span class="dim">· ${POSITION_NAMES[item.position]}${fvsLabel(item)}${item.default ? " · default" : ""}${item.archaic ? " · archaic" : ""}</span></div>
    <div class="dim">${item.written}${item.writtenPosition !== item.position ? ` (borrowed from ${POSITION_NAMES[item.writtenPosition]})` : ""}${item.conditions.length ? " · " + item.conditions.join(", ") : ""}</div>
    ${item.gb ? `<div class="gb">GB ${escapeHtml(item.gb)}</div>` : ""}`;

  els.refCodepoints.innerHTML = item.codePoints
    .map((cp) => {
      const hex = cp.toString(16).toUpperCase().padStart(4, "0");
      const hidden = INVISIBLE.has(cp) ? " hidden-cp" : "";
      return `<span class="cp${hidden}" title="${hidden ? "invisible format character" : "character"}">U+${hex}</span>`;
    })
    .join("");

  const stored = state.items[item.id] || {};
  els.legacy.value = stored.typed || "";
  els.note.value = stored.note || "";

  renderCmsStage();
  renderKeys();

  document.querySelectorAll(".verdict button.v").forEach((button) => {
    button.classList.toggle("chosen", button.dataset.v === stored.verdict);
  });
}

function renderCmsStage() {
  const item = currentItem();
  if (!item) return;
  const run = legacyRun(els.legacy.value, state.family);
  const viewBox = zoomedViewBox(item);
  els.cmsStage.classList.toggle("empty", !run);
  els.cmsStage.innerHTML = run ? legacySvg(run, viewBox) : "";
}

function renderKeys() {
  const text = els.legacy.value;
  if (!text) {
    els.keys.innerHTML = `<span class="key blank">no keys yet</span>`;
    return;
  }
  els.keys.innerHTML = [...text]
    .map((character) => {
      if (character === " ") return `<span class="key blank">␣</span>`;
      const shifted = character !== character.toLowerCase();
      return `<span class="key${shifted ? " shift" : ""}">${escapeHtml(character)}</span>`;
    })
    .join("");
}

/* ------------------------------------------------------------------ *
 * free mode
 * ------------------------------------------------------------------ */

function renderFree() {
  els.freeUnicode.value = state.free.unicode;
  els.freeLegacy.value = state.free.legacy;
  els.freeFamilyLabel.textContent = CMS.families[state.family]?.label || "";
  renderFreeUnicode();
  renderFreeLegacy();
  renderPairs();
}

function renderFreeUnicode() {
  const text = state.free.unicode;
  els.freeUnicodeStage.innerHTML = text
    ? `<div class="vertical">${escapeHtml(text)}</div>`
    : `<span class="key blank">type Unicode text…</span>`;
}

function renderFreeLegacy() {
  const run = legacyRun(state.free.legacy, state.family);
  els.freeLegacyStage.innerHTML = run
    ? legacySvgFitted(run)
    : `<span class="key blank">type CMs keys…</span>`;
}

function renderPairs() {
  els.pairs.innerHTML = state.freePairs
    .slice()
    .reverse()
    .map(
      (pair) => `
      <div class="pair">
        <span class="u">${escapeHtml(pair.unicode)}</span>
        <span class="l">${escapeHtml(pair.legacy)}</span>
        <span class="f">${escapeHtml(pair.family || "")} · ${new Date(pair.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
      </div>`
    )
    .join("");
}

/* ------------------------------------------------------------------ *
 * navigation & verdicts
 * ------------------------------------------------------------------ */

function selectItem(id) {
  state.current = id;
  renderPanes();
  renderList();
  els.legacy.focus();
}

function advance(direction = 1) {
  const items = visibleItems();
  if (!items.length) return;
  const currentIndex = Math.max(0, items.findIndex((item) => item.id === state.current));
  let nextIndex = -1;
  for (let step = 1; step <= items.length; step += 1) {
    const index = (currentIndex + direction * step + items.length * 2) % items.length;
    if (!state.items[items[index].id]?.verdict) {
      nextIndex = index;
      break;
    }
  }
  if (nextIndex < 0) nextIndex = (currentIndex + direction + items.length) % items.length;
  state.current = items[nextIndex].id;
  renderProgress();
  renderPanes();
  renderList();
  els.legacy.focus();
}

function setVerdict(verdict) {
  const item = currentItem();
  if (!item) return;
  const entry = record(item.id);
  entry.verdict = verdict;
  entry.typed = els.legacy.value;
  entry.note = els.note.value;
  entry.label = labelOf(item);
  entry.ts = Date.now();
  advance(1);
  scheduleSave();
}

/* ------------------------------------------------------------------ *
 * persistence
 * ------------------------------------------------------------------ */

let saveTimer = null;

function setSaved(text, className = "") {
  els.saved.textContent = text;
  els.saved.className = "saved" + (className ? " " + className : "");
}

function scheduleSave() {
  setSaved("saving…", "saving");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 300);
}

async function save() {
  state.revision = (state.revision || 0) + 1;
  state.stats = stats();
  state.currentLabel = currentItem() ? labelOf(currentItem()) : "";
  state.updated = new Date().toISOString();
  try {
    const response = await fetch("api/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
    if (!response.ok) throw new Error(String(response.status));
    setSaved(
      "saved " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      "ok"
    );
  } catch (error) {
    setSaved("not saved — is server.py running?", "err");
  }
}

window.addEventListener("beforeunload", () => {
  try {
    const blob = new Blob([JSON.stringify(state)], { type: "application/json" });
    navigator.sendBeacon("api/state", blob);
  } catch (error) {
    /* best effort */
  }
});

/* ------------------------------------------------------------------ *
 * events
 * ------------------------------------------------------------------ */

function wireEvents() {
  document.querySelectorAll(".tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      state.ui.tab = button.dataset.tab;
      renderAll();
    });
  });

  els.search.addEventListener("input", () => {
    state.ui.search = els.search.value;
    renderList();
    scheduleSave();
  });

  els.defaultsOnly.addEventListener("change", () => {
    state.ui.defaultsOnly = els.defaultsOnly.checked;
    if (!visibleItems().some((item) => item.id === state.current)) {
      state.current = defaultStartItem();
    }
    renderList();
    renderPanes();
    scheduleSave();
  });

  els.hideDone.addEventListener("change", () => {
    state.ui.hideDone = els.hideDone.checked;
    renderList();
    scheduleSave();
  });

  els.list.addEventListener("click", (event) => {
    const row = event.target.closest(".row");
    if (row) selectItem(row.dataset.id);
  });

  els.family.addEventListener("change", () => {
    state.family = els.family.value;
    $("#free-family-label").textContent = CMS.families[state.family]?.label || "";
    renderPanes();
    renderFree();
    scheduleSave();
  });

  els.legacy.addEventListener("input", () => {
    const item = currentItem();
    if (item) {
      const entry = record(item.id);
      entry.typed = els.legacy.value;
      entry.label = labelOf(item);
    }
    renderCmsStage();
    renderKeys();
    scheduleSave();
  });

  els.legacy.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      setVerdict("same");
    } else if (event.key === "Escape") {
      event.preventDefault();
      els.legacy.value = "";
      els.legacy.dispatchEvent(new Event("input"));
      els.legacy.focus();
    } else if (event.key === "Tab") {
      event.preventDefault();
      advance(event.shiftKey ? -1 : 1);
    }
  });

  els.note.addEventListener("input", () => {
    const item = currentItem();
    if (item) record(item.id).note = els.note.value;
    scheduleSave();
  });

  document.querySelectorAll(".verdict button.v").forEach((button) => {
    button.addEventListener("click", () => setVerdict(button.dataset.v));
  });

  els.prev.addEventListener("click", () => advance(-1));
  els.next.addEventListener("click", () => advance(1));

  els.clear.addEventListener("click", () => {
    els.legacy.value = "";
    els.legacy.dispatchEvent(new Event("input"));
    els.legacy.focus();
  });

  els.order.addEventListener("change", () => {
    state.ui.topToBottom = els.order.checked;
    renderCmsStage();
    scheduleSave();
  });

  els.showInvisibles.addEventListener("change", () => {
    state.ui.showInvisibles = els.showInvisibles.checked;
    renderCmsStage();
    scheduleSave();
  });

  els.freeUnicode.addEventListener("input", () => {
    state.free.unicode = els.freeUnicode.value;
    renderFreeUnicode();
    scheduleSave();
  });

  els.freeLegacy.addEventListener("input", () => {
    state.free.legacy = els.freeLegacy.value;
    renderFreeLegacy();
    scheduleSave();
  });

  els.savePair.addEventListener("click", () => {
    if (!state.free.unicode && !state.free.legacy) return;
    state.freePairs.push({
      unicode: state.free.unicode,
      legacy: state.free.legacy,
      family: state.family,
      ts: Date.now(),
    });
    renderPairs();
    els.freeSaved.textContent = "pair saved";
    setTimeout(() => (els.freeSaved.textContent = ""), 2000);
    scheduleSave();
  });

  window.addEventListener("keydown", (event) => {
    if (event.altKey && event.key === "ArrowLeft") {
      event.preventDefault();
      advance(-1);
    } else if (event.altKey && event.key === "ArrowRight") {
      event.preventDefault();
      advance(1);
    }
  });
}

boot().catch((error) => {
  console.error(error);
  document.body.innerHTML = `<pre style="padding:24px;font:13px monospace;color:#9a3733">Could not start the editor.\n\n${escapeHtml(error.stack || error)}</pre>`;
});
