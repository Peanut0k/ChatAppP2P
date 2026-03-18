from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import HSplit, Window, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import ANSI
import threading
import queue
import io

class ChatUI:
    def __init__(self, role, peer_mac, safety_number):
        self.role = role
        self.peer_mac = peer_mac
        self.safety_number = safety_number
        self.messages = []
        self._stop_event = threading.Event()
        self.app = None
        self.send_callback = None
        self._current_ansi = ANSI("")
        
        # We'll use a FormattedTextControl to show the ANSI from Rich
        self.history_control = FormattedTextControl(lambda: self._current_ansi)

    def add_message(self, sender, text):
        self.messages.append((sender, text))
        self._update_history()
        if self.app:
            self.app.invalidate()
        # Scroll to bottom after adding
        if hasattr(self, 'history_window'):
            self.history_window.vertical_scroll = 999999

    def _update_history(self):
        """Builds the full chat history in Rich and converts to ANSI."""
        buf = io.StringIO()
        # Use a fixed width
        console = Console(file=buf, force_terminal=True, width=78, color_system="truecolor")
        
        # Header - minimal
        console.print(Text(f"🔒 {self.role} • {self.peer_mac}", style="bold cyan dim"))
        console.print(" " * 78) # Spacer
        
        # Messages rendered as bubbles
        for sender, text in self.messages:
            if sender == "You":
                p = Panel(Text(text), border_style="blue", padding=(0, 1), title="[bold]You", title_align="right")
                console.print(Align.right(p, width=78))
            elif sender == "Peer":
                p = Panel(Text(text), border_style="green", padding=(0, 1), title="[bold]Peer", title_align="left")
                console.print(Align.left(p, width=78))
            else:
                console.print(Align.center(Text(text, style="italic dim yellow")))
            console.print(" ") # Space between bubbles

        # Safety number at bottom of history
        console.print("-" * 78, style="dim")
        console.print(Text(f"Safety: {self.safety_number}", style="italic dim yellow"))
        
        self._current_ansi = ANSI(buf.getvalue())

    def start(self, send_callback, receive_callback):
        self.send_callback = send_callback
        self._update_history() # Initial render

        def recv_thread():
            while not self._stop_event.is_set():
                try:
                    msg = receive_callback()
                    if msg:
                        self.add_message("Peer", msg)
                    else:
                        self.add_message("System", "Peer disconnected.")
                        self._stop_event.set()
                        if self.app: self.app.exit()
                        break
                except Exception as e:
                    self.add_message("System", f"Error: {e}")
                    self._stop_event.set()
                    if self.app: self.app.exit()
                    break

        threading.Thread(target=recv_thread, daemon=True).start()

        # Input Area
        input_field = TextArea(
            height=3,
            prompt="You: ",
            multiline=False,
            style="class:input-field",
        )

        def accept_text(buffer):
            text = input_field.text.strip()
            if text:
                if text.lower() in ["/quit", "/exit"]:
                    self._stop_event.set()
                    self.app.exit()
                    return True
                
                self.add_message("You", text)
                self.send_callback(text)
                input_field.text = ""
            return True

        input_field.accept_handler = accept_text

        # Layout
        # Use a Window around the FormattedTextControl for scrolling
        self.history_window = Window(
            content=self.history_control,
            always_hide_cursor=True,
            wrap_lines=True,
        )

        root_container = HSplit([
            self.history_window,
            Window(height=1, char="─", style="dim"),
            input_field,
        ])

        # Key Bindings
        kb = KeyBindings()
        @kb.add("c-c")
        def _(event):
            self._stop_event.set()
            event.app.exit()

        # Application
        self.app = Application(
            layout=Layout(root_container, focused_element=input_field),
            key_bindings=kb,
            full_screen=True,
            mouse_support=True,
        )

        try:
            self.app.run()
        finally:
            print("Conversation ended.")

if __name__ == "__main__":
    ui = ChatUI("Server", "AA:BB:CC:DD:EE:FF", "apple-beach-cloud-dance-eagle-flame")
    ui.start(lambda x: print(f"Sent: {x}"), lambda: None)
