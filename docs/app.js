"use strict";

/* ------------------------------------------------------------------
 * Data layer (mirrors checklist_data.py, backed by localStorage)
 * ------------------------------------------------------------------ */

const STORAGE_KEY = "ecl_data";
const ITEM_LINE_WIDTH = 46;

function defaultData() {
  return {
    aircraft: [
      {
        name: "Cessna 172",
        checklists: [
          {
            name: "Before Start",
            completed: false,
            items: [
              { type: "item", text: "Preflight Inspection", result: "COMPLETE" },
              { type: "item", text: "Seats, Belts, Harnesses", result: "ADJUST, LOCK" },
              { type: "item", text: "Fuel Selector Valve", result: "BOTH" },
              { type: "item", text: "Circuit Breakers", result: "CHECK IN" },
              { type: "item", text: "Parking Brake", result: "SET" },
            ],
          },
          {
            name: "Taxi",
            completed: false,
            items: [
              { type: "item", text: "Flight Instruments", result: "CHECK" },
              { type: "item", text: "Taxi Clearance", result: "OBTAIN" },
              { type: "item", text: "Brakes", result: "CHECK" },
            ],
          },
        ],
      },
    ],
  };
}

const Store = {
  data: null,

  load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        this.data = JSON.parse(raw);
        return;
      }
    } catch (e) { /* fall through to default */ }
    this.data = defaultData();
    this.save();
  },

  save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
  },

  // ---- aircraft ----
  aircraftList() { return this.data.aircraft; },

  getAircraft(name) { return this.data.aircraft.find(a => a.name === name) || null; },

  addAircraft(name) {
    if (this.getAircraft(name)) throw new Error("An aircraft with that name already exists.");
    this.data.aircraft.push({ name, checklists: [] });
    this.save();
  },

  getOrCreateAircraft(name) {
    let ac = this.getAircraft(name);
    if (!ac) {
      ac = { name, checklists: [] };
      this.data.aircraft.push(ac);
      this.save();
    }
    return ac;
  },

  renameAircraft(oldName, newName) {
    if (oldName !== newName && this.getAircraft(newName)) {
      throw new Error("An aircraft with that name already exists.");
    }
    this.getAircraft(oldName).name = newName;
    this.save();
  },

  deleteAircraft(name) {
    this.data.aircraft = this.data.aircraft.filter(a => a.name !== name);
    this.save();
  },

  // ---- checklists ----
  getChecklist(acName, clName) {
    const ac = this.getAircraft(acName);
    if (!ac) return null;
    return ac.checklists.find(c => c.name === clName) || null;
  },

  addChecklist(acName, clName) {
    const ac = this.getAircraft(acName);
    if (this.getChecklist(acName, clName)) {
      throw new Error("A checklist with that name already exists for this aircraft.");
    }
    ac.checklists.push({ name: clName, completed: false, items: [] });
    this.save();
  },

  renameChecklist(acName, oldName, newName) {
    if (oldName !== newName && this.getChecklist(acName, newName)) {
      throw new Error("A checklist with that name already exists for this aircraft.");
    }
    this.getChecklist(acName, oldName).name = newName;
    this.save();
  },

  deleteChecklist(acName, clName) {
    const ac = this.getAircraft(acName);
    ac.checklists = ac.checklists.filter(c => c.name !== clName);
    this.save();
  },

  moveChecklist(acName, clName, delta) {
    const ac = this.getAircraft(acName);
    const idx = ac.checklists.findIndex(c => c.name === clName);
    const newIdx = idx + delta;
    if (newIdx >= 0 && newIdx < ac.checklists.length) {
      const [item] = ac.checklists.splice(idx, 1);
      ac.checklists.splice(newIdx, 0, item);
      this.save();
    }
  },

  setChecklistCompleted(acName, clName, completed) {
    const cl = this.getChecklist(acName, clName);
    if (cl) { cl.completed = completed; this.save(); }
  },

  resetAllChecklists(acName) {
    const ac = this.getAircraft(acName);
    if (!ac) return;
    ac.checklists.forEach(cl => { cl.completed = false; });
    this.save();
  },

  // ---- items ----
  addItem(acName, clName, text, result) {
    const cl = this.getChecklist(acName, clName);
    cl.items.push({ type: "item", text, result: result || "" });
    this.save();
  },

  editItem(acName, clName, index, text, result) {
    const cl = this.getChecklist(acName, clName);
    cl.items[index] = { type: "item", text, result: result || "" };
    this.save();
  },

  insertSeparator(acName, clName, position) {
    const cl = this.getChecklist(acName, clName);
    cl.items.splice(position, 0, { type: "separator" });
    this.save();
  },

  deleteItem(acName, clName, index) {
    const cl = this.getChecklist(acName, clName);
    cl.items.splice(index, 1);
    this.save();
  },

  moveItem(acName, clName, index, delta) {
    const cl = this.getChecklist(acName, clName);
    const newIdx = index + delta;
    if (newIdx >= 0 && newIdx < cl.items.length) {
      const [item] = cl.items.splice(index, 1);
      cl.items.splice(newIdx, 0, item);
      this.save();
    }
  },

  // ---- export / import ----
  exportChecklists(acName, checklistNames) {
    const ac = this.getAircraft(acName);
    if (!ac) return [];
    return ac.checklists
      .filter(cl => !checklistNames || checklistNames.includes(cl.name))
      .map(cl => ({ name: cl.name, items: JSON.parse(JSON.stringify(cl.items)) }));
  },

  uniqueChecklistName(ac, baseName) {
    const existing = new Set(ac.checklists.map(c => c.name));
    if (!existing.has(baseName)) return baseName;
    let n = 2;
    while (existing.has(`${baseName} (${n})`)) n++;
    return `${baseName} (${n})`;
  },

  importChecklists(acName, checklists) {
    const ac = this.getAircraft(acName);
    if (!ac) throw new Error("Aircraft not found.");
    const added = [];
    for (const cl of checklists) {
      const name = this.uniqueChecklistName(ac, String(cl.name || "Imported Checklist"));
      const items = (cl.items || []).map(item => {
        if (typeof item === "string") return { type: "item", text: item, result: "" };
        if (item.type === "separator") return { type: "separator" };
        return { type: "item", text: item.text || "", result: item.result || "" };
      });
      ac.checklists.push({ name, completed: false, items });
      added.push(name);
    }
    this.save();
    return added;
  },
};

