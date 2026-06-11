"""Interactive TUI for exploring GEDCOM files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import RenderableType
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from .models import GedcomData, Individual
from .parser import GedcomParseError, parse
from .queries import (
    apply_leaf_filters,
    apply_root_filters,
    count_generations,
    count_incomplete_name,
    count_no_name,
    display_name,
    find_by_id,
    find_by_name,
    get_all_individuals,
    get_ancestor_details,
    get_connected_components,
    get_descendant_details,
    get_leaves,
    get_roots,
    id_sort_key,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class NavItem:
    label: str
    individual: Optional[Individual]
    date_hint: str      # birth/death for self, "m. DATE" for spouses, ""
    pane: str           # "left", "center", or "right"
    idx: int            # sequential position in the full nav list
    family_id: Optional[str] = None  # set on spouse items: the marriage family ID


# ---------------------------------------------------------------------------
# Label helpers (mirrors relatives.py)
# ---------------------------------------------------------------------------

def _parent_label(indi: Individual) -> str:
    return {"M": "father:", "F": "mother:"}.get(indi.sex, "parent:")


def _spouse_label(indi: Individual) -> str:
    return {"M": "husband:", "F": "wife:"}.get(indi.sex, "spouse:")


def _child_label(indi: Individual) -> str:
    return {"M": "son:", "F": "daughter:"}.get(indi.sex, "child:")


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def build_nav_items(
    data: GedcomData,
    focus_id: str,
    center_cursor: int = 0,
) -> list[NavItem]:
    """Return the flat navigation list for the given focus individual.

    center_cursor is the center-pane-local index (0 = self, 1 = first spouse,
    …). The right pane shows children filtered to the selected family: all
    families when cursor is on self, one specific family when on a spouse.

    Raises ValueError if focus_id is not found.
    """
    indi = find_by_id(data, focus_id)
    if indi is None:
        raise ValueError(f"Unknown individual ID: {focus_id}")

    left: list[NavItem] = []
    center: list[NavItem] = []
    right: list[NavItem] = []

    # --- Left pane: parents ---
    for fam_id in indi.family_ids_as_child:
        fam = data.families.get(fam_id)
        if fam is None:
            continue
        for parent_id in [fam.husband_id, fam.wife_id]:
            if not parent_id:
                continue
            parent = data.individuals.get(parent_id)
            if parent is None:
                continue
            left.append(NavItem(
                label=_parent_label(parent),
                individual=parent,
                date_hint="",
                pane="left",
                idx=0,
            ))

    # --- Center pane: self ---
    parts: list[str] = []
    if indi.birth_date:
        parts.append(indi.birth_date)
    if indi.death_date:
        parts.append(indi.death_date)
    center.append(NavItem(
        label="self:",
        individual=indi,
        date_hint=" – ".join(parts),
        pane="center",
        idx=0,
        family_id=None,
    ))

    # --- Center pane: spouses ---
    for fam_id in indi.family_ids_as_spouse:
        fam = data.families.get(fam_id)
        if fam is None:
            continue
        other_id = fam.wife_id if fam.husband_id == indi.id else fam.husband_id
        if not other_id:
            continue
        spouse = data.individuals.get(other_id)
        if spouse is None:
            continue
        center.append(NavItem(
            label=_spouse_label(spouse),
            individual=spouse,
            date_hint=f"m. {fam.marriage_date}" if fam.marriage_date else "",
            pane="center",
            idx=0,
            family_id=fam_id,
        ))

    # --- Right pane: children filtered by selected center item ---
    safe_cursor = min(center_cursor, len(center) - 1) if center else 0
    selected = center[safe_cursor] if center else None
    target_fam = selected.family_id if selected else None  # None = show all

    for fam_id in indi.family_ids_as_spouse:
        if target_fam is not None and fam_id != target_fam:
            continue
        fam = data.families.get(fam_id)
        if fam is None:
            continue
        for child_id in fam.child_ids:
            child = data.individuals.get(child_id)
            if child is None:
                continue
            right.append(NavItem(
                label=_child_label(child),
                individual=child,
                date_hint="",
                pane="right",
                idx=0,
            ))

    # Assign sequential global idx values
    all_items = left + center + right
    for i, item in enumerate(all_items):
        item.idx = i

    return all_items


def _find_ged_files() -> list[Path]:
    """Return *.ged files in CWD and one level of non-hidden subdirectories."""
    cwd = Path.cwd()
    found: list[Path] = sorted(cwd.glob("*.ged"))
    for subdir in sorted(p for p in cwd.iterdir() if p.is_dir() and not p.name.startswith(".")):
        found.extend(sorted(subdir.glob("*.ged")))
    return found


def _go_to_root(data: GedcomData, start_id: str) -> str:
    """Return the ID of the topmost ancestor via the first-parent path.

    Follows husband_id then wife_id at each generation. Returns start_id if
    there are no known parents.
    """
    current_id = start_id
    visited: set[str] = {current_id}
    while True:
        indi = find_by_id(data, current_id)
        if not indi:
            break
        parent_id: str | None = None
        for fam_id in indi.family_ids_as_child:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            for pid in (fam.husband_id, fam.wife_id):
                if pid and pid not in visited:
                    parent_id = pid
                    break
            if parent_id:
                break
        if not parent_id:
            break
        visited.add(parent_id)
        current_id = parent_id
    return current_id


# ---------------------------------------------------------------------------
# Three-column person pane
# ---------------------------------------------------------------------------

class PersonPane(Widget):
    """Renders one column (left / center / right) of the family view.

    The cursor lives exclusively in the center pane and is represented as the
    center-local index (app.cursor_idx). Left and right panes are info-only.
    """

    def __init__(self, pane_id: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._pane_id = pane_id

    def render(self) -> RenderableType:
        try:
            app: GedTui = self.app  # type: ignore[assignment]
            items = [i for i in app._nav_items if i.pane == self._pane_id]
            center_cursor = app.cursor_idx
        except Exception:
            return Text("")

        lines = Text()
        for enum_idx, item in enumerate(items):
            is_cursor = self._pane_id == "center" and enum_idx == center_cursor
            prefix = "► " if is_cursor else "  "
            name = display_name(item.individual) if item.individual else "(unknown)"
            id_str = item.individual.id.strip("@") if item.individual else ""
            style = "bold reverse" if is_cursor else ""

            # Main line: label + name + (ID)
            id_part = f" ({id_str})" if id_str else ""
            lines.append(f"{prefix}{item.label} {name}{id_part}\n", style=style)

            # Sub-line: sex + date info (only for center pane)
            if self._pane_id == "center":
                sub_parts: list[str] = []
                if item.label == "self:" and item.individual:
                    sex_str = {"M": "male", "F": "female"}.get(item.individual.sex, "")
                    if sex_str:
                        sub_parts.append(sex_str)
                if item.date_hint:
                    sub_parts.append(item.date_hint)
                if sub_parts:
                    lines.append(f"    {' · '.join(sub_parts)}\n", style="dim")
            elif item.date_hint:
                lines.append(f"    {item.date_hint}\n", style="dim")

        return lines


# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------

class SearchBar(Widget):
    """Inline search input docked at the bottom of the screen."""

    DEFAULT_CSS = """
    SearchBar {
        height: 3;
        dock: bottom;
        background: $panel;
        border-top: solid $accent;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search by name or ID — Enter to confirm, empty Enter to cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Capture app reference BEFORE removing self from DOM.
        app: GedTui = self.app  # type: ignore[assignment]
        query = event.value.strip()
        self.remove()
        if not query or not app._data:
            return
        by_id = find_by_id(app._data, query)
        if by_id is not None:
            app._navigate_to(by_id.id)
            return
        results = find_by_name(app._data, query)
        if not results:
            app.notify(f"Not found: {query!r}", severity="warning")
            return
        app._navigate_to(results[0].id)
        if len(results) > 1:
            app.notify(f"{len(results)} matches — navigated to first", timeout=3)


# ---------------------------------------------------------------------------
# File picker screen
# ---------------------------------------------------------------------------

class _FileItem(ListItem):
    """ListView item that holds a Path; displays only the filename."""

    def __init__(self, path: Path) -> None:
        super().__init__(Label(path.name))
        self.path = path


class FilePickerScreen(ModalScreen[str | None]):
    """Modal for selecting or typing a .ged file path."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    FilePickerScreen { align: center middle; }
    #picker-dialog {
        width: 60;
        height: auto;
        max-height: 28;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #picker-title  { text-style: bold; margin-bottom: 1; }
    #file-list     { height: auto; max-height: 16; border: solid $panel; margin-top: 1; }
    #path-status   { color: $text-disabled; margin-top: 1; }
    """

    def __init__(self, files: list[Path], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._files = files

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Label("Open GEDCOM file", id="picker-title")
            yield Input(
                placeholder="Type a file path, or select from list below",
                id="path-input",
            )
            if self._files:
                yield ListView(*[_FileItem(f) for f in self._files], id="file-list")
                yield Label("", id="path-status")
            else:
                yield Label("(no *.ged files found in current directory or subdirectories)")

    def on_mount(self) -> None:
        self.query_one("#path-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        path = event.value.strip()
        if path:
            self.dismiss(path)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Show full path in the status label when an item is highlighted."""
        status = self.query_one("#path-status", Label)
        if event.item and isinstance(event.item, _FileItem):
            status.update(str(event.item.path))
        else:
            status.update("")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, _FileItem):
            self.dismiss(str(event.item.path))

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Command palette
# ---------------------------------------------------------------------------

_COMMANDS: list[tuple[str, str]] = [
    ("stat",        "File statistics"),
    ("roots",       "Root individuals (no known parents)"),
    ("leaves",      "Leaf individuals (no known children)"),
    ("indi",        "All individuals"),
    ("ancestors",   "Ancestors of current person"),
    ("descendants", "Descendants of current person"),
]


class _CmdItem(ListItem):
    def __init__(self, cmd: str, desc: str) -> None:
        super().__init__(Label(f"{cmd:<14}{desc}"))
        self.cmd = cmd


class CommandScreen(ModalScreen[str | None]):
    """Command palette modal."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    CommandScreen { align: center middle; }
    #cmd-dialog {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #cmd-title { text-style: bold; margin-bottom: 1; }
    #cmd-list  { height: auto; max-height: 16; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="cmd-dialog"):
            yield Label("Commands", id="cmd-title")
            yield ListView(*[_CmdItem(cmd, desc) for cmd, desc in _COMMANDS], id="cmd-list")

    def on_mount(self) -> None:
        self.query_one(ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, _CmdItem):
            self.dismiss(event.item.cmd)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Results screens
# ---------------------------------------------------------------------------

class _IndiItem(ListItem):
    def __init__(self, individual: Individual) -> None:
        id_str = individual.id.strip("@")
        name = display_name(individual)
        dates = ""
        if individual.birth_date or individual.death_date:
            parts = []
            if individual.birth_date:
                parts.append(f"b. {individual.birth_date}")
            if individual.death_date:
                parts.append(f"d. {individual.death_date}")
            dates = "  " + "  ".join(parts)
        super().__init__(Label(f"{id_str:<8}{name}{dates}"))
        self.individual = individual


class IndividualListScreen(ModalScreen[str | None]):
    """Shows a navigable list of individuals; returns the selected ID."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    IndividualListScreen { align: center middle; }
    #list-dialog {
        width: 72;
        height: auto;
        max-height: 30;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #list-title   { text-style: bold; }
    #list-count   { color: $text-disabled; margin-bottom: 1; }
    #indi-list    { height: auto; max-height: 20; }
    """

    def __init__(self, title: str, individuals: list[Individual], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._individuals = individuals

    def compose(self) -> ComposeResult:
        with Vertical(id="list-dialog"):
            yield Label(self._title, id="list-title")
            yield Label(f"{len(self._individuals)} individuals", id="list-count")
            if self._individuals:
                yield ListView(*[_IndiItem(i) for i in self._individuals], id="indi-list")
            else:
                yield Label("(none)")

    def on_mount(self) -> None:
        lv = self.query_one(ListView, expect_type=ListView)
        if lv:
            lv.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, _IndiItem):
            self.dismiss(event.item.individual.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class TextResultScreen(ModalScreen[None]):
    """Shows a static text result (e.g., statistics)."""

    BINDINGS = [Binding("escape", "cancel", "Close")]

    DEFAULT_CSS = """
    TextResultScreen { align: center middle; }
    #text-dialog {
        width: 50;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #text-title   { text-style: bold; margin-bottom: 1; }
    #text-content { margin-top: 1; }
    """

    def __init__(self, title: str, text: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="text-dialog"):
            yield Label(self._title, id="text-title")
            yield Static(self._text, id="text-content")

    def action_cancel(self) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class GedTui(App):
    """Interactive TUI for navigating a GEDCOM family tree."""

    TITLE = "gedinfo"

    DEFAULT_CSS = """
    Screen   { layout: vertical; }
    #panes   { layout: horizontal; height: 1fr; }
    #left-pane   { width: 1fr;  border: solid $panel;  padding: 0 1; }
    #center-pane { width: 2fr;  border: solid $accent; padding: 0 1; }
    #right-pane  { width: 1fr;  border: solid $panel;  padding: 0 1; }
    """

    BINDINGS = [
        Binding("j",     "cursor_down",     "Down"),
        Binding("k",     "cursor_up",       "Up"),
        Binding("down",  "cursor_down",     ""),
        Binding("up",    "cursor_up",       ""),
        Binding("l",     "navigate_right",  "Children"),
        Binding("right", "navigate_right",  ""),
        Binding("h",     "go_up",           "Parents"),
        Binding("left",  "go_up",           ""),
        Binding("enter", "navigate_select", "Select"),
        Binding("b",     "go_back",         "Back"),
        Binding("r",     "go_to_root",      "Root"),
        Binding("c",     "commands",        "Commands"),
        Binding("/",     "search",          "Search"),
        Binding("o",     "open_file",       "Open file"),
        Binding("q",     "quit",            "Quit"),
    ]

    # cursor_idx is the center-pane-local index: 0 = self, 1 = first spouse, …
    focus_id: reactive[str | None] = reactive(None)
    cursor_idx: reactive[int] = reactive(0)

    def __init__(self, data: GedcomData | None, file_path: str | None) -> None:
        super().__init__()
        self._data = data
        self._file_path = file_path
        self._history: list[str] = []
        self._nav_items: list[NavItem] = []

    # --- lifecycle ---

    def on_mount(self) -> None:
        self.sub_title = self._file_path or "(no file)"
        if self._data and self._data.individuals:
            first = sorted(self._data.individuals.values(), key=lambda i: id_sort_key(i.id))[0]
            self.focus_id = first.id

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panes"):
            yield PersonPane("left",   id="left-pane")
            yield PersonPane("center", id="center-pane")
            yield PersonPane("right",  id="right-pane")
        yield Footer()

    # --- reactive watchers ---

    def watch_focus_id(self, new_id: str | None) -> None:
        if new_id and self._data:
            try:
                self._nav_items = build_nav_items(self._data, new_id, 0)
            except ValueError:
                self._nav_items = []
            self.cursor_idx = 0   # may re-trigger watch_cursor_idx if was already 0
        else:
            self._nav_items = []
        self._refresh_panes()

    def watch_cursor_idx(self, new_cursor: int) -> None:
        # Rebuild nav items so right pane reflects the selected family.
        if self.focus_id and self._data:
            try:
                self._nav_items = build_nav_items(self._data, self.focus_id, new_cursor)
            except ValueError:
                pass
        self._refresh_panes()

    def _refresh_panes(self) -> None:
        try:
            for pane_id in ("left-pane", "center-pane", "right-pane"):
                self.query_one(f"#{pane_id}").refresh()
        except Exception:
            pass

    # --- cursor movement (j/k: within center pane only) ---

    def action_cursor_down(self) -> None:
        center = [i for i in self._nav_items if i.pane == "center"]
        if self.cursor_idx < len(center) - 1:
            self.cursor_idx += 1

    def action_cursor_up(self) -> None:
        if self.cursor_idx > 0:
            self.cursor_idx -= 1

    # --- lateral navigation (h/l: between generations) ---

    def action_navigate_right(self) -> None:
        """l / →: navigate to the first child shown in the right pane."""
        right = [i for i in self._nav_items if i.pane == "right" and i.individual]
        if right:
            self._navigate_to(right[0].individual.id)  # type: ignore[union-attr]

    def action_go_up(self) -> None:
        """h / ←: navigate to the first parent shown in the left pane."""
        left = [i for i in self._nav_items if i.pane == "left" and i.individual]
        if left:
            self._navigate_to(left[0].individual.id)  # type: ignore[union-attr]

    def action_navigate_select(self) -> None:
        """Enter: navigate to the cursor-selected center pane item (e.g. a spouse)."""
        center = [i for i in self._nav_items if i.pane == "center"]
        if 0 <= self.cursor_idx < len(center):
            item = center[self.cursor_idx]
            if item.individual and item.individual.id != self.focus_id:
                self._navigate_to(item.individual.id)

    # --- history ---

    def action_go_back(self) -> None:
        if self._history:
            self.focus_id = self._history.pop()

    def action_go_to_root(self) -> None:
        if not self._data or not self.focus_id:
            return
        root_id = _go_to_root(self._data, self.focus_id)
        if root_id != self.focus_id:
            self._navigate_to(root_id)
        else:
            self.notify("Already at root", timeout=2)

    # --- overlays ---

    def action_search(self) -> None:
        if not self.query(SearchBar):
            self.mount(SearchBar())

    def action_open_file(self) -> None:
        self.push_screen(FilePickerScreen(_find_ged_files()), self._on_file_selected)

    def action_commands(self) -> None:
        if not self._data:
            self.notify("No file loaded", severity="warning")
            return
        self.push_screen(CommandScreen(), self._on_command_selected)

    # --- callbacks from modal screens ---

    def _on_file_selected(self, path: str | None) -> None:
        if path:
            self._load_file(path)

    def _on_command_selected(self, cmd: str | None) -> None:
        if not cmd or not self._data:
            return
        if cmd == "stat":
            self.push_screen(TextResultScreen("Statistics", self._build_stat_text()))
        elif cmd == "roots":
            roots = apply_root_filters(self._data, get_roots(self._data, sort_key="name"))
            self.push_screen(IndividualListScreen("Roots", roots), self._on_individual_selected)
        elif cmd == "leaves":
            leaves = apply_leaf_filters(self._data, get_leaves(self._data, sort_key="name"))
            self.push_screen(IndividualListScreen("Leaves", leaves), self._on_individual_selected)
        elif cmd == "indi":
            indis = get_all_individuals(self._data, sort_key="name")
            self.push_screen(IndividualListScreen("All individuals", indis), self._on_individual_selected)
        elif cmd == "ancestors":
            if not self.focus_id:
                self.notify("No person in focus", severity="warning")
                return
            records = get_ancestor_details(self._data, self.focus_id)
            indis = [r["individual"] for r in records]
            name = display_name(find_by_id(self._data, self.focus_id))  # type: ignore[arg-type]
            self.push_screen(
                IndividualListScreen(f"Ancestors of {name}", indis),
                self._on_individual_selected,
            )
        elif cmd == "descendants":
            if not self.focus_id:
                self.notify("No person in focus", severity="warning")
                return
            records = get_descendant_details(self._data, self.focus_id)
            indis = [r["individual"] for r in records]
            name = display_name(find_by_id(self._data, self.focus_id))  # type: ignore[arg-type]
            self.push_screen(
                IndividualListScreen(f"Descendants of {name}", indis),
                self._on_individual_selected,
            )

    def _on_individual_selected(self, indi_id: str | None) -> None:
        if indi_id:
            self._navigate_to(indi_id)

    # --- internal helpers ---

    def _navigate_to(self, target_id: str) -> None:
        if self.focus_id and self.focus_id != target_id:
            self._history.append(self.focus_id)
        self.focus_id = target_id

    def _load_file(self, path: str) -> None:
        try:
            new_data = parse(path)
        except (GedcomParseError, FileNotFoundError, ValueError) as e:
            self.notify(str(e), severity="error")
            return
        self._data = new_data
        self._file_path = path
        self._history.clear()
        self.sub_title = path
        if new_data.individuals:
            first = sorted(new_data.individuals.values(), key=lambda i: id_sort_key(i.id))[0]
            self.focus_id = first.id
        else:
            self.focus_id = None

    def _build_stat_text(self) -> str:
        data = self._data
        assert data is not None
        n_ind = len(data.individuals)
        n_fam = len(data.families)
        n_roots = len(get_roots(data))
        n_leaves = len(get_leaves(data))
        gens = count_generations(data)
        n_noname = count_no_name(data)
        n_incomplete = count_incomplete_name(data)
        n_comp = len(get_connected_components(data))
        lines = [
            f"Individuals:    {n_ind}",
            f"Families:       {n_fam}",
            f"Roots:          {n_roots}",
            f"Leaves:         {n_leaves}",
            f"Generations:    {gens}",
            f"No name:        {n_noname}",
            f"Incomplete:     {n_incomplete}",
            f"Components:     {n_comp}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_tui(data: GedcomData | None, file_path: str | None) -> None:
    """Entry point called from cli.main()."""
    GedTui(data, file_path).run()
