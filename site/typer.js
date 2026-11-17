import { layoutById } from "@gege-mn/typepad";
import { attachKeyboard } from "@gege-mn/typepad/dom";

const KEY = "cms-revived-keyboard";
const fields = [...document.querySelectorAll("textarea.pad")];
const buttons = [...document.querySelectorAll("[data-layout]")];
const hint = document.getElementById("kb-hint");
const sample = JSON.parse(document.getElementById("sample").textContent);

const stored = () => {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
};
// A soft keyboard sends no key positions, so on touch screens the device's own keyboard types.
let layoutId = stored() || (matchMedia("(pointer: coarse)").matches ? "os" : "standard");
const current = () => (layoutId === "os" ? null : layoutById(layoutId));

const choose = (id, focus) => {
  layoutId = id;
  for (const b of buttons) b.setAttribute("aria-pressed", String(b.dataset.layout === id));
  const active = buttons.find((b) => b.dataset.layout === id);
  hint.replaceChildren(
    ...(active ? active.dataset.hint : "").split(/([\u1800-\u18af]+)/).map((part, i) => {
      if (i % 2 === 0) return part;
      const letter = document.createElement("span");
      letter.className = "hk";
      letter.lang = "mn-Mong";
      letter.textContent = part;
      return letter;
    }),
  );
  try {
    localStorage.setItem(KEY, id);
  } catch {}
  if (focus) fields[0].focus();
};

for (const field of fields) {
  field.value = sample;
  attachKeyboard(field, { layout: current });
  field.addEventListener("input", () => {
    for (const other of fields) if (other !== field) other.value = field.value;
  });
}
for (const b of buttons) b.addEventListener("click", () => choose(b.dataset.layout, true));
choose(layoutId, false);

document.getElementById("try-reset").addEventListener("click", () => {
  for (const f of fields) f.value = sample;
});
document.getElementById("try-clear").addEventListener("click", () => {
  for (const f of fields) f.value = "";
  fields[0].focus();
});