function isSeparator(item) { return item.type === "separator"; }

function formatItem(text, result) {
  text = text || "";
  result = (result || "").trim();
  if (!result) return text;
  const dots = ".".repeat(Math.max(3, ITEM_LINE_WIDTH - text.length - result.length));
  return `${text}${dots}${result}`;
}

/* ------------------------------------------------------------------
 * App state / navigation
 * ------------------------------------------------------------------ */

const state = {
  view: "menu", // menu | menuEdit | run | itemEdit
  currentAircraft: "",
  currentChecklist: "",
  selectedChecklistName: null, // in menuEdit list
  selectedItemIndex: null,     // in itemEdit list
};

const el = {
  aircraftSelect: document.getElementById("aircraftSelect"),
  header: document.getElementById("header"),
  main: document.getElementById("main"),
  modalRoot: document.getElementById("modalRoot"),
};

document.getElementById("btnAddAircraft").addEventListener("click", addAircraft);
document.getElementById("btnRenameAircraft").addEventListener("click", renameAircraft);
document.getElementById("btnDeleteAircraft").addEventListener("click", deleteAircraft);
el.aircraftSelect.addEventListener("change", () => {
  state.currentAircraft = el.aircraftSelect.value;
  showMenu();
});

function refreshAircraftSelect() {
  const names = Store.aircraftList().map(a => a.name);
  el.aircraftSelect.innerHTML = "";
  names.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    el.aircraftSelect.appendChild(opt);
  });
  if (names.length) {
    if (!names.includes(state.currentAircraft)) state.currentAircraft = names[0];
    el.aircraftSelect.value = state.currentAircraft;
  } else {
    state.currentAircraft = "";
  }
  showMenu();
}

