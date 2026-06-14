"""Interactive TUI for exploring GEDCOM files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import RenderableType
from rich.text import Text
from textual import events
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
    normalise_id,
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

    # --- Center pane: spouses (chronological by marriage year, then GEDCOM order) ---
    def _marr_sort_key(item: tuple[int, str]) -> tuple[int, int]:
        idx, date_str = item
        m = re.search(r'\b(\d{4})\b', date_str) if date_str else None
        return (0, int(m.group(1))) if m else (1, idx)

    sorted_fam_ids = [
        fam_id
        for _, fam_id in sorted(
            ((i, fam_id) for i, fam_id in enumerate(indi.family_ids_as_spouse)),
            key=lambda x: _marr_sort_key((
                x[0],
                (data.families[x[1]].marriage_date or "") if x[1] in data.families else "",
            )),
        )
    ]
    for fam_id in sorted_fam_ids:
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


def _fmt_path(path: str, max_len: int = 52) -> str:
    """Truncate a path to max_len by keeping the head and tail with '...' in the middle."""
    if len(path) <= max_len:
        return path
    ellipsis = "..."
    keep = max_len - len(ellipsis)
    head = keep // 3
    tail = keep - head
    return path[:head] + ellipsis + path[-tail:]


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
# Vim-scrollable ListView
# ---------------------------------------------------------------------------

class VimListView(ListView):
    """ListView that adds ctrl+d/u/f/b for half/full-page vim scrolling.

    Also handles Enter directly in on_key so it fires before the app-level
    binding chain has a chance to intercept it.
    """

    BINDINGS = [
        Binding("enter",  "select_cursor",    show=False),
        Binding("ctrl+d", "scroll_half_down", show=False),
        Binding("ctrl+u", "scroll_half_up",   show=False),
        Binding("ctrl+f", "scroll_full_down", show=False),
        Binding("ctrl+b", "scroll_full_up",   show=False),
    ]

    def on_key(self, event: events.Key) -> None:
        """Handle Enter directly to guarantee it fires before app-level bindings."""
        if event.key == "enter":
            self.action_select_cursor()
            event.stop()

    def _item_count(self) -> int:
        return len(self._nodes)

    def _move(self, delta: int) -> None:
        n = self._item_count()
        if n == 0:
            return
        self.index = max(0, min(n - 1, (self.index or 0) + delta))

    def action_scroll_half_down(self) -> None:
        self._move(max(1, self.size.height // 2))

    def action_scroll_half_up(self) -> None:
        self._move(-max(1, self.size.height // 2))

    def action_scroll_full_down(self) -> None:
        self._move(max(1, self.size.height))

    def action_scroll_full_up(self) -> None:
        self._move(-max(1, self.size.height))


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
            normal_mode = not app._in_child_selection and not app._in_parent_selection
            show_ids = app.show_ids
        except Exception:
            return Text("")

        try:
            css = app.get_css_variables()
            accent = css.get("accent-darken-2") or css.get("accent", "")
            hint_style = f"bold {accent}" if accent else "bold yellow"
        except Exception:
            hint_style = "bold yellow"

        # Index of first spouse item in center pane (for the 's' hint)
        first_spouse_idx = next(
            (i for i, it in enumerate(items) if self._pane_id == "center" and it.label != "self:"),
            None,
        )

        lines = Text()
        for enum_idx, item in enumerate(items):
            is_cursor = self._pane_id == "center" and enum_idx == center_cursor
            name = display_name(item.individual) if item.individual else "(unknown)"
            id_str = item.individual.id.strip("@") if (item.individual and show_ids) else ""
            id_part = f" ({id_str})" if id_str else ""

            # Main line: label + name + (ID)
            if self._pane_id == "center":
                if is_cursor:
                    # Cursor row: everything in bold reverse, no dimming
                    lines.append(f"► {item.label} {name}{id_part}\n", style="bold reverse")
                else:
                    if normal_mode and enum_idx == first_spouse_idx and item.individual:
                        lines.append("s", style=hint_style)
                        lines.append(" ")
                    else:
                        lines.append("  ")
                    lines.append(f"{item.label} ", style="dim")
                    lines.append(name)
                    if id_str:
                        lines.append(f" ({id_str})", style="dim")
                    lines.append("\n")
            else:
                hint = " "
                if normal_mode and item.individual:
                    if self._pane_id == "left":
                        if item.label == "father:":
                            hint = "f"
                        elif item.label == "mother:":
                            hint = "m"
                    elif self._pane_id == "right" and enum_idx < 9:
                        hint = str(enum_idx + 1)
                if hint != " ":
                    lines.append(hint, style=hint_style)
                    lines.append(" ")
                else:
                    lines.append("  ")
                lines.append(f"{item.label} ", style="dim")
                lines.append(name)
                if id_str:
                    lines.append(f" ({id_str})", style="dim")
                lines.append("\n")

            # Sub-line: sex + date info (only for center pane)
            if self._pane_id == "center":
                sub_parts: list[str] = []
                if item.label == "self:" and item.individual:
                    sex_str = {"M": "male", "F": "female"}.get(item.individual.sex, "")
                    if sex_str:
                        sub_parts.append(sex_str)
                if item.date_hint:
                    sub_parts.append(item.date_hint)
                if show_ids and item.label != "self:" and item.family_id:
                    sub_parts.append(f"({item.family_id.strip('@')})")
                if sub_parts:
                    lines.append(f"    {' · '.join(sub_parts)}\n", style="dim")
            elif item.date_hint:
                lines.append(f"    {item.date_hint}\n", style="dim")

        return lines


# ---------------------------------------------------------------------------
# Status pane
# ---------------------------------------------------------------------------

class StatusPane(Widget):
    """Persistent pane showing details about the currently focused individual."""

    DEFAULT_CSS = """
    StatusPane {
        height: 4;
        border-top: solid $accent;
        background: $surface;
        padding: 0 1;
    }
    """

    def render(self) -> RenderableType:
        try:
            app: GedTui = self.app  # type: ignore[assignment]
            if not app.focus_id or not app._data:
                return Text("No individual in focus", style="dim")
            indi = find_by_id(app._data, app.focus_id)
            if not indi:
                return Text("")
        except Exception:
            return Text("")

        lines = Text()

        # Line 1: name (ID) · sex · birth · death
        name = display_name(indi)
        id_str = indi.id.strip("@")
        show_ids = getattr(app, "show_ids", False)
        sex_str = {"M": "male", "F": "female"}.get(indi.sex, "")
        parts1: list[str] = [f"{name} ({id_str})" if show_ids else name]
        if sex_str:
            parts1.append(sex_str)
        if indi.birth_date:
            parts1.append(f"b. {indi.birth_date}")
        if indi.death_date:
            parts1.append(f"d. {indi.death_date}")
        lines.append(" · ".join(parts1) + "\n", style="bold")

        # Line 2: parents | spouses count | children count
        parents: list[str] = []
        for fam_id in indi.family_ids_as_child:
            fam = app._data.families.get(fam_id)
            if not fam:
                continue
            for pid in [fam.husband_id, fam.wife_id]:
                if pid:
                    p = app._data.individuals.get(pid)
                    if p:
                        parents.append(display_name(p))

        n_children = sum(
            len(app._data.families[fam_id].child_ids)
            for fam_id in indi.family_ids_as_spouse
            if fam_id in app._data.families
        )
        n_spouses = len(indi.family_ids_as_spouse)

        parts2: list[str] = []
        if parents:
            parts2.append("Parents: " + ", ".join(parents))
        parts2.append(f"Spouses: {n_spouses}")
        parts2.append(f"Children: {n_children}")
        lines.append("  ".join(parts2) + "\n", style="dim")

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

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.remove()
            event.stop()

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
        if len(results) == 1:
            app._navigate_to(results[0].id)
            return
        # Multiple matches: show a navigable list.
        # Use app._context() so active_message_pump is the App, not this
        # SearchBar (which is already removed).  Without this, Textual
        # registers the dismiss callback on the SearchBar's dead pump and
        # _on_individual_selected is never called.
        with app._context():
            app.push_screen(
                IndividualListScreen(f'Search: "{query}"', results),
                app._on_individual_selected,
            )


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
                yield VimListView(*[_FileItem(f) for f in self._files], id="file-list")
                yield Label("", id="path-status")
            else:
                yield Label("(no *.ged files found in current directory or subdirectories)")

    def on_mount(self) -> None:
        if self._files:
            lv = self.query_one(VimListView)
            lv.focus()
            self.query_one("#path-status", Label).update(
                _fmt_path(str(self._files[0]))
            )
        else:
            self.query_one("#path-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        path = event.value.strip()
        if path:
            self.dismiss(path)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Show truncated full path in the status label when an item is highlighted."""
        try:
            status = self.query_one("#path-status", Label)
            if event.item and isinstance(event.item, _FileItem):
                status.update(_fmt_path(str(event.item.path)))
            else:
                status.update("")
        except Exception:
            pass

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
    ("lastnames",   "Distinct last names in ancestor tree"),
    ("givennames",  "Distinct given names in ancestor tree"),
]

