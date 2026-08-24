from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
)

OPTIONS_DATA: dict[str, list[str]] = {
    "Informatica": ["teclado", "mouse", "monitor", "notebook"],
    "Esporte_e_lazer": ["camisa_esportiva", "chuteira"],
    "Automotivo": ["volante"],
}

DESCRIPTIONS: dict[str, str] = {
    "teclado": "Periferico de entrada para computadores",
    "mouse": "Periferico de entrada para computadores",
    "monitor": "Periferico de saida para computadores",
    "notebook": "Computador portatil",
    "camisa_esportiva": "Camisa destinada para pratica de esportes",
    "chuteira": "Calçado destinado para pratica de esportes",
    "volante": "Ferramenta utilizada para direcionar o veiculo",
}

DEFAULT_DESCRIPTION = "Sem descrição disponível para esta opção."


class CategoryScreen(Screen):
    def __init__(self, categoria: str, itens: list[str]) -> None:
        super().__init__()
        self.categoria = categoria
        self.itens = itens

    def compose(self) -> ComposeResult:
        for item in self.itens:
            yield Button(item, classes="column")

        yield Button("voltar", classes="column", id="pop")


class TUIInstaller(Screen):
    """Protótipo de tela: seleção de pacotes/apps em categorias."""

    BINDINGS = [
        ("q", "quit", "Sair"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        for categoria, itens in OPTIONS_DATA.items():
            yield Button(categoria, id=categoria, classes="column")

        yield Footer()


class AppTeste(App):
    CSS_PATH = "style.tcss"

    BINDINGS = [
        ("q", "quit", "Sair"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="conteiner"):
            yield Static("Um", classes="column")
            yield Static("dois", classes="column")
            yield ListView(ListItem(Label("um")), ListItem(Label("dois")))
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pop":
            self.app.pop_screen()
            return

        categoria = event.button.id
        if categoria is None:
            return
        itens = OPTIONS_DATA[categoria]


if __name__ == "__main__":
    app = AppTeste()
    app.run()