function addAircraft() {
  const name = (window.prompt("Aircraft name (e.g. Cessna 172):") || "").trim();
  if (!name) return;
  try {
    Store.addAircraft(name);
  } catch (e) {
    window.alert(e.message);
    return;
  }
  state.currentAircraft = name;
  refreshAircraftSelect();
}

function renameAircraft() {
  const old = state.currentAircraft;
  if (!old) return;
  const next = (window.prompt("New name:", old) || "").trim();
  if (!next || next === old) return;
  try {
    Store.renameAircraft(old, next);
  } catch (e) {
    window.alert(e.message);
    return;
  }
  state.currentAircraft = next;
  refreshAircraftSelect();
}

function deleteAircraft() {
  const name = state.currentAircraft;
  if (!name) return;
  if (!window.confirm(`Delete '${name}' and all its checklists?`)) return;
  Store.deleteAircraft(name);
  refreshAircraftSelect();
}

/* ------------------------------------------------------------------
 * View: checklist menu
 * ------------------------------------------------------------------ */

function showMenu() {
  state.view = "menu";
  renderMenu();
}

function currentChecklists() {
  const ac = Store.getAircraft(state.currentAircraft);
  return ac ? ac.checklists : [];
}

function renderMenu() {
  el.header.textContent = state.currentAircraft
    ? `${state.currentAircraft.toUpperCase()} — CHECKLISTS` : "NO AIRCRAFT SELECTED";
  el.main.innerHTML = "";

  const bar = document.createElement("div");
  bar.className = "btn-row spread";
  bar.innerHTML = `
    <button class="btn" id="btnAddChecklist">+ Add Checklist</button>
    <span style="flex:1"></span>
    <button class="btn" id="btnResetAll">Reset All</button>
    <button class="btn" id="btnEditChecklists">Edit Checklists</button>
  `;
  el.main.appendChild(bar);
  bar.querySelector("#btnAddChecklist").addEventListener("click", addChecklist);
  bar.querySelector("#btnResetAll").addEventListener("click", resetAllChecklists);
  bar.querySelector("#btnEditChecklists").addEventListener("click", showMenuEdit);

  const list = document.createElement("div");
  list.className = "scroll";
  el.main.appendChild(list);

  const checklists = currentChecklists();
  if (!checklists.length) {
    const msg = document.createElement("div");
    msg.className = "empty-msg";
    msg.textContent = state.currentAircraft
      ? "No checklists yet. Use '+ Add Checklist' to create one."
      : "Add an aircraft above to get started.";
    list.appendChild(msg);
    return;
  }

  checklists.forEach(cl => {
    const tile = document.createElement("button");
    tile.className = "tile" + (cl.completed ? " completed" : "");
    tile.textContent = (cl.completed ? "✓  " : "") + cl.name;
    tile.addEventListener("click", () => openChecklist(cl.name));
    list.appendChild(tile);
  });
}

function openChecklist(name) {
  state.currentChecklist = name;
  const cl = Store.getChecklist(state.currentAircraft, name);
  if (cl && cl.completed) Store.setChecklistCompleted(state.currentAircraft, name, false);
  showRun();
}

function resetAllChecklists() {
  const acName = state.currentAircraft;
  if (!acName) { window.alert("Select an aircraft first."); return; }
  if (!currentChecklists().length) { window.alert("No checklists to reset."); return; }
  if (!window.confirm(`Reset all checklists for '${acName}'? This clears their completed status - it doesn't delete anything.`)) return;
  Store.resetAllChecklists(acName);
  renderMenu();
}

