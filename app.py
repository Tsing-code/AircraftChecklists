"""
Electronic Checklist (ECL) - a simple desktop app that recreates aircraft
electronic checklists. Checklists are grouped by aircraft. Selecting an
aircraft shows a menu of its checklists; opening one shows its items, and
completing every item automatically returns you to the checklist menu.
"""
import json
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog

from checklist_data import DataStore

BG = "#0a0a0a"
PANEL_BG = "#1c1c1c"
FG = "#f5f5f5"
ACCENT = "#ffffff"
DIM = "#8a8a8a"
DONE = "#39ff6a"
BTN_BG = "#262626"
BTN_FG = "#f0f0f0"
FONT_UI = ("Segoe UI", 10)
FONT_HEADER = ("Consolas", 18, "bold")
FONT_ITEM = ("Consolas", 13)
FONT_TILE = ("Consolas", 14, "bold")

ITEM_LINE_WIDTH = 46


def _format_item(text, result):
    """Lay out "Text.....Result" with a dot leader, ECL-style. Plain text if no result."""
    text = text or ""
    result = (result or "").strip()
    if not result:
        return text
    dots = "." * max(3, ITEM_LINE_WIDTH - len(text) - len(result))
    return f"{text}{dots}{result}"


def _is_separator(item):
    return item.get("type") == "separator"