# Explicit shortcut letter for each command (letter → cmd, cmd → letter).
_CMD_SHORTCUTS: dict[str, str] = {
    "stat":        "s",
    "roots":       "r",
    "leaves":      "v",  # lea[v]es
    "indi":        "i",
    "ancestors":   "a",
    "descendants": "d",
    "lastnames":   "l",  # [l]astnames
    "givennames":  "g",
}
_letter_to_cmd: dict[str, str] = {v: k for k, v in _CMD_SHORTCUTS.items()}


class _CmdItem(ListItem):
    def __init__(self, cmd: str, desc: str, *, accent: str = "") -> None:
        shortcut = _CMD_SHORTCUTS.get(cmd)
        if shortcut:
            style = f"bold {accent}" if accent else "bold"
            pos = cmd.index(shortcut)
            padding = " " * (14 - len(cmd))
            markup = f"{cmd[:pos]}[{style}]{shortcut}[/]{cmd[pos + 1:]}{padding}{desc}"
        else:
            markup = f"{cmd:<14}{desc}"
        super().__init__(Label(markup))
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
        try:
            css = self.app.get_css_variables()
            accent = css.get("accent-darken-2") or css.get("accent", "")
        except Exception:
            accent = ""
        with Vertical(id="cmd-dialog"):
            yield Label("Commands", id="cmd-title")
            yield VimListView(*[_CmdItem(cmd, desc, accent=accent) for cmd, desc in _COMMANDS], id="cmd-list")

    def on_mount(self) -> None:
        self.query_one(VimListView).focus()

    def on_key(self, event: events.Key) -> None:
        if event.key in _letter_to_cmd:
            self.dismiss(_letter_to_cmd[event.key])
            event.stop()

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

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select_item", "Select", priority=True),
    ]

    DEFAULT_CSS = """
    IndividualListScreen { align: center middle; }
    #list-dialog {
        width: 72;
        height: auto;
        max-height: 32;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #list-title   { text-style: bold; }
    #list-count   { color: $text-disabled; margin-bottom: 1; }
    #indi-list    { height: auto; max-height: 20; }
    #indi-hint    { color: $text-disabled; margin-top: 1; }
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
                yield VimListView(*[_IndiItem(i) for i in self._individuals], id="indi-list")
            else:
                yield Label("(none)")
            yield Label("↵ Select  Esc Cancel  ctrl+d/u Scroll", id="indi-hint")

    def on_mount(self) -> None:
        if self._individuals:
            self.call_after_refresh(lambda: self.query_one("#indi-list").focus())

    def action_select_item(self) -> None:
        try:
            lv = self.query_one("#indi-list", VimListView)
            item = lv.highlighted_child
            if isinstance(item, _IndiItem):
                self.dismiss(item.individual.id)
        except Exception:
            pass

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
    Screen        { layout: vertical; }
    #panes        { layout: horizontal; height: 1fr; }
    #left-pane    { width: 30%;  border: solid $panel;  padding: 0 1; }
    #center-pane  { width: 40%;  border: solid $accent; padding: 0 1; }
    #right-pane   { width: 30%;  border: solid $panel;  padding: 0 1; }
    StatusPane    { height: 4;   border-top: solid $accent; background: $surface; padding: 0 1; }
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
        Binding("i",     "toggle_ids",       "IDs"),
        Binding("f",     "go_father",       show=False),
        Binding("m",     "go_mother",       show=False),
        Binding("s",     "go_spouse",       show=False),
        Binding("1",     "child_1",         show=False),
        Binding("2",     "child_2",         show=False),
        Binding("3",     "child_3",         show=False),
        Binding("4",     "child_4",         show=False),
        Binding("5",     "child_5",         show=False),
        Binding("6",     "child_6",         show=False),
        Binding("7",     "child_7",         show=False),
        Binding("8",     "child_8",         show=False),
        Binding("9",     "child_9",         show=False),
    ]

    # cursor_idx is the center-pane-local index: 0 = self, 1 = first spouse, …
    # In child-selection mode it is the index into _children_for_selection.
    focus_id: reactive[str | None] = reactive(None)
    cursor_idx: reactive[int] = reactive(0)
    show_ids: reactive[bool] = reactive(False)

    def __init__(self, data: GedcomData | None, file_path: str | None, *, initial_id: str | None = None) -> None:
        super().__init__()
        self._data = data
        self._file_path = file_path
        self._initial_id = initial_id
        self._history: list[str] = []
        self._nav_items: list[NavItem] = []
        # Child-selection mode state
        self._in_child_selection: bool = False
        self._children_for_selection: list[Individual] = []
        # Parent-selection mode state
        self._in_parent_selection: bool = False
        self._parents_for_selection: list[Individual] = []

    # --- lifecycle ---

    def on_mount(self) -> None:
        self.sub_title = self._file_path or "(no file)"
        if self._data and self._data.individuals:
            if self._initial_id:
                norm = normalise_id(self._initial_id)
                start = self._data.individuals.get(norm)
            else:
                start = None
            if start is None:
                start = sorted(self._data.individuals.values(), key=lambda i: id_sort_key(i.id))[0]
            self.focus_id = start.id

    def on_resize(self, event: events.Resize) -> None:
        w = event.size.width
        side = w * 30 // 100
        self.query_one("#left-pane").styles.width = side
        self.query_one("#right-pane").styles.width = side
        self.query_one("#center-pane").styles.width = w - 2 * side

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panes"):
            yield PersonPane("left",   id="left-pane")
            yield PersonPane("center", id="center-pane")
            yield PersonPane("right",  id="right-pane")
        yield StatusPane()
        yield Footer()

    # --- reactive watchers ---

    def watch_focus_id(self, new_id: str | None) -> None:
        self._in_child_selection = False  # always leave selection modes on navigation
        self._in_parent_selection = False
        if new_id and self._data:
            try:
                self._nav_items = build_nav_items(self._data, new_id, 0)
            except ValueError:
                self._nav_items = []
            self.cursor_idx = 0
        else:
            self._nav_items = []
        self._refresh_panes()

    def watch_cursor_idx(self, new_cursor: int) -> None:
        if self._in_child_selection:
            self._nav_items = self._build_child_selection_items(new_cursor)
        elif self._in_parent_selection:
            self._nav_items = self._build_parent_selection_items(new_cursor)
        elif self.focus_id and self._data:
            try:
                self._nav_items = build_nav_items(self._data, self.focus_id, new_cursor)
            except ValueError:
                pass
        self._refresh_panes()

    def watch_show_ids(self, _: bool) -> None:
        self._refresh_panes()

    def _refresh_panes(self) -> None:
        try:
            for pane_id in ("left-pane", "center-pane", "right-pane"):
                self.query_one(f"#{pane_id}").refresh()
            self.query_one(StatusPane).refresh()
        except Exception:
            pass

    # --- child selection mode helpers ---

    def _build_child_selection_items(self, cursor: int) -> list[NavItem]:
        """Build nav items for child-selection mode.

        Left: focus person (as context). Center: children to choose from.
        Right: live preview of the highlighted child's spouses and their children.
        """
        data = self._data
        if not data or not self.focus_id:
            return []
        focus = find_by_id(data, self.focus_id)
        if not focus:
            return []

        left: list[NavItem] = []
        center: list[NavItem] = []
        right: list[NavItem] = []

        # Left pane: show focus person as "where you came from"
        focus_dates: list[str] = []
        if focus.birth_date:
            focus_dates.append(focus.birth_date)
        if focus.death_date:
            focus_dates.append(focus.death_date)
        left.append(NavItem(
            label="self:",
            individual=focus,
            date_hint=" – ".join(focus_dates),
            pane="left",
            idx=0,
        ))

        # Center pane: the children the user is choosing between
        for child in self._children_for_selection:
            c_dates: list[str] = []
            if child.birth_date:
                c_dates.append(child.birth_date)
            if child.death_date:
                c_dates.append(child.death_date)
            center.append(NavItem(
                label=_child_label(child),
                individual=child,
                date_hint=" – ".join(c_dates),
                pane="center",
                idx=0,
            ))

        # Right pane: preview of the highlighted child's family
        safe = min(cursor, len(center) - 1) if center else 0
        if center and 0 <= safe < len(center):
            child_indi = center[safe].individual
            if child_indi:
                try:
                    child_items = build_nav_items(data, child_indi.id)
                    # Spouses of the child (center items except self)
                    for item in child_items:
                        if item.pane == "center" and item.label != "self:":
                            right.append(NavItem(
                                label=item.label,
                                individual=item.individual,
                                date_hint=item.date_hint,
                                pane="right",
                                idx=0,
                            ))
                    # Children of the child
                    for item in child_items:
                        if item.pane == "right":
                            right.append(NavItem(
                                label=item.label,
                                individual=item.individual,
                                date_hint=item.date_hint,
                                pane="right",
                                idx=0,
                            ))
                except ValueError:
                    pass

        all_items = left + center + right
        for i, item in enumerate(all_items):
            item.idx = i
        return all_items

    def _enter_child_selection(self, children: list[Individual]) -> None:
        self._children_for_selection = children
        self._in_child_selection = True
        # cursor_idx may already be 0; force-rebuild regardless
        self._nav_items = self._build_child_selection_items(0)
        if self.cursor_idx != 0:
            self.cursor_idx = 0  # watcher will rebuild, harmless double
        self._refresh_panes()

    def _cancel_child_selection(self) -> None:
        self._in_child_selection = False
        self._children_for_selection = []
        if self.focus_id and self._data:
            try:
                self._nav_items = build_nav_items(self._data, self.focus_id, 0)
            except ValueError:
                self._nav_items = []
        if self.cursor_idx != 0:
            self.cursor_idx = 0
        else:
            self._refresh_panes()

    def _build_parent_selection_items(self, cursor: int) -> list[NavItem]:
        """Build nav items for parent-selection mode.

        Left: grandparents (parents of the highlighted parent, live preview).
        Center: parents of focus person — the list to choose between.
        Right: focus person (the child context, with their spouses).
        """
        data = self._data
        if not data or not self.focus_id:
            return []
        focus = find_by_id(data, self.focus_id)
        if not focus:
            return []

        left: list[NavItem] = []
        center: list[NavItem] = []
        right: list[NavItem] = []

        # Center: parents the user is choosing between
        for parent in self._parents_for_selection:
            p_dates: list[str] = []
            if parent.birth_date:
                p_dates.append(parent.birth_date)
            if parent.death_date:
                p_dates.append(parent.death_date)
            center.append(NavItem(
                label=_parent_label(parent),
                individual=parent,
                date_hint=" – ".join(p_dates),
                pane="center",
                idx=0,
            ))

        # Left: grandparents of the highlighted parent
        safe = min(cursor, len(center) - 1) if center else 0
        if center and 0 <= safe < len(center):
            parent_indi = center[safe].individual
            if parent_indi:
                try:
                    gp_items = build_nav_items(data, parent_indi.id)
                    for item in gp_items:
                        if item.pane == "left":
                            left.append(NavItem(
                                label=item.label,
                                individual=item.individual,
                                date_hint=item.date_hint,
                                pane="left",
                                idx=0,
                            ))
                except ValueError:
                    pass

        # Right: focus person and their spouses (the "child" context)
        focus_dates: list[str] = []
        if focus.birth_date:
            focus_dates.append(focus.birth_date)
        if focus.death_date:
            focus_dates.append(focus.death_date)
        right.append(NavItem(
            label="self:",
            individual=focus,
            date_hint=" – ".join(focus_dates),
            pane="right",
            idx=0,
        ))
        for fam_id in focus.family_ids_as_spouse:
            fam = data.families.get(fam_id)
            if not fam:
                continue
            other_id = fam.wife_id if fam.husband_id == focus.id else fam.husband_id
            if not other_id:
                continue
            spouse = data.individuals.get(other_id)
            if spouse:
                right.append(NavItem(
                    label=_spouse_label(spouse),
                    individual=spouse,
                    date_hint=f"m. {fam.marriage_date}" if fam.marriage_date else "",
                    pane="right",
                    idx=0,
                ))

        all_items = left + center + right
        for i, item in enumerate(all_items):
            item.idx = i
        return all_items

    def _enter_parent_selection(self, parents: list[Individual]) -> None:
        self._parents_for_selection = parents
        self._in_parent_selection = True
        self._nav_items = self._build_parent_selection_items(0)
        if self.cursor_idx != 0:
            self.cursor_idx = 0
        self._refresh_panes()

    def _cancel_parent_selection(self) -> None:
        self._in_parent_selection = False
        self._parents_for_selection = []
        if self.focus_id and self._data:
            try:
                self._nav_items = build_nav_items(self._data, self.focus_id, 0)
            except ValueError:
                self._nav_items = []
        if self.cursor_idx != 0:
            self.cursor_idx = 0
        else:
            self._refresh_panes()

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
        """l / →: confirm child-selection, cancel parent-selection, or enter children."""
        if self._in_child_selection:
            self.action_navigate_select()
            return
        if self._in_parent_selection:
            # Going right from parent-selection = go back to child (cancel)
            self._cancel_parent_selection()
            return
        right = [i for i in self._nav_items if i.pane == "right" and i.individual]
        if not right:
            self.notify("No children", timeout=2)
            return
        if len(right) == 1:
            self._navigate_to(right[0].individual.id)  # type: ignore[union-attr]
            return
        children = [i.individual for i in right]  # type: ignore[misc]
        self._enter_child_selection(children)

    def action_go_up(self) -> None:
        """h / ←: confirm parent-selection, cancel child-selection, or enter parents."""
        if self._in_parent_selection:
            self.action_navigate_select()
            return
        if self._in_child_selection:
            self._cancel_child_selection()
            return
        left = [i for i in self._nav_items if i.pane == "left" and i.individual]
        if not left:
            return
        if len(left) == 1:
            self._navigate_to(left[0].individual.id)  # type: ignore[union-attr]
            return
        parents = [i.individual for i in left]  # type: ignore[misc]
        self._enter_parent_selection(parents)

    def action_toggle_ids(self) -> None:
        self.show_ids = not self.show_ids

    def action_go_father(self) -> None:
        if self._in_child_selection or self._in_parent_selection:
            return
        left = [i for i in self._nav_items if i.pane == "left" and i.label == "father:" and i.individual]
        if left:
            self._navigate_to(left[0].individual.id)  # type: ignore[union-attr]

    def action_go_mother(self) -> None:
        if self._in_child_selection or self._in_parent_selection:
            return
        left = [i for i in self._nav_items if i.pane == "left" and i.label == "mother:" and i.individual]
        if left:
            self._navigate_to(left[0].individual.id)  # type: ignore[union-attr]

    def action_go_spouse(self) -> None:
        if self._in_child_selection or self._in_parent_selection:
            return
        spouses = [i for i in self._nav_items if i.pane == "center" and i.label != "self:" and i.individual]
        if spouses:
            self._navigate_to(spouses[0].individual.id)  # type: ignore[union-attr]

    def _go_to_child(self, n: int) -> None:
        if self._in_child_selection or self._in_parent_selection:
            return
        right = [i for i in self._nav_items if i.pane == "right" and i.individual]
        if 1 <= n <= len(right):
            self._navigate_to(right[n - 1].individual.id)  # type: ignore[union-attr]

    def action_child_1(self) -> None: self._go_to_child(1)
    def action_child_2(self) -> None: self._go_to_child(2)
    def action_child_3(self) -> None: self._go_to_child(3)
    def action_child_4(self) -> None: self._go_to_child(4)
    def action_child_5(self) -> None: self._go_to_child(5)
    def action_child_6(self) -> None: self._go_to_child(6)
    def action_child_7(self) -> None: self._go_to_child(7)
    def action_child_8(self) -> None: self._go_to_child(8)
    def action_child_9(self) -> None: self._go_to_child(9)

    def action_navigate_select(self) -> None:
        """Enter: confirm selection or navigate to selected center item."""
        center = [i for i in self._nav_items if i.pane == "center"]
        if 0 <= self.cursor_idx < len(center):
            item = center[self.cursor_idx]
            if item.individual and item.individual.id != self.focus_id:
                self._in_child_selection = False
                self._in_parent_selection = False
                self._navigate_to(item.individual.id)

    # --- history ---

    def action_go_back(self) -> None:
        if self._in_child_selection:
            self._cancel_child_selection()
            return
        if self._in_parent_selection:
            self._cancel_parent_selection()
            return
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
        elif cmd == "lastnames":
            if not self.focus_id:
                self.notify("No person in focus", severity="warning")
                return
            records = get_ancestor_details(self._data, self.focus_id)
            focus_name = display_name(find_by_id(self._data, self.focus_id))  # type: ignore[arg-type]
            names = sorted({r["individual"].last_name for r in records if r["individual"].last_name})
            text = f"{len(names)} distinct last names · ancestors of {focus_name}\n\n" + "\n".join(names)
            self.push_screen(TextResultScreen("Last names", text))
        elif cmd == "givennames":
            if not self.focus_id:
                self.notify("No person in focus", severity="warning")
                return
            records = get_ancestor_details(self._data, self.focus_id)
            focus_name = display_name(find_by_id(self._data, self.focus_id))  # type: ignore[arg-type]
            names = sorted({r["individual"].first_name for r in records if r["individual"].first_name})
            text = f"{len(names)} distinct given names · ancestors of {focus_name}\n\n" + "\n".join(names)
            self.push_screen(TextResultScreen("Given names", text))

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

def run_tui(data: GedcomData | None, file_path: str | None, *, initial_id: str | None = None) -> None:
    """Entry point called from the explore command."""
    GedTui(data, file_path, initial_id=initial_id).run()
