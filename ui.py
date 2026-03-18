from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
import sys
import threading
import queue

class ChatUI:
    def __init__(self, role, peer_mac, safety_number):
        self.console = Console()
        self.role = role
        self.peer_mac = peer_mac
        self.safety_number = safety_number
        self.messages = []
        self.input_queue = queue.Queue()
        self._stop_event = threading.Event()

    def add_message(self, sender, text):
        self.messages.append((sender, text))

    def make_layout(self):
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        
        # Header
        header_text = Text(f"🔒 Offline Encrypted Chat | Role: {self.role} | Peer: {self.peer_mac}", style="bold cyan")
        layout["header"].update(Panel(header_text, border_style="blue"))
        
        # Body (Messages)
        msg_table = Table(show_header=False, box=None, expand=True)
        msg_table.add_column("Sender", style="bold green", width=12)
        msg_table.add_column("Message")
        
        # Display last 15 messages
        for sender, text in self.messages[-15:]:
            msg_table.add_row(sender, text)
            
        layout["body"].update(Panel(msg_table, title="Conversation", border_style="white"))
        
        # Footer (Safety Number)
        footer_text = Text(f"Safety Number (Verify verbally!): {self.safety_number}", style="bold yellow")
        layout["footer"].update(Panel(footer_text, border_style="yellow"))
        
        return layout

    def start(self, send_callback, receive_callback):
        """
        Starts the UI loop.
        - send_callback: function(text) to send a message.
        - receive_callback: function() that returns new messages.
        """
        # Thread for receiving messages
        def recv_thread():
            while not self._stop_event.is_set():
                try:
                    msg = receive_callback()
                    if msg:
                        self.add_message("Peer", msg)
                    else:
                        self.add_message("System", "Peer disconnected.")
                        self._stop_event.set()
                        break
                except Exception as e:
                    self.add_message("System", f"Error: {e}")
                    self._stop_event.set()
                    break

        threading.Thread(target=recv_thread, daemon=True).start()

        # UI refresh loop
        with Live(self.make_layout(), refresh_per_second=4, console=self.console) as live:
            while not self._stop_event.is_set():
                live.update(self.make_layout())
                
                # Check for user input (blocking in console.input)
                # Note: rich.Live and console.input can sometimes clash, 
                # but for simplicity we'll use a direct console.input here.
                # In a more complex app, we'd use 'prompt' or a custom input handler.
                try:
                    # We have to stop Live while taking input to avoid artifacts
                    live.stop()
                    text = self.console.input("[bold green]You: [/]")
                    live.start()
                    
                    if text.lower() in ["/quit", "/exit"]:
                        self._stop_event.set()
                        break
                    
                    if text:
                        self.add_message("You", text)
                        send_callback(text)
                except KeyboardInterrupt:
                    self._stop_event.set()
                    break
                except EOFError:
                    self._stop_event.set()
                    break

        self.console.print("[bold red]Conversation ended.[/]")

if __name__ == "__main__":
    # Test UI mock
    ui = ChatUI("Server", "AA:BB:CC:DD:EE:FF", "apple-beach-cloud-dance-eagle-flame")
    ui.start(lambda x: print(f"Sent: {x}"), lambda: None)
