import asyncio
import fcntl
import os
import pty
import re
import shlex
import struct
import termios

import pyte
from rich.text import Text
from textual import events
from textual.message import Message
from textual.widget import Widget


class PyteDisplay:
    def __init__(self, lines):
        self.lines = lines

    def __rich_console__(self, console, options):
        yield from self.lines


class TerminalPTY:
    """Dono do PTY de verdade: spawna um bash persistente e faz a ponte
    entre ele e as filas assíncronas usadas pelo widget Terminal.
    Adaptado do exemplo oficial do pyte (não herda de App)."""

    def __init__(self, ncol: int, nrow: int) -> None:
        self.ncol = ncol
        self.nrow = nrow
        self.data_or_disconnect: str | None = None
        self.fd = self._open_terminal()
        self.p_out = os.fdopen(self.fd, "w+b", 0)
        self.recv_queue: asyncio.Queue = asyncio.Queue()
        self.send_queue: asyncio.Queue = asyncio.Queue()
        self.event = asyncio.Event()

    def _open_terminal(self) -> int:
        pid, fd = pty.fork()
        if pid == 0:
            argv = shlex.split("bash")
            lang = os.environ.get("LANG") or "C.UTF-8"
            env = dict(
                os.environ,
                TERM="xterm-256color",
                LANG=lang,
                COLUMNS=str(self.ncol),
                LINES=str(self.nrow),
            )
            os.execvpe(argv[0], argv, env)
        return fd

    def start(self) -> None:
        asyncio.create_task(self._run())
        asyncio.create_task(self._send_data())

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()

        def on_output() -> None:
            try:
                self.data_or_disconnect = self.p_out.read(65536).decode(
                    errors="replace"
                )
                self.event.set()
            except Exception:
                loop.remove_reader(self.p_out)
                self.data_or_disconnect = None
                self.event.set()

        loop.add_reader(self.p_out, on_output)
        await self.send_queue.put(["setup", {}])
        while True:
            msg = await self.recv_queue.get()
            if msg[0] == "stdin":
                self.p_out.write(msg[1].encode())
            elif msg[0] == "set_size":
                winsize = struct.pack("HH", msg[1], msg[2])
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    async def _send_data(self) -> None:
        while True:
            await self.event.wait()
            self.event.clear()
            if self.data_or_disconnect is None:
                await self.send_queue.put(["disconnect", 1])
            else:
                await self.send_queue.put(["stdout", self.data_or_disconnect])


class ScriptFinished(Message):
    """Postada quando um script rodado via run_script() termina.
    exit_code=None significa que o próprio bash caiu (não o script)."""

    def __init__(self, exit_code: int | None) -> None:
        self.exit_code = exit_code
        super().__init__()


class Terminal(Widget, can_focus=True):
    EXIT_MARKER = "@@LT_EXIT@@:"
    _EXIT_LINE_RE = re.compile(re.escape(EXIT_MARKER) + r"(\d+)\r?\n?")

    def __init__(self, ncol: int = 80, nrow: int = 24, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ctrl_keys = {
            "left": "\u001b[D",
            "right": "\u001b[C",
            "up": "\u001b[A",
            "down": "\u001b[B",
            "enter": "\r",
            "backspace": "\u007f",
        }
        self.ncol = ncol
        self.nrow = nrow
        self._display = PyteDisplay([Text()])
        self._screen = pyte.Screen(ncol, nrow)
        self.stream = pyte.Stream(self._screen)
        self.pty: TerminalPTY | None = None
        self._exit_scan_buffer = ""
        self._awaiting_exit_code = False

    def on_mount(self) -> None:
        self.pty = TerminalPTY(self.ncol, self.nrow)
        self.pty.start()
        self.run_worker(self._recv(), exclusive=True)
        self.focus()

    def render(self):
        return self._display

    async def on_key(self, event: events.Key) -> None:
        if self.pty is None:
            return
        char = self.ctrl_keys.get(event.key) or event.character
        if char:
            await self.pty.recv_queue.put(["stdin", char])

    def run_script(self, path: str) -> None:
        """Injeta 'bash <script>' no shell persistente, com um marcador
        de saída logo depois pra detectar o fim e capturar o exit code."""
        if self.pty is None:
            return
        self._awaiting_exit_code = True
        self._exit_scan_buffer = ""
        command = f"bash {shlex.quote(path)}; echo {self.EXIT_MARKER}$?\n"
        asyncio.create_task(self.pty.recv_queue.put(["stdin", command]))

    async def _recv(self) -> None:
        while True:
            message = await self.pty.send_queue.get()
            cmd = message[0]
            if cmd == "setup":
                await self.pty.recv_queue.put(
                    ["set_size", self.nrow, self.ncol, 567, 573]
                )
            elif cmd == "stdout":
                self._handle_stdout(message[1])
            elif cmd == "disconnect":
                self.post_message(ScriptFinished(None))

    def _handle_stdout(self, chars: str) -> None:
        """Alimenta a tela com o que chegou do pty. Enquanto está
        esperando o marcador de exit code, segura no buffer qualquer
        trecho final que possa ser um marcador partido ao meio por
        causa da fragmentação de leitura do pty."""
        if not self._awaiting_exit_code:
            self.stream.feed(chars)
            self._render_screen()
            return

        self._exit_scan_buffer += chars
        match = self._EXIT_LINE_RE.search(self._exit_scan_buffer)

        if match:
            # marcador completo encontrado: remove ele do que vai pra
            # tela e extrai o exit code
            before = self._exit_scan_buffer[: match.start()]
            after = self._exit_scan_buffer[match.end() :]
            exit_code = int(match.group(1))

            self._awaiting_exit_code = False
            self._exit_scan_buffer = ""

            if before or after:
                self.stream.feed(before + after)
                self._render_screen()

            self.post_message(ScriptFinished(exit_code))
            return

        # ainda não achou o marcador completo — pode ser que o final do
        # buffer seja o começo de um marcador cortado ao meio. Segura só
        # essa parte ambígua e libera o resto pra tela.
        held = self._partial_marker_suffix(self._exit_scan_buffer)
        safe_len = len(self._exit_scan_buffer) - len(held)
        safe, self._exit_scan_buffer = self._exit_scan_buffer[:safe_len], held

        if safe:
            self.stream.feed(safe)
            self._render_screen()

    def _partial_marker_suffix(self, buffer: str) -> str:
        """Maior sufixo de `buffer` que é, ao mesmo tempo, um prefixo
        de EXIT_MARKER — ou seja, o pedaço final que ainda pode vir a
        se completar como o marcador na próxima leitura."""
        marker = self.EXIT_MARKER
        max_check = min(len(marker) - 1, len(buffer))
        for size in range(max_check, 0, -1):
            if buffer.endswith(marker[:size]):
                return buffer[-size:]
        return ""

    def _render_screen(self) -> None:
        lines = []
        for i, line in enumerate(self._screen.display):
            text = Text.from_ansi(line)
            x = self._screen.cursor.x
            if i == self._screen.cursor.y and x < len(text):
                cursor = text[x]
                cursor.stylize("reverse")
                new_text = text[:x]
                new_text.append(cursor)
                new_text.append(text[x + 1 :])
                text = new_text
            lines.append(text)
        self._display = PyteDisplay(lines)
        self.refresh()