class ItemDialog(tk.Toplevel):
    """Dialog collecting an item's text and its (optional) result.

    In single-shot mode (on_submit=None), OK/Cancel closes the dialog and
    the caller reads .result. In multi mode (on_submit given), each
    Add/Enter immediately submits the item, clears the fields, and keeps
    the dialog open so several items can be entered back-to-back without
    reopening it - closed only via Done/Escape/the window close button.
    """

    def __init__(self, parent, title, initial_text="", initial_result="", on_submit=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=PANEL_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.on_submit = on_submit
        self.multi = on_submit is not None

        tk.Label(self, text="Item text", bg=PANEL_BG, fg=DIM, font=FONT_UI).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 2))
        self.text_entry = tk.Entry(self, width=42, bg=BG, fg=FG, insertbackground=FG,
                                    relief="flat", font=FONT_UI)
        self.text_entry.grid(row=1, column=0, padx=14)
        self.text_entry.insert(0, initial_text)

        tk.Label(self, text="Result (optional)", bg=PANEL_BG, fg=DIM, font=FONT_UI).grid(
            row=2, column=0, sticky="w", padx=14, pady=(10, 2))
        self.result_entry = tk.Entry(self, width=42, bg=BG, fg=FG, insertbackground=FG,
                                      relief="flat", font=FONT_UI)
        self.result_entry.grid(row=3, column=0, padx=14)
        self.result_entry.insert(0, initial_result)

        if self.multi:
            tk.Label(self, text="Press Enter to add and keep going. Esc when done.",
                     bg=PANEL_BG, fg=DIM, font=("Segoe UI", 8)).grid(
                row=4, column=0, sticky="w", padx=14, pady=(8, 0))

        btns = tk.Frame(self, bg=PANEL_BG)
        btns.grid(row=5, column=0, sticky="e", padx=14, pady=14)
        tk.Button(btns, text=("Done" if self.multi else "Cancel"), command=self._cancel, bg=BTN_BG,
                  fg=BTN_FG, activebackground=ACCENT, activeforeground="#000000", relief="flat",
                  font=FONT_UI, padx=10, pady=4, bd=0, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(btns, text=("Add" if self.multi else "OK"), command=self._ok, bg=BTN_BG, fg=ACCENT,
                  activebackground=ACCENT, activeforeground="#000000", relief="flat",
                  font=FONT_UI, padx=10, pady=4, bd=0, cursor="hand2").pack(side="left")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.text_entry.focus_set()
        self.grab_set()
        self.wait_window(self)

    def _ok(self):
        text = self.text_entry.get().strip()
        if not text:
            messagebox.showerror("Item text required", "Please enter the item text.", parent=self)
            return
        result = self.result_entry.get().strip()
        if self.multi:
            self.on_submit(text, result)
            self.text_entry.delete(0, "end")
            self.result_entry.delete(0, "end")
            self.text_entry.focus_set()
        else:
            self.result = (text, result)
            self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class ChecklistApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Electronic Checklist")
        self.geometry("880x640")
        self.configure(bg=BG)
        self.minsize(680, 480)

        self.store = DataStore()
        self.current_aircraft = tk.StringVar()
        self.current_checklist = tk.StringVar()
        self.item_rows = []  # [{"var": BooleanVar, "label": Label}, ...] for checkable rows only

        self._build_style()
        self._build_top_bar()
        self._build_header()
        self._build_main_area()

        self._refresh_aircraft_combo()

    # ------------------------------------------------------------------
    # Style / layout scaffolding
    # ------------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL_BG, background=PANEL_BG,
                         foreground=FG, arrowcolor=FG)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_BG)],
                   foreground=[("readonly", FG)])

    def _btn(self, parent, text, command, width=None, fg=BTN_FG):
        return tk.Button(parent, text=text, command=command, bg=BTN_BG, fg=fg,
                          activebackground=ACCENT, activeforeground="#000000",
                          relief="flat", font=FONT_UI, padx=6, pady=2, width=width,
                          highlightthickness=0, bd=0, cursor="hand2")

    def _build_top_bar(self):
        bar = tk.Frame(self, bg=PANEL_BG, pady=6)
        bar.pack(side="top", fill="x")

        tk.Label(bar, text="AIRCRAFT", bg=PANEL_BG, fg=DIM, font=FONT_UI).pack(side="left", padx=(10, 4))
        self.aircraft_combo = ttk.Combobox(bar, textvariable=self.current_aircraft,
                                            state="readonly", width=18, font=FONT_UI)
        self.aircraft_combo.pack(side="left")
        self.aircraft_combo.bind("<<ComboboxSelected>>", lambda e: self._on_aircraft_selected())

        self._btn(bar, "+", self._add_aircraft, width=2).pack(side="left", padx=2)
        self._btn(bar, "Rename", self._rename_aircraft).pack(side="left", padx=2)
        self._btn(bar, "Delete", self._delete_aircraft).pack(side="left", padx=2)

    def _build_header(self):
        self.header_label = tk.Label(self, text="", bg=BG, fg=ACCENT, font=FONT_HEADER, pady=10)
        self.header_label.pack(side="top", fill="x")

    def _build_main_area(self):
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(side="top", fill="both", expand=True, padx=16, pady=(0, 12))

        self._build_menu_frame()
        self._build_menu_edit_frame()
        self._build_run_frame()
        self._build_item_edit_frame()

        self.frames = {
            "menu": self.menu_frame,
            "menu_edit": self.menu_edit_frame,
            "run": self.run_frame,
            "item_edit": self.item_edit_frame,
        }
        self.view = None

    # ---- MENU: list of checklists for the selected aircraft ----
    def _build_menu_frame(self):
        self.menu_frame = tk.Frame(self.container, bg=BG)

        top = tk.Frame(self.menu_frame, bg=BG)
        top.pack(side="top", fill="x", pady=(0, 8))
        self._btn(top, "+ Add Checklist", self._add_checklist).pack(side="left")
        self.menu_edit_toggle_btn = self._btn(top, "Edit Checklists", self._show_menu_edit)
        self.menu_edit_toggle_btn.pack(side="right")
        self._btn(top, "Reset All", self._reset_all_checklists).pack(side="right", padx=(0, 6))

        canvas = tk.Canvas(self.menu_frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.menu_frame, orient="vertical", command=canvas.yview)
        self.menu_tiles_frame = tk.Frame(canvas, bg=BG)
        self.menu_tiles_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=self.menu_tiles_frame, anchor="nw", width=1)

        def _sync_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        canvas.bind("<Configure>", _sync_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ---- MENU EDIT: rename / delete / reorder checklists ----
    def _build_menu_edit_frame(self):
        self.menu_edit_frame = tk.Frame(self.container, bg=BG)

        top = tk.Frame(self.menu_edit_frame, bg=BG)
        top.pack(side="top", fill="x", pady=(0, 8))
        self._btn(top, "Done", self._show_menu, fg=ACCENT).pack(side="left")

        body = tk.Frame(self.menu_edit_frame, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        list_wrap = tk.Frame(body, bg=BG)
        list_wrap.pack(side="left", fill="both", expand=True)
        self.checklist_listbox = tk.Listbox(list_wrap, bg=PANEL_BG, fg=FG, font=FONT_ITEM,
                                             selectbackground=ACCENT, selectforeground="#000000",
                                             highlightthickness=0, bd=0, activestyle="none")
        self.checklist_listbox.pack(side="left", fill="both", expand=True)
        cl_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.checklist_listbox.yview)
        cl_scroll.pack(side="right", fill="y")
        self.checklist_listbox.configure(yscrollcommand=cl_scroll.set)

        btns = tk.Frame(body, bg=BG)
        btns.pack(side="left", fill="y", padx=(12, 0))
        self._btn(btns, "Rename", self._rename_checklist_sel).pack(fill="x", pady=2)
        self._btn(btns, "Delete", self._delete_checklist_sel).pack(fill="x", pady=2)
        self._btn(btns, "Move Up", self._move_checklist_sel_up).pack(fill="x", pady=(12, 2))
        self._btn(btns, "Move Down", self._move_checklist_sel_down).pack(fill="x", pady=2)
        self._btn(btns, "Export", self._export_checklists).pack(fill="x", pady=(12, 2))
        self._btn(btns, "Import", self._import_checklists).pack(fill="x", pady=2)

    # ---- RUN: checkbox items for the open checklist ----
    def _build_run_frame(self):
        self.run_frame = tk.Frame(self.container, bg=BG)

        top = tk.Frame(self.run_frame, bg=BG)
        top.pack(side="top", fill="x", pady=(0, 8))
        self._btn(top, "◀ Menu", self._show_menu).pack(side="left")
        self._btn(top, "Edit Items", self._show_item_edit).pack(side="right")

        canvas = tk.Canvas(self.run_frame, bg=BG, highlightthickness=0)
        self.items_canvas = canvas
        scrollbar = ttk.Scrollbar(self.run_frame, orient="vertical", command=canvas.yview)
        self.items_frame = tk.Frame(canvas, bg=BG)
        self.items_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.items_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        bottom = tk.Frame(self.run_frame, bg=PANEL_BG, pady=8)
        bottom.pack(side="bottom", fill="x", pady=(8, 0))
        self.progress_label = tk.Label(bottom, text="", bg=PANEL_BG, fg=FG, font=FONT_UI)
        self.progress_label.pack(side="left", padx=12)
        self._btn(bottom, "RESET", self._reset_checklist).pack(side="right", padx=12)
        self.complete_label = tk.Label(bottom, text="", bg=PANEL_BG, fg=ACCENT,
                                        font=("Segoe UI", 10, "bold"))
        self.complete_label.pack(side="right", padx=12)

    # ---- ITEM EDIT: add / edit / delete / reorder items ----
    def _build_item_edit_frame(self):
        self.item_edit_frame = tk.Frame(self.container, bg=BG)

        top = tk.Frame(self.item_edit_frame, bg=BG)
        top.pack(side="top", fill="x", pady=(0, 8))
        self._btn(top, "◀ Back", self._show_run, fg=ACCENT).pack(side="left")

        body = tk.Frame(self.item_edit_frame, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        list_wrap = tk.Frame(body, bg=BG)
        list_wrap.pack(side="left", fill="both", expand=True)
        self.item_listbox = tk.Listbox(list_wrap, bg=PANEL_BG, fg=FG, font=FONT_ITEM,
                                        selectbackground=ACCENT, selectforeground="#000000",
                                        highlightthickness=0, bd=0, activestyle="none")
        self.item_listbox.pack(side="left", fill="both", expand=True)
        item_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.item_listbox.yview)
        item_scroll.pack(side="right", fill="y")
        self.item_listbox.configure(yscrollcommand=item_scroll.set)

        item_btns = tk.Frame(body, bg=BG)
        item_btns.pack(side="left", fill="y", padx=(12, 0))
        self._btn(item_btns, "Add Item", self._add_item).pack(fill="x", pady=2)
        self._btn(item_btns, "Edit Item", self._edit_item).pack(fill="x", pady=2)
        self._btn(item_btns, "Insert Separator", self._insert_separator).pack(fill="x", pady=2)
        self._btn(item_btns, "Delete Item", self._delete_item).pack(fill="x", pady=2)
        self._btn(item_btns, "Move Up", self._move_item_up).pack(fill="x", pady=(12, 2))
        self._btn(item_btns, "Move Down", self._move_item_down).pack(fill="x", pady=2)

    # ------------------------------------------------------------------
    # View navigation
    # ------------------------------------------------------------------
    def _switch_view(self, view):
        for name, frame in self.frames.items():
            if name == view:
                frame.pack(side="top", fill="both", expand=True)
            else:
                frame.pack_forget()
        self.view = view

    def _show_menu(self):
        self._switch_view("menu")
        self._refresh_menu()

    def _show_menu_edit(self):
        self._switch_view("menu_edit")
        self._reload_checklist_listbox()

    def _show_run(self):
        self._switch_view("run")
        self._render_items()

    def _show_item_edit(self):
        self._switch_view("item_edit")
        self._reload_item_listbox()

    # ------------------------------------------------------------------
    # Aircraft
    # ------------------------------------------------------------------
    def _refresh_aircraft_combo(self):
        names = [a["name"] for a in self.store.aircraft_list()]
        self.aircraft_combo["values"] = names
        if names:
            if self.current_aircraft.get() not in names:
                self.current_aircraft.set(names[0])
        else:
            self.current_aircraft.set("")
        self._on_aircraft_selected()

    def _on_aircraft_selected(self):
        self._show_menu()

    def _add_aircraft(self):
        name = simpledialog.askstring("Add Aircraft", "Aircraft name (e.g. Cessna 172):", parent=self)
        if not name:
            return
        try:
            self.store.add_aircraft(name.strip())
        except ValueError as e:
            messagebox.showerror("Add Aircraft", str(e), parent=self)
            return
        self.current_aircraft.set(name.strip())
        self._refresh_aircraft_combo()

    def _rename_aircraft(self):
        old = self.current_aircraft.get()
        if not old:
            return
        new = simpledialog.askstring("Rename Aircraft", "New name:", initialvalue=old, parent=self)
        if not new or new.strip() == old:
            return
        try:
            self.store.rename_aircraft(old, new.strip())
        except ValueError as e:
            messagebox.showerror("Rename Aircraft", str(e), parent=self)
            return
        self.current_aircraft.set(new.strip())
        self._refresh_aircraft_combo()

    def _delete_aircraft(self):
        name = self.current_aircraft.get()
        if not name:
            return
        if not messagebox.askyesno("Delete Aircraft",
                                    f"Delete '{name}' and all its checklists?", parent=self):
            return
        self.store.delete_aircraft(name)
        self._refresh_aircraft_combo()

    # ------------------------------------------------------------------
    # Checklist menu
    # ------------------------------------------------------------------
    def _current_checklists(self):
        ac = self.store.get_aircraft(self.current_aircraft.get())
        return ac["checklists"] if ac else []

    def _refresh_menu(self):
        ac_name = self.current_aircraft.get()
        self.header_label.configure(text=(f"{ac_name.upper()} — CHECKLISTS" if ac_name
                                           else "NO AIRCRAFT SELECTED"))

        for w in self.menu_tiles_frame.winfo_children():
            w.destroy()

        checklists = self._current_checklists()
        if not checklists:
            tk.Label(self.menu_tiles_frame, text="No checklists yet. Use '+ Add Checklist' to create one.",
                     bg=BG, fg=DIM, font=FONT_UI).pack(anchor="w", pady=10)
            return

        for cl in checklists:
            completed = cl.get("completed", False)
            label = f"✓  {cl['name']}" if completed else cl["name"]
            tile = tk.Button(self.menu_tiles_frame, text=label, anchor="w",
                              command=lambda n=cl["name"]: self._open_checklist(n),
                              bg=PANEL_BG, fg=(DONE if completed else FG),
                              activebackground=ACCENT, activeforeground="#000000",
                              relief="flat", font=FONT_TILE, padx=14, pady=12,
                              highlightthickness=0, bd=0, cursor="hand2")
            tile.pack(fill="x", pady=4)

    def _open_checklist(self, name):
        self.current_checklist.set(name)
        ac_name = self.current_aircraft.get()
        if self.store.get_checklist(ac_name, name).get("completed", False):
            self.store.set_checklist_completed(ac_name, name, False)
        self._show_run()

    def _reset_all_checklists(self):
        ac_name = self.current_aircraft.get()
        if not ac_name:
            messagebox.showinfo("Reset All", "Select an aircraft first.", parent=self)
            return
        if not self._current_checklists():
            messagebox.showinfo("Reset All", "No checklists to reset.", parent=self)
            return
        if not messagebox.askyesno("Reset All",
                                    f"Reset all checklists for '{ac_name}'? This clears their "
                                    "completed status (shown in this menu) - it doesn't delete "
                                    "anything.", parent=self):
            return
        self.store.reset_all_checklists(ac_name)
        self._refresh_menu()

    def _add_checklist(self):
        ac_name = self.current_aircraft.get()
        if not ac_name:
            messagebox.showinfo("Add Checklist", "Add an aircraft first.", parent=self)
            return
        name = simpledialog.askstring("Add Checklist", "Checklist name (e.g. Before Takeoff):", parent=self)
        if not name:
            return
        try:
            self.store.add_checklist(ac_name, name.strip())
        except ValueError as e:
            messagebox.showerror("Add Checklist", str(e), parent=self)
            return
        self._refresh_menu()

    # ------------------------------------------------------------------
    # Checklist menu - edit (rename / delete / reorder)
    # ------------------------------------------------------------------
    def _reload_checklist_listbox(self):
        self.header_label.configure(text=f"{self.current_aircraft.get().upper()} — EDIT CHECKLISTS")
        self.checklist_listbox.delete(0, "end")
        for cl in self._current_checklists():
            self.checklist_listbox.insert("end", cl["name"])

    def _selected_checklist_name(self):
        sel = self.checklist_listbox.curselection()
        if not sel:
            return None
        return self.checklist_listbox.get(sel[0])

    def _rename_checklist_sel(self):
        ac_name = self.current_aircraft.get()
        old = self._selected_checklist_name()
        if not old:
            messagebox.showinfo("Rename Checklist", "Select a checklist first.", parent=self)
            return
        new = simpledialog.askstring("Rename Checklist", "New name:", initialvalue=old, parent=self)
        if not new or new.strip() == old:
            return
        try:
            self.store.rename_checklist(ac_name, old, new.strip())
        except ValueError as e:
            messagebox.showerror("Rename Checklist", str(e), parent=self)
            return
        self._reload_checklist_listbox()

    def _delete_checklist_sel(self):
        ac_name = self.current_aircraft.get()
        name = self._selected_checklist_name()
        if not name:
            messagebox.showinfo("Delete Checklist", "Select a checklist first.", parent=self)
            return
        if not messagebox.askyesno("Delete Checklist", f"Delete checklist '{name}'?", parent=self):
            return
        self.store.delete_checklist(ac_name, name)
        self._reload_checklist_listbox()

    def _move_checklist_sel_up(self):
        self._move_checklist_sel(-1)

    def _move_checklist_sel_down(self):
        self._move_checklist_sel(1)

    def _move_checklist_sel(self, delta):
        ac_name = self.current_aircraft.get()
        name = self._selected_checklist_name()
        if not name:
            return
        self.store.move_checklist(ac_name, name, delta)
        names = [cl["name"] for cl in self._current_checklists()]
        self._reload_checklist_listbox()
        if name in names:
            self.checklist_listbox.selection_set(names.index(name))

    def _export_checklists(self):
        ac_name = self.current_aircraft.get()
        if not ac_name:
            messagebox.showinfo("Export", "Select an aircraft first.", parent=self)
            return
        sel_name = self._selected_checklist_name()
        checklists = self.store.export_checklists(ac_name, [sel_name] if sel_name else None)
        if not checklists:
            messagebox.showinfo("Export", "No checklists to export.", parent=self)
            return
        default_name = f"{ac_name} - {sel_name}.json" if sel_name else f"{ac_name} - checklists.json"
        path = filedialog.asksaveasfilename(parent=self, title="Export Checklists",
                                             defaultextension=".json", initialfile=default_name,
                                             filetypes=[("Checklist JSON", "*.json")])
        if not path:
            return
        payload = {"app": "Electronic Checklist", "type": "checklists",
                   "aircraft": ac_name, "checklists": checklists}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            messagebox.showerror("Export", f"Could not write file:\n{e}", parent=self)
            return
        messagebox.showinfo("Export", f"Exported {len(checklists)} checklist(s) to:\n{path}", parent=self)

    def _import_checklists(self):
        path = filedialog.askopenfilename(parent=self, title="Import Checklists",
                                           filetypes=[("Checklist JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            messagebox.showerror("Import", f"Could not read file:\n{e}", parent=self)
            return
        checklists = payload.get("checklists") if isinstance(payload, dict) else payload
        if not isinstance(checklists, list) or not checklists:
            messagebox.showerror("Import", "That file doesn't contain any checklists.", parent=self)
            return

        # A whole-aircraft export names its aircraft in the file - default to
        # that (falling back to whatever aircraft is currently selected) so
        # importing a checklist suite doesn't require creating the aircraft
        # by hand first. The aircraft is created automatically if it's new.
        suggested = (payload.get("aircraft") if isinstance(payload, dict) else None) \
            or self.current_aircraft.get()
        target = simpledialog.askstring("Import Checklists", "Import into aircraft:",
                                         initialvalue=suggested, parent=self)
        if not target or not target.strip():
            return
        target = target.strip()

        self.store.get_or_create_aircraft(target)
        added = self.store.import_checklists(target, checklists)

        self.current_aircraft.set(target)
        self._refresh_aircraft_combo()
        messagebox.showinfo("Import", f"Imported {len(added)} checklist(s) into '{target}':\n"
                                       + "\n".join(added), parent=self)

    # ------------------------------------------------------------------
    # Items - rendering (run view)
    # ------------------------------------------------------------------
    def _current_items(self):
        cl = self.store.get_checklist(self.current_aircraft.get(), self.current_checklist.get())
        return cl["items"] if cl else []

    def _render_items(self):
        name = self.current_checklist.get()
        self.header_label.configure(text=name.upper() if name else "NO CHECKLIST SELECTED")

        for w in self.items_frame.winfo_children():
            w.destroy()
        self.item_rows = []

        items = self._current_items()
        for item in items:
            if _is_separator(item):
                sep = tk.Frame(self.items_frame, bg=BG)
                sep.pack(fill="x", pady=12)
                tk.Frame(sep, bg=ACCENT, height=2).pack(fill="x")
                continue

            pos = len(self.item_rows)
            var = tk.BooleanVar(value=False)
            row = tk.Frame(self.items_frame, bg=BG)
            row.pack(fill="x", pady=3)
            cb = tk.Checkbutton(row, variable=var, bg=BG, activebackground=BG,
                                 selectcolor=PANEL_BG, fg=FG, highlightthickness=0, bd=0,
                                 command=lambda p=pos: self._on_item_toggled(p))
            cb.pack(side="left")
            display_text = _format_item(item["text"], item.get("result", ""))
            lbl = tk.Label(row, text=display_text, bg=BG, fg=FG, font=FONT_ITEM, anchor="w", justify="left")
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, p=pos: (self.item_rows[p]["var"].set(
                not self.item_rows[p]["var"].get()), self._on_item_toggled(p)))
            self.item_rows.append({"var": var, "label": lbl, "row": row})

        self._update_progress()

    def _on_item_toggled(self, pos):
        entry = self.item_rows[pos]
        var, lbl = entry["var"], entry["label"]
        if var.get():
            lbl.configure(fg=DONE, font=(FONT_ITEM[0], FONT_ITEM[1], "overstrike"))
            self._maybe_scroll_to_next_page()
        else:
            lbl.configure(fg=FG, font=FONT_ITEM)
        self._update_progress()

    def _maybe_scroll_to_next_page(self):
        """If every checkable item currently visible in the run view has now
        been checked, and there's more checklist below the fold, scroll down
        so the next batch of items comes into view - like turning a page."""
        canvas = self.items_canvas
        canvas.update_idletasks()
        view_top = canvas.canvasy(0)
        view_bottom = canvas.canvasy(canvas.winfo_height())

        visible = []
        content_bottom = 0
        for entry in self.item_rows:
            row = entry["row"]
            row_top = row.winfo_y()
            row_bottom = row_top + row.winfo_height()
            content_bottom = max(content_bottom, row_bottom)
            if row_bottom > view_top and row_top < view_bottom:
                visible.append(entry)

        if not visible or not all(e["var"].get() for e in visible):
            return
        if content_bottom > view_bottom + 1:
            canvas.yview_scroll(1, "pages")

    def _update_progress(self):
        total = len(self.item_rows)
        done = sum(1 for entry in self.item_rows if entry["var"].get())
        if total == 0:
            self.progress_label.configure(text="No items in this checklist.")
            self.complete_label.configure(text="")
            return
        self.progress_label.configure(text=f"{done} / {total} items complete")
        if done == total:
            self.complete_label.configure(text="✓ CHECKLIST COMPLETE")
            self.store.set_checklist_completed(self.current_aircraft.get(),
                                                self.current_checklist.get(), True)
            self.after(0, self._show_menu)
        else:
            self.complete_label.configure(text="")

    def _reset_checklist(self):
        for pos, entry in enumerate(self.item_rows):
            entry["var"].set(False)
            self._on_item_toggled(pos)
        self.store.set_checklist_completed(self.current_aircraft.get(),
                                            self.current_checklist.get(), False)

    # ------------------------------------------------------------------
    # Items - editing
    # ------------------------------------------------------------------
    def _require_checklist(self):
        ac_name = self.current_aircraft.get()
        cl_name = self.current_checklist.get()
        if not ac_name or not cl_name:
            messagebox.showinfo("No Checklist", "Select (or create) an aircraft and checklist first.",
                                 parent=self)
            return None, None
        return ac_name, cl_name

    def _selected_item_index(self):
        sel = self.item_listbox.curselection()
        return sel[0] if sel else None

    def _add_item(self):
        ac_name, cl_name = self._require_checklist()
        if ac_name is None:
            return

        def submit(text, result):
            self.store.add_item(ac_name, cl_name, text, result)
            self._reload_item_listbox()

        ItemDialog(self, "Add Items", on_submit=submit)

    def _edit_item(self):
        ac_name, cl_name = self._require_checklist()
        if ac_name is None:
            return
        idx = self._selected_item_index()
        if idx is None:
            messagebox.showinfo("Edit Item", "Select an item first.", parent=self)
            return
        current = self._current_items()[idx]
        if _is_separator(current):
            messagebox.showinfo("Edit Item", "Separators have no text to edit. Delete it and insert "
                                              "a new one if you need to move it.", parent=self)
            return
        entered = ItemDialog(self, "Edit Item", current["text"], current.get("result", "")).result
        if not entered:
            return
        text, result = entered
        self.store.edit_item(ac_name, cl_name, idx, text, result)
        self._reload_item_listbox()

    def _insert_separator(self):
        ac_name, cl_name = self._require_checklist()
        if ac_name is None:
            return
        idx = self._selected_item_index()
        position = (idx + 1) if idx is not None else len(self._current_items())
        self.store.insert_separator(ac_name, cl_name, position)
        self._reload_item_listbox()
        self.item_listbox.selection_clear(0, "end")
        self.item_listbox.selection_set(position)

    def _delete_item(self):
        ac_name, cl_name = self._require_checklist()
        if ac_name is None:
            return
        idx = self._selected_item_index()
        if idx is None:
            messagebox.showinfo("Delete Item", "Select an item first.", parent=self)
            return
        self.store.delete_item(ac_name, cl_name, idx)
        self._reload_item_listbox()

    def _move_item_up(self):
        self._move_item(-1)

    def _move_item_down(self):
        self._move_item(1)

    def _move_item(self, delta):
        ac_name, cl_name = self._require_checklist()
        if ac_name is None:
            return
        idx = self._selected_item_index()
        if idx is None:
            return
        self.store.move_item(ac_name, cl_name, idx, delta)
        new_idx = idx + delta
        self._reload_item_listbox()
        if 0 <= new_idx < self.item_listbox.size():
            self.item_listbox.selection_set(new_idx)

    def _reload_item_listbox(self):
        name = self.current_checklist.get()
        self.header_label.configure(text=f"{name.upper()} — EDIT ITEMS" if name else "EDIT ITEMS")
        self.item_listbox.delete(0, "end")
        for idx, item in enumerate(self._current_items()):
            if _is_separator(item):
                self.item_listbox.insert("end", f"{idx + 1}. ─────────── separator ───────────")
            else:
                display_text = _format_item(item["text"], item.get("result", ""))
                self.item_listbox.insert("end", f"{idx + 1}. {display_text}")


if __name__ == "__main__":
    app = ChecklistApp()
    app.mainloop()