function addChecklist() {
  const acName = state.currentAircraft;
  if (!acName) { window.alert("Add an aircraft first."); return; }
  const name = (window.prompt("Checklist name (e.g. Before Takeoff):") || "").trim();
  if (!name) return;
  try {
    Store.addChecklist(acName, name);
  } catch (e) {
    window.alert(e.message);
    return;
  }
  renderMenu();
}

/* ------------------------------------------------------------------
 * View: checklist menu - edit (rename / delete / reorder / export / import)
 * ------------------------------------------------------------------ */

function showMenuEdit() {
  state.view = "menuEdit";
  state.selectedChecklistName = null;
  renderMenuEdit();
}

function renderMenuEdit() {
  el.header.textContent = `${state.currentAircraft.toUpperCase()} — EDIT CHECKLISTS`;
  el.main.innerHTML = "";

  const bar = document.createElement("div");
  bar.className = "btn-row";
  bar.innerHTML = `
    <button class="btn btn-accent" id="btnDone">Done</button>
    <span style="flex:1"></span>
    <button class="btn" id="btnExportAll">Export All</button>
    <button class="btn" id="btnImport">Import</button>
  `;
  el.main.appendChild(bar);
  bar.querySelector("#btnDone").addEventListener("click", showMenu);
  bar.querySelector("#btnExportAll").addEventListener("click", exportAllChecklists);
  bar.querySelector("#btnImport").addEventListener("click", importChecklists);

  const list = document.createElement("div");
  list.className = "scroll";
  el.main.appendChild(list);

  const checklists = currentChecklists();
  if (!checklists.length) {
    const msg = document.createElement("div");
    msg.className = "empty-msg";
    msg.textContent = "No checklists yet.";
    list.appendChild(msg);
    return;
  }

  checklists.forEach(cl => {
    const row = document.createElement("div");
    row.className = "list-row" + (cl.name === state.selectedChecklistName ? " selected" : "");
    row.innerHTML = `
      <span class="row-name">${escapeHtml(cl.name)}</span>
      <button class="btn btn-icon" data-act="rename">&#9998;</button>
      <button class="btn btn-icon" data-act="delete">&#10005;</button>
      <button class="btn btn-icon" data-act="up">&#9650;</button>
      <button class="btn btn-icon" data-act="down">&#9660;</button>
    `;
    row.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      state.selectedChecklistName = cl.name;
      renderMenuEdit();
    });
    row.querySelector('[data-act="rename"]').addEventListener("click", () => renameChecklistSel(cl.name));
    row.querySelector('[data-act="delete"]').addEventListener("click", () => deleteChecklistSel(cl.name));
    row.querySelector('[data-act="up"]').addEventListener("click", () => moveChecklistSel(cl.name, -1));
    row.querySelector('[data-act="down"]').addEventListener("click", () => moveChecklistSel(cl.name, 1));
    list.appendChild(row);
  });
}

function renameChecklistSel(oldName) {
  const acName = state.currentAircraft;
  const next = (window.prompt("New name:", oldName) || "").trim();
  if (!next || next === oldName) return;
  try {
    Store.renameChecklist(acName, oldName, next);
  } catch (e) {
    window.alert(e.message);
    return;
  }
  if (state.selectedChecklistName === oldName) state.selectedChecklistName = next;
  renderMenuEdit();
}

function deleteChecklistSel(name) {
  if (!window.confirm(`Delete checklist '${name}'?`)) return;
  Store.deleteChecklist(state.currentAircraft, name);
  if (state.selectedChecklistName === name) state.selectedChecklistName = null;
  renderMenuEdit();
}

function moveChecklistSel(name, delta) {
  Store.moveChecklist(state.currentAircraft, name, delta);
  renderMenuEdit();
}

function exportAllChecklists() {
  const acName = state.currentAircraft;
  if (!acName) { window.alert("Select an aircraft first."); return; }
  const checklists = Store.exportChecklists(acName, null);
  if (!checklists.length) { window.alert("No checklists to export."); return; }
  const payload = { app: "Electronic Checklist", type: "checklists", aircraft: acName, checklists };
  downloadJson(payload, `${acName} - checklists.json`);
}

