from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Collapsible,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

OPTIONS_DATA: dict[str, list[str]] = {
    "Informatica": ["teclado", "mouse", "monitor", "notebook"],
    "Esporte e lazer": ["camisa_esportiva", "chuteira"],
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


class TUIInstaller(App):
    """Protótipo de tela: seleção de pacotes/apps em categorias."""

    CSS_PATH = "style.tcss"

    BINDINGS = [
        ("q", "quit", "Sair"),
        Binding("up", "cursor_up", "Cursor up", show=False),
        Binding("down", "cursor_down", "Cursor down", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="body"):
            # ---- Container 1: categorias colapsáveis (1/3 da tela) ----
            with VerticalScroll(id="left-panel"):
                for indice, (categoria, itens) in enumerate(
                    OPTIONS_DATA.items()
                ):
                    with Collapsible(title=categoria, collapsed=True):
                        list_items = []
                        for item in itens:
                            list_item = ListItem(
                                Label(item), id=f"item-{item}"
                            )
                            # guarda o nome original da opção como metadado,
                            # evitando depender de atributos internos do Label
                            list_item.opcao_nome = item
                            list_items.append(list_item)
                        yield ListView(*list_items, id=f"list-{indice}")

            # ---- Containers 2 e 3: descrição + logs (2/3 da tela) ----
            with Vertical(id="right-panel"):
                yield Static(
                    "Selecione uma opção à esquerda para ver a descrição aqui.",
                    id="description-box",
                )
                yield RichLog(
                    id="log-box", highlight=True, markup=True, wrap=True
                )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#left-panel").border_title = "Categorias"
        self.query_one("#description-box").border_title = "Descrição"
        self.query_one("#log-box", RichLog).border_title = "Logs de instalação"
        self.query_one("#log-box", RichLog).write(
            "[dim]Aguardando seleção de opções...[/dim]"
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Disparado ao selecionar uma opção dentro de qualquer ListView."""
        item = event.item
        opcao = getattr(item, "opcao_nome", None)
        if opcao is None:
            # fallback caso o metadado não exista por algum motivo
            label = item.query_one(Label)
            opcao = str(label.content)

        # Requisito 9: imprime na tela de logs
        log = self.query_one("#log-box", RichLog)
        log.write(f"opção '{opcao}' selecionada")

        # Requisito 6/10: mostra descrição genérica
        descricao = DESCRIPTIONS.get(opcao, DEFAULT_DESCRIPTION)
        desc_box = self.query_one("#description-box", Static)
        desc_box.update(f"[b]{opcao}[/b]\n\n{descricao}")


if __name__ == "__main__":
    TUIInstaller().run()
