"""JSON-backed storage for aircraft / checklists / items."""
import copy
import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


def _default_data():
    return {
        "aircraft": [
            {
                "name": "Cessna 172",
                "checklists": [
                    {
                        "name": "Before Start",
                        "completed": False,
                        "items": [
                            {"type": "item", "text": "Preflight Inspection", "result": "COMPLETE"},
                            {"type": "item", "text": "Seats, Belts, Harnesses", "result": "ADJUST, LOCK"},
                            {"type": "item", "text": "Fuel Selector Valve", "result": "BOTH"},
                            {"type": "item", "text": "Circuit Breakers", "result": "CHECK IN"},
                            {"type": "item", "text": "Parking Brake", "result": "SET"},
                        ],
                    },
                    {
                        "name": "Taxi",
                        "completed": False,
                        "items": [
                            {"type": "item", "text": "Flight Instruments", "result": "CHECK"},
                            {"type": "item", "text": "Taxi Clearance", "result": "OBTAIN"},
                            {"type": "item", "text": "Brakes", "result": "CHECK"},
                        ],
                    },
                ],
            }
        ]
    }


def _migrate_items(data):
    """Convert old plain-string items to {"type": "item", "text", "result"}
    dicts in place, tag any pre-existing item dicts with an explicit "type",
    and backfill a "completed" flag on checklists that predate it. Returns
    True if anything was migrated."""
    migrated = False
    for ac in data.get("aircraft", []):
        for cl in ac.get("checklists", []):
            if "completed" not in cl:
                cl["completed"] = False
                migrated = True
            items = cl.get("items", [])
            for i, item in enumerate(items):
                if isinstance(item, str):
                    items[i] = {"type": "item", "text": item, "result": ""}
                    migrated = True
                elif "type" not in item:
                    item["type"] = "item"
                    migrated = True
    return migrated


class DataStore:
    def __init__(self, path=DATA_FILE):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if _migrate_items(data):
                    self._save(data)
                return data
            except (json.JSONDecodeError, OSError):
                pass
        data = _default_data()
        self._save(data)
        return data

    def save(self):
        self._save(self.data)

    def _save(self, data):
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.path)

    # ---- aircraft ----
    def aircraft_list(self):
        return self.data["aircraft"]

    def get_aircraft(self, name):
        for ac in self.data["aircraft"]:
            if ac["name"] == name:
                return ac
        return None

    def add_aircraft(self, name):
        if self.get_aircraft(name):
            raise ValueError("An aircraft with that name already exists.")
        self.data["aircraft"].append({"name": name, "checklists": []})
        self.save()

    def rename_aircraft(self, old_name, new_name):
        if old_name != new_name and self.get_aircraft(new_name):
            raise ValueError("An aircraft with that name already exists.")
        self.get_aircraft(old_name)["name"] = new_name
        self.save()

    def delete_aircraft(self, name):
        self.data["aircraft"] = [a for a in self.data["aircraft"] if a["name"] != name]
        self.save()

    # ---- checklists ----
    def get_checklist(self, aircraft_name, checklist_name):
        ac = self.get_aircraft(aircraft_name)
        if not ac:
            return None
        for cl in ac["checklists"]:
            if cl["name"] == checklist_name:
                return cl
        return None

    def add_checklist(self, aircraft_name, checklist_name):
        ac = self.get_aircraft(aircraft_name)
        if self.get_checklist(aircraft_name, checklist_name):
            raise ValueError("A checklist with that name already exists for this aircraft.")
        ac["checklists"].append({"name": checklist_name, "completed": False, "items": []})
        self.save()

    def rename_checklist(self, aircraft_name, old_name, new_name):
        if old_name != new_name and self.get_checklist(aircraft_name, new_name):
            raise ValueError("A checklist with that name already exists for this aircraft.")
        self.get_checklist(aircraft_name, old_name)["name"] = new_name
        self.save()

    def delete_checklist(self, aircraft_name, checklist_name):
        ac = self.get_aircraft(aircraft_name)
        ac["checklists"] = [c for c in ac["checklists"] if c["name"] != checklist_name]
        self.save()

    def set_checklist_completed(self, aircraft_name, checklist_name, completed):
        cl = self.get_checklist(aircraft_name, checklist_name)
        cl["completed"] = completed
        self.save()

    def move_checklist(self, aircraft_name, checklist_name, delta):
        ac = self.get_aircraft(aircraft_name)
        items = ac["checklists"]
        idx = next(i for i, c in enumerate(items) if c["name"] == checklist_name)
        new_idx = idx + delta
        if 0 <= new_idx < len(items):
            items[idx], items[new_idx] = items[new_idx], items[idx]
            self.save()

    # ---- export / import ----
    def export_checklists(self, aircraft_name, checklist_names=None):
        """Return plain checklist dicts (name + items, no runtime "completed"
        flag) for aircraft_name - all of them if checklist_names is None,
        otherwise only those whose name is in checklist_names."""
        ac = self.get_aircraft(aircraft_name)
        if not ac:
            return []
        result = []
        for cl in ac["checklists"]:
            if checklist_names is not None and cl["name"] not in checklist_names:
                continue
            result.append({"name": cl["name"], "items": copy.deepcopy(cl["items"])})
        return result

    def import_checklists(self, aircraft_name, checklists):
        """Append the given checklist dicts (as produced by export_checklists,
        or any list of {"name", "items"} dicts) onto aircraft_name's
        checklist list, renaming on name collision and normalizing item
        shape. Returns the list of names actually added."""
        ac = self.get_aircraft(aircraft_name)
        if not ac:
            raise ValueError("Aircraft not found.")
        added = []
        for cl in checklists:
            name = self._unique_checklist_name(ac, str(cl.get("name") or "Imported Checklist"))
            items = []
            for item in cl.get("items", []):
                if isinstance(item, str):
                    items.append({"type": "item", "text": item, "result": ""})
                elif item.get("type") == "separator":
                    items.append({"type": "separator"})
                else:
                    items.append({"type": "item", "text": item.get("text", ""),
                                  "result": item.get("result", "")})
            ac["checklists"].append({"name": name, "completed": False, "items": items})
            added.append(name)
        self.save()
        return added

    def _unique_checklist_name(self, ac, base_name):
        existing = {c["name"] for c in ac["checklists"]}
        if base_name not in existing:
            return base_name
        n = 2
        while f"{base_name} ({n})" in existing:
            n += 1
        return f"{base_name} ({n})"

    # ---- items ----
    def add_item(self, aircraft_name, checklist_name, text, result=""):
        cl = self.get_checklist(aircraft_name, checklist_name)
        cl["items"].append({"type": "item", "text": text, "result": result})
        self.save()

    def edit_item(self, aircraft_name, checklist_name, index, text, result=""):
        cl = self.get_checklist(aircraft_name, checklist_name)
        cl["items"][index] = {"type": "item", "text": text, "result": result}
        self.save()

    def insert_separator(self, aircraft_name, checklist_name, position):
        cl = self.get_checklist(aircraft_name, checklist_name)
        cl["items"].insert(position, {"type": "separator"})
        self.save()

    def delete_item(self, aircraft_name, checklist_name, index):
        cl = self.get_checklist(aircraft_name, checklist_name)
        del cl["items"][index]
        self.save()

    def move_item(self, aircraft_name, checklist_name, index, delta):
        cl = self.get_checklist(aircraft_name, checklist_name)
        items = cl["items"]
        new_idx = index + delta
        if 0 <= new_idx < len(items):
            items[index], items[new_idx] = items[new_idx], items[index]
            self.save()
