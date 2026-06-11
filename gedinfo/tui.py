"""Interactive TUI for exploring GEDCOM files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rich.console import RenderableType
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Header, Input

from .models import GedcomData, Individual
from .parser import GedcomParseError, parse
from .queries import display_name, find_by_id, find_by_name, id_sort_key


@dataclass
class NavItem:
    label: str
    individual: Optional[Individual]
    date_hint: str  # birth/death dates for self, "m. DATE" for spouses, "" otherwise
    pane: str       # "left", "center", or "right"
    idx: int        # position in the flat navigation list


def _parent_label(indi: Individual) -> str:
    return {"M": "father:", "F": "mother:"}.get(indi.sex, "parent:")


def _spouse_label(indi: Individual) -> str:
    return {"M": "husband:", "F": "wife:"}.get(indi.sex, "spouse:")


def _child_label(indi: Individual) -> str:
    return {"M": "son:", "F": "daughter:"}.get(indi.sex, "child:")


def build_nav_items(data: GedcomData, focus_id: str) -> list[NavItem]:
    """Return the flat navigation list for the given focus individual.

    Order: left-pane items (parents), then center-pane items (self + spouses),
    then right-pane items (children). Items are assigned sequential idx values
    starting at 0. Raises ValueError if focus_id is not found.
    """
    indi = find_by_id(data, focus_id)
    if indi is None:
        raise ValueError(f"Unknown individual ID: {focus_id}")

    items: list[NavItem] = []

    # Left pane: parents
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
            items.append(NavItem(
                label=_parent_label(parent),
                individual=parent,
                date_hint="",
                pane="left",
                idx=0,
            ))

    # Center pane: self
    parts = []
    if indi.birth_date:
        parts.append(indi.birth_date)
    if indi.death_date:
        parts.append(indi.death_date)
    self_date_hint = " – ".join(parts)
    items.append(NavItem(
        label="self:",
        individual=indi,
        date_hint=self_date_hint,
        pane="center",
        idx=0,
    ))

    # Center pane: spouses
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
        marriage_hint = f"m. {fam.marriage_date}" if fam.marriage_date else ""
        items.append(NavItem(
            label=_spouse_label(spouse),
            individual=spouse,
            date_hint=marriage_hint,
            pane="center",
            idx=0,
        ))

    # Right pane: children across all marriages
    for fam_id in indi.family_ids_as_spouse:
        fam = data.families.get(fam_id)
        if fam is None:
            continue
        for child_id in fam.child_ids:
            child = data.individuals.get(child_id)
            if child is None:
                continue
            items.append(NavItem(
                label=_child_label(child),
                individual=child,
                date_hint="",
                pane="right",
                idx=0,
            ))

    # Assign sequential idx values across all panes
    for i, item in enumerate(items):
        item.idx = i

    return items


class PersonPane(Widget):
    """Renders one column (left/center/right) of the family view."""

    def __init__(self, pane_id: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._pane_id = pane_id

    def render(self) -> RenderableType:
        try:
            app: GedTui = self.app  # type: ignore[assignment]
            items = [i for i in app._nav_items if i.pane == self._pane_id]
            cursor = app.cursor_idx
        except Exception:
            return Text("")

        lines = Text()
        for item in items:
            is_cursor = item.idx == cursor
            prefix = "► " if is_cursor else "  "
            name = display_name(item.individual) if item.individual else "(unknown)"
            style = "bold reverse" if is_cursor else ""
            lines.append(f"{prefix}{item.label} {name}\n", style=style)
            if item.date_hint:
                lines.append(f"    {item.date_hint}\n", style="dim")
        return lines


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
        yield Input(placeholder="Search by name or ID — press Enter to confirm, Esc to cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        self.remove()
        if not query:
            return
        app: GedTui = self.app  # type: ignore[assignment]
        if not app._data:
            return
        by_id = find_by_id(app._data, query)
        if by_id is not None:
            if app.focus_id:
                app._history.append(app.focus_id)
            app.focus_id = by_id.id
            return
        results = find_by_name(app._data, query)
        if not results:
            app.sub_title = f"{app._file_path or '(no file)'} — not found: {query!r}"
            return
        if app.focus_id:
            app._history.append(app.focus_id)
        app.focus_id = results[0].id
        if len(results) > 1:
            app.sub_title = f"{app._file_path or '(no file)'} — {len(results)} matches, showing first"

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key == "escape":
            event.stop()
            self.remove()


class FileBar(Widget):
    """Inline file-path input docked at the bottom of the screen."""

    DEFAULT_CSS = """
    FileBar {
        height: 3;
        dock: bottom;
        background: $panel;
        border-top: solid $accent;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Path to GEDCOM file — press Enter to open, Esc to cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        path = event.value.strip()
        if not path:
            self.remove()
            return
        app: GedTui = self.app  # type: ignore[assignment]
        try:
            new_data = parse(path)
        except (GedcomParseError, FileNotFoundError, ValueError) as e:
            self.query_one(Input).value = ""
            app.sub_title = f"Error: {e}"
            return
        app._data = new_data
        app._file_path = path
        app._history.clear()
        app.sub_title = path
        self.remove()
        if new_data.individuals:
            first = sorted(new_data.individuals.values(), key=lambda i: id_sort_key(i.id))[0]
            app.focus_id = first.id
        else:
            app.focus_id = None

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key == "escape":
            event.stop()
            self.remove()


class GedTui(App):
    """Interactive TUI for navigating a GEDCOM family tree."""

    TITLE = "gedinfo"

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }

    #panes {
        layout: horizontal;
        height: 1fr;
    }

    #left-pane {
        width: 1fr;
        border: solid $panel-lighten-1;
        padding: 0 1;
    }

    #center-pane {
        width: 2fr;
        border: solid $accent;
        padding: 0 1;
    }

    #right-pane {
        width: 1fr;
        border: solid $panel-lighten-1;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("j",     "cursor_down", "Down"),
        Binding("k",     "cursor_up",   "Up"),
        Binding("down",  "cursor_down", ""),
        Binding("up",    "cursor_up",   ""),
        Binding("l",     "navigate",    "Navigate"),
        Binding("right", "navigate",    ""),
        Binding("enter", "navigate",    "Navigate"),
        Binding("h",     "go_up",       "Parents"),
        Binding("left",  "go_up",       ""),
        Binding("b",     "go_back",     "Back"),
        Binding("/",     "search",      "Search"),
        Binding("o",     "open_file",   "Open file"),
        Binding("q",     "quit",        "Quit"),
    ]

    focus_id: reactive[str | None] = reactive(None)
    cursor_idx: reactive[int] = reactive(0)

    def __init__(self, data: GedcomData | None, file_path: str | None) -> None:
        super().__init__()
        self._data = data
        self._file_path = file_path
        self._history: list[str] = []
        self._nav_items: list[NavItem] = []

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

    def watch_focus_id(self, new_id: str | None) -> None:
        if new_id and self._data:
            self._nav_items = build_nav_items(self._data, new_id)
            self.cursor_idx = 0
        else:
            self._nav_items = []
        self._refresh_panes()

    def watch_cursor_idx(self, _: int) -> None:
        self._refresh_panes()

    def _refresh_panes(self) -> None:
        try:
            for pane_id in ("left-pane", "center-pane", "right-pane"):
                self.query_one(f"#{pane_id}").refresh()
        except Exception:
            pass

    def action_cursor_down(self) -> None:
        if self._nav_items:
            self.cursor_idx = min(self.cursor_idx + 1, len(self._nav_items) - 1)

    def action_cursor_up(self) -> None:
        self.cursor_idx = max(self.cursor_idx - 1, 0)

    def action_navigate(self) -> None:
        item = self._current_item()
        if item and item.individual and self.focus_id:
            self._history.append(self.focus_id)
            self.focus_id = item.individual.id

    def action_go_up(self) -> None:
        parents = [i for i in self._nav_items if i.pane == "left" and i.individual]
        if parents and self.focus_id:
            self._history.append(self.focus_id)
            self.focus_id = parents[0].individual.id  # type: ignore[union-attr]

    def action_go_back(self) -> None:
        if self._history:
            self.focus_id = self._history.pop()

    def action_search(self) -> None:
        if not self.query(SearchBar) and not self.query(FileBar):
            self.mount(SearchBar())

    def action_open_file(self) -> None:
        if not self.query(SearchBar) and not self.query(FileBar):
            self.mount(FileBar())

    def _current_item(self) -> NavItem | None:
        if 0 <= self.cursor_idx < len(self._nav_items):
            return self._nav_items[self.cursor_idx]
        return None


def run_tui(data: GedcomData | None, file_path: str | None) -> None:
    """Entry point called from cli.main()."""
    app = GedTui(data, file_path)
    app.run()