function importChecklists() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "application/json,.json";
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      let payload;
      try {
        payload = JSON.parse(reader.result);
      } catch (e) {
        window.alert("Could not read file:\n" + e.message);
        return;
      }
      const checklists = Array.isArray(payload) ? payload : payload.checklists;
      if (!Array.isArray(checklists) || !checklists.length) {
        window.alert("That file doesn't contain any checklists.");
        return;
      }
      const suggested = (payload && payload.aircraft) || state.currentAircraft || "";
      const target = (window.prompt("Import into aircraft:", suggested) || "").trim();
      if (!target) return;
      Store.getOrCreateAircraft(target);
      const added = Store.importChecklists(target, checklists);
      state.currentAircraft = target;
      refreshAircraftSelect();
      window.alert(`Imported ${added.length} checklist(s) into '${target}':\n` + added.join("\n"));
    };
    reader.readAsText(file);
  });
  input.click();
}

function downloadJson(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ------------------------------------------------------------------
 * View: run (checkbox items for the open checklist)
 * ------------------------------------------------------------------ */

let itemRowEls = []; // [{el, checkbox, label, var: bool}] aligned with checkable items only

function showRun() {
  state.view = "run";
  renderRun();
}

function currentItems() {
  const cl = Store.getChecklist(state.currentAircraft, state.currentChecklist);
  return cl ? cl.items : [];
}

function renderRun() {
  el.header.textContent = state.currentChecklist
    ? state.currentChecklist.toUpperCase() : "NO CHECKLIST SELECTED";
  el.main.innerHTML = "";
  itemRowEls = [];

  const bar = document.createElement("div");
  bar.className = "btn-row spread";
  bar.innerHTML = `
    <button class="btn" id="btnMenu">&#9664; Menu</button>
    <button class="btn" id="btnEditItems">Edit Items</button>
  `;
  el.main.appendChild(bar);
  bar.querySelector("#btnMenu").addEventListener("click", showMenu);
  bar.querySelector("#btnEditItems").addEventListener("click", showItemEdit);

  const scroll = document.createElement("div");
  scroll.className = "scroll";
  scroll.id = "runItems";
  el.main.appendChild(scroll);

  currentItems().forEach(item => {
    if (isSeparator(item)) {
      const sep = document.createElement("div");
      sep.className = "separator";
      scroll.appendChild(sep);
      return;
    }
    const row = document.createElement("label");
    row.className = "item-row";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    const text = document.createElement("span");
    text.className = "item-text";
    const challenge = document.createElement("span");
    challenge.className = "item-challenge";
    challenge.textContent = item.text;
    text.appendChild(challenge);
    const result = (item.result || "").trim();
    if (result) {
      const fill = document.createElement("span");
      fill.className = "item-fill";
      const resultEl = document.createElement("span");
      resultEl.className = "item-result";
      resultEl.textContent = result;
      text.appendChild(fill);
      text.appendChild(resultEl);
    }
    row.appendChild(cb);
    row.appendChild(text);
    scroll.appendChild(row);

    const entry = { row, cb, checked: false };
    itemRowEls.push(entry);
    cb.addEventListener("change", () => onItemToggled(entry));
  });

  const bottom = document.createElement("div");
  bottom.id = "runBottom";
  bottom.innerHTML = `<span id="runProgress"></span><span id="runComplete"></span><button class="btn" id="btnReset">RESET</button>`;
  el.main.appendChild(bottom);
  bottom.querySelector("#btnReset").addEventListener("click", resetChecklist);

  updateProgress();
}

function onItemToggled(entry) {
  entry.checked = entry.cb.checked;
  entry.row.classList.toggle("done", entry.checked);
  if (entry.checked) maybeScrollToNextPage();
  updateProgress();
}

function maybeScrollToNextPage() {
  const container = document.getElementById("runItems");
  if (!container) return;
  const viewTop = container.scrollTop;
  const viewBottom = viewTop + container.clientHeight;

  const visible = itemRowEls.filter(e => {
    const top = e.row.offsetTop;
    const bottom = top + e.row.offsetHeight;
    return bottom > viewTop && top < viewBottom;
  });
  if (!visible.length || !visible.every(e => e.checked)) return;
  if (container.scrollHeight > viewBottom + 1) {
    container.scrollBy({ top: container.clientHeight * 0.9, behavior: "smooth" });
  }
}

function updateProgress() {
  const total = itemRowEls.length;
  const done = itemRowEls.filter(e => e.checked).length;
  const progressEl = document.getElementById("runProgress");
  const completeEl = document.getElementById("runComplete");
  if (!progressEl) return;
  if (total === 0) {
    progressEl.textContent = "No items in this checklist.";
    completeEl.textContent = "";
    return;
  }
  progressEl.textContent = `${done} / ${total} items complete`;
  if (done === total) {
    completeEl.textContent = "✓ CHECKLIST COMPLETE";
    Store.setChecklistCompleted(state.currentAircraft, state.currentChecklist, true);
    setTimeout(showMenu, 0);
  } else {
    completeEl.textContent = "";
  }
}

function resetChecklist() {
  itemRowEls.forEach(entry => {
    entry.cb.checked = false;
    onItemToggled(entry);
  });
  Store.setChecklistCompleted(state.currentAircraft, state.currentChecklist, false);
}

/* ------------------------------------------------------------------
 * View: item edit (add / edit / delete / reorder / insert separator)
 * ------------------------------------------------------------------ */

function showItemEdit() {
  state.view = "itemEdit";
  state.selectedItemIndex = null;
  renderItemEdit();
}

function renderItemEdit() {
  el.header.textContent = state.currentChecklist
    ? `${state.currentChecklist.toUpperCase()} — EDIT ITEMS` : "EDIT ITEMS";
  el.main.innerHTML = "";

  const bar = document.createElement("div");
  bar.className = "btn-row";
  bar.innerHTML = `<button class="btn btn-accent" id="btnBack">&#9664; Back</button>`;
  el.main.appendChild(bar);
  bar.querySelector("#btnBack").addEventListener("click", showRun);

  const list = document.createElement("div");
  list.className = "scroll";
  el.main.appendChild(list);

  currentItems().forEach((item, idx) => {
    const row = document.createElement("div");
    row.className = "list-row" + (idx === state.selectedItemIndex ? " selected" : "");
    const label = isSeparator(item)
      ? `${idx + 1}. ─── separator ───`
      : `${idx + 1}. ${formatItem(item.text, item.result)}`;
    row.innerHTML = `<span class="row-name">${escapeHtml(label)}</span>`;
    row.addEventListener("click", () => {
      state.selectedItemIndex = idx;
      renderItemEdit();
    });
    list.appendChild(row);
  });

  const actions = document.createElement("div");
  actions.className = "btn-row";
  actions.innerHTML = `
    <button class="btn" id="btnAddItem">Add Item</button>
    <button class="btn" id="btnEditItem">Edit Item</button>
    <button class="btn" id="btnInsertSep">Insert Separator</button>
    <button class="btn" id="btnDeleteItem">Delete Item</button>
    <button class="btn" id="btnMoveUp">&#9650; Up</button>
    <button class="btn" id="btnMoveDown">&#9660; Down</button>
  `;
  el.main.appendChild(actions);
  actions.querySelector("#btnAddItem").addEventListener("click", addItem);
  actions.querySelector("#btnEditItem").addEventListener("click", editItem);
  actions.querySelector("#btnInsertSep").addEventListener("click", insertSeparator);
  actions.querySelector("#btnDeleteItem").addEventListener("click", deleteItem);
  actions.querySelector("#btnMoveUp").addEventListener("click", () => moveItem(-1));
  actions.querySelector("#btnMoveDown").addEventListener("click", () => moveItem(1));
}

function requireChecklist() {
  if (!state.currentAircraft || !state.currentChecklist) {
    window.alert("Select (or create) an aircraft and checklist first.");
    return false;
  }
  return true;
}

function addItem() {
  if (!requireChecklist()) return;
  openItemModal({
    title: "Add Items",
    multi: true,
    onSubmit: (text, result) => {
      Store.addItem(state.currentAircraft, state.currentChecklist, text, result);
      renderItemEdit();
    },
  });
}

function editItem() {
  if (!requireChecklist()) return;
  const idx = state.selectedItemIndex;
  if (idx === null) { window.alert("Select an item first."); return; }
  const current = currentItems()[idx];
  if (isSeparator(current)) {
    window.alert("Separators have no text to edit. Delete it and insert a new one if you need to move it.");
    return;
  }
  openItemModal({
    title: "Edit Item",
    initialText: current.text,
    initialResult: current.result || "",
    multi: false,
    onSubmit: (text, result) => {
      Store.editItem(state.currentAircraft, state.currentChecklist, idx, text, result);
      renderItemEdit();
    },
  });
}

function insertSeparator() {
  if (!requireChecklist()) return;
  const idx = state.selectedItemIndex;
  const position = idx !== null ? idx + 1 : currentItems().length;
  Store.insertSeparator(state.currentAircraft, state.currentChecklist, position);
  state.selectedItemIndex = position;
  renderItemEdit();
}

function deleteItem() {
  if (!requireChecklist()) return;
  const idx = state.selectedItemIndex;
  if (idx === null) { window.alert("Select an item first."); return; }
  Store.deleteItem(state.currentAircraft, state.currentChecklist, idx);
  state.selectedItemIndex = null;
  renderItemEdit();
}

function moveItem(delta) {
  if (!requireChecklist()) return;
  const idx = state.selectedItemIndex;
  if (idx === null) return;
  Store.moveItem(state.currentAircraft, state.currentChecklist, idx, delta);
  const newIdx = idx + delta;
  if (newIdx >= 0 && newIdx < currentItems().length) state.selectedItemIndex = newIdx;
  renderItemEdit();
}

/* ------------------------------------------------------------------
 * Item add/edit modal
 * ------------------------------------------------------------------ */

function openItemModal({ title, initialText = "", initialResult = "", multi = false, onSubmit }) {
  el.modalRoot.innerHTML = "";
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal">
      <label>Item text</label>
      <input type="text" id="modalText" value="${escapeAttr(initialText)}">
      <label>Result (optional)</label>
      <input type="text" id="modalResult" value="${escapeAttr(initialResult)}">
      ${multi ? '<div class="hint">Tap Add to save and keep going.</div>' : ""}
      <div class="modal-btns">
        <button class="btn" id="modalCancel">${multi ? "Done" : "Cancel"}</button>
        <button class="btn btn-accent" id="modalOk">${multi ? "Add" : "OK"}</button>
      </div>
    </div>
  `;
  el.modalRoot.appendChild(overlay);

  const textInput = overlay.querySelector("#modalText");
  const resultInput = overlay.querySelector("#modalResult");
  const close = () => { el.modalRoot.innerHTML = ""; };

  overlay.querySelector("#modalCancel").addEventListener("click", close);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });

  const submit = () => {
    const text = textInput.value.trim();
    if (!text) { window.alert("Please enter the item text."); return; }
    const result = resultInput.value.trim();
    onSubmit(text, result);
    if (multi) {
      textInput.value = "";
      resultInput.value = "";
      textInput.focus();
    } else {
      close();
    }
  };
  overlay.querySelector("#modalOk").addEventListener("click", submit);
  resultInput.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });

  setTimeout(() => textInput.focus(), 0);
}

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

/* ------------------------------------------------------------------
 * Boot
 * ------------------------------------------------------------------ */

Store.load();
refreshAircraftSelect();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => { /* offline support is best-effort */ });
  });
}
