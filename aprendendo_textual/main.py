from pathlib import Path

from terminal import ScriptFinished, Terminal
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
)

BASE_DIR = Path(__file__).parent
SCRIPT_DIR = BASE_DIR / "scripts"


class SuccessDialog(ModalScreen[None]):
    """Diálogo modal exibido quando um script termina com exit code 0."""

    DEFAULT_CSS = """
    SuccessDialog {
        align: center middle;
    }
    SuccessDialog > Vertical {
        width: auto;
        height: auto;
        padding: 1 2;
        border: solid $success;
        background: $surface;
    }
    SuccessDialog Label {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }
    SuccessDialog Button {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Script executado com sucesso")
            yield Button("Finalizar", id="finalizar", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "finalizar":
            self.dismiss()


class TerminalApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #content {
        height: 1fr;
    }
    #menu {
        width: 30;
        border: solid $primary;
    }
    #terminal-container {
        width: 1fr;
        border: solid $primary;
    }
    #info-panel {
        width: 1fr;
        height: 1fr;
    }
    TerminalWidget {
        width: 1fr;
        height: 1fr;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Sair"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="content"):
            with Vertical(id="menu"):
                yield Label("Scripts")
                yield ListView(
                    ListItem(
                        Label("Hello"),
                        id="hello",
                    ),
                    id="script-list",
                )
            with VerticalScroll(id="terminal-container"):
                with Vertical(id="info-panel"):
                    yield Static("logo")
                    yield Static("menu")
                yield Terminal(id="terminal")
        yield Footer()

    def on_mount(self) -> None:
        # o terminal começa escondido; só aparece quando um script é
        # disparado pelo ListView.
        self.query_one("#terminal", Terminal).display = False

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id == "hello":
            self.run_script("test.sh")

    def run_script(self, script_name: str) -> None:
        script = SCRIPT_DIR / script_name

        info_panel = self.query_one("#info-panel")
        terminal = self.query_one("#terminal", Terminal)

        info_panel.display = False
        terminal.display = True

        # Importante: o terminal precisa receber o foco para que
        # as teclas (inclusive a senha do sudo) sejam enviadas ao pty.
        terminal.focus()
        terminal.run_script(str(script))

    def on_script_finished(self, message: ScriptFinished) -> None:
        if message.exit_code == 0:
            self.push_screen(SuccessDialog(), callback=self._voltar_para_home)
        else:
            self.notify(f"erro (exit {message.exit_code})", severity="error")

    def _voltar_para_home(self, _result: None = None) -> None:
        info_panel = self.query_one("#info-panel")
        terminal = self.query_one("#terminal", Terminal)

        terminal.display = False
        info_panel.display = True


if __name__ == "__main__":
    TerminalApp().run()
