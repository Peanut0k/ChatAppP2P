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
from prompt_toolkit.data_structures import Point
import threading
import queue
import io

class ChatUI:
    def __init__(self, role, peer_mac, safety_number, trust_status="new"):
        self.role = role
        self.peer_mac = peer_mac
        self.safety_number = safety_number
        self.trust_status = trust_status 
        self.peer_typing = False
        self.is_online = True
        self.messages = []
        self._stop_event = threading.Event()
        self.app = None
        self.send_callback = None
        self.trust_callback = None
        self.typing_callback = None
        self._current_ansi = ANSI("")
        self._line_count = 0
        
        # Use get_cursor_position to force the window to always be at the bottom
        self.history_control = FormattedTextControl(
            lambda: self._current_ansi,
            get_cursor_position=lambda: Point(x=0, y=self._line_count)
        )

    def add_message(self, sender, text):
        self.messages.append((sender, text))
        self._update_history()
        if self.app:
            self.app.invalidate()

    def _update_history(self):
        """Builds the full chat history in Rich and converts to ANSI."""
        buf = io.StringIO()
        # Use terminal width (fallback to 80)
        from shutil import get_terminal_size
        width = get_terminal_size((80, 24)).columns
        
        console = Console(file=buf, force_terminal=True, width=width, color_system="truecolor")
        
        # Header - minimal
        trust_icon = "🟢" if self.trust_status == "trusted" else ("🟡" if self.trust_status == "new" else "🔴")
        signal_icon = "📶" if self.is_online else "⚠️ [bold red]DISCONNECTED[/]"
        typing_text = " [italic cyan]... is typing[/]" if self.peer_typing else ""
        header_text = f"🔒 {self.role} • {self.peer_mac} • {trust_icon} {self.trust_status.upper()} • {signal_icon}{typing_text}"
        
        if self.trust_status == "untrusted":
             header_text += " [bold blink red](!) WARNING: IDENTITY CHANGED"
        
        console.print(Text.from_markup(header_text, style="bold cyan dim"))
        console.print(" " * width) # Spacer
        
        # Messages rendered as bubbles
        for sender, text in self.messages:
            if sender == "You":
                # Max width for bubbles is 2/3 of terminal
                bubble_width = min(width - 10, int(width * 0.7))
                p = Panel(Text(text), border_style="blue", padding=(0, 1), title="[bold]You", title_align="right", width=bubble_width)
                console.print(Align.right(p, width=width))
            elif sender == "Peer":
                bubble_width = min(width - 10, int(width * 0.7))
                p = Panel(Text(text), border_style="green", padding=(0, 1), title="[bold]Peer", title_align="left", width=bubble_width)
                console.print(Align.left(p, width=width))
            else:
                console.print(Align.center(Text(text, style="italic dim yellow")))
            console.print(" ") # Space between bubbles

        # Safety number at bottom of history
        console.print("-" * width, style="dim")
        console.print(Text(f"Safety: {self.safety_number}", style="italic dim yellow"))
        
        raw_text = buf.getvalue()
        self._current_ansi = ANSI(raw_text)
        self._line_count = raw_text.count('\n') + 1

    def start(self, send_callback, receive_callback, trust_callback=None, typing_callback=None):
        self.send_callback = send_callback
        self.trust_callback = trust_callback
        self.typing_callback = typing_callback
        
        if self.trust_status == "new":
            self.add_message("System", "This is a new peer. Type /trust to mark as trusted.")
        elif self.trust_status == "untrusted":
             self.add_message("System", "(!) WARNING: Peer's identity has changed! Someone might be intercepting your connection.")

        self._update_history() # Initial render

        def recv_thread():
            while not self._stop_event.is_set():
                try:
                    msg_type, content = receive_callback()
                    if msg_type == "text":
                        self.peer_typing = False
                        self.add_message("Peer", content)
                    elif msg_type == "typing":
                        self.peer_typing = content
                        self._update_history()
                        if self.app: self.app.invalidate()
                    elif msg_type is None:
                        self.is_online = False
                        self.add_message("System", "Peer disconnected. Waiting for auto-reconnect...")
                        self._update_history()
                        if self.app: self.app.invalidate()
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

        # Typing notification logic
        self._last_typing_state = False
        def on_text_changed(_):
            is_typing = len(input_field.text.strip()) > 0
            if is_typing != self._last_typing_state:
                self._last_typing_state = is_typing
                if self.typing_callback:
                    self.typing_callback(is_typing)

        input_field.buffer.on_text_changed += on_text_changed

        def accept_text(buffer):
            text = input_field.text.strip()
            if text:
                if text.lower() in ["/quit", "/exit"]:
                    self._stop_event.set()
                    self.app.exit()
                    return True
                
                if text.lower() == "/trust":
                    if self.trust_callback:
                        self.trust_callback()
                        input_field.text = ""
                        return True

                self.add_message("You", text)
                self.send_callback(text)
                input_field.text = ""
                self._last_typing_state = False # Reset typing state
                if self.typing_callback:
                    self.typing_callback(False)
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
            # Empty Window here acts as a spacer that pushes history to the bottom
            Window(), 
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
