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
import time
import os

class ChatUI:
    def __init__(self, role, peer_mac, safety_number, trust_status="new"):
        self.role = role
        self.peer_mac = peer_mac
        self.safety_number = safety_number
        self.trust_status = trust_status 
        self.peer_typing = False
        self.is_online = True
        self.is_recording = False
        self.explorer_visible = False
        self.explorer_path = None
        self.explorer_selection = 0
        self.explorer_items = []
        self.voice_pending_path = None
        self.messages = []
        self.recv_progress_id = None
        self.total_received = 0
        self.requested_resume_offset = 0
        self.last_update_time = 0
        self._stop_event = threading.Event()
        self.app = None
        self.send_callback = None
        self.resume_callback = None
        self.trust_callback = None
        self.typing_callback = None
        self._current_ansi = ANSI("")
        self._line_count = 0
        
        # Use get_cursor_position to force the window to always be at the bottom
        self.history_control = FormattedTextControl(
            lambda: self._current_ansi,
            get_cursor_position=lambda: Point(x=0, y=max(0, self._line_count - 1))
        )

    def add_message(self, sender, text, is_seen=False, msg_id=None):
        mid = msg_id or str(int(time.time() * 1000000))
        self.messages.append({
            "id": mid,
            "sender": sender,
            "text": text,
            "seen": is_seen
        })
        self._update_history()
        if self.app: self.app.invalidate()
        return mid

    def update_message(self, msg_id, text):
        for msg in self.messages:
            if msg["id"] == msg_id:
                msg["text"] = text
                self._update_history()
                if self.app: self.app.invalidate()
                return True
        return False

    def _mark_message_seen(self, msg_id):
        updated = False
        for msg in self.messages:
            if msg["id"] == msg_id:
                msg["seen"] = True
                updated = True
        if updated:
            self._update_history()
            if self.app: self.app.invalidate()

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
        if self.is_recording:
             header_text += " [bold blink red]● REC[/]"
        
        if self.trust_status == "untrusted":
             header_text += " [bold blink red](!) WARNING: IDENTITY CHANGED"
        
        console.print(Text.from_markup(header_text, style="bold cyan dim"))
        console.print(" " * width) # Spacer
        
        # Messages or Explorer?
        if self.explorer_visible:
            console.print(Align.center(Panel(Text(f"📂 Select File: {self.explorer_path}", style="bold yellow"), border_style="yellow")))
            for i, (name, is_dir) in enumerate(self.explorer_items):
                prefix = "> " if i == self.explorer_selection else "  "
                icon = "📁" if is_dir else "📄"
                style = "bold cyan" if i == self.explorer_selection else ("dim" if not is_dir else "")
                console.print(Text(f"{prefix}{icon} {name}", style=style))
        else:
            # Messages rendered as bubbles
            for msg in self.messages:
                sender = msg["sender"]
                text = msg["text"]
                is_seen = msg.get("seen", False)
                
                if sender == "You":
                    max_bw = min(width - 10, int(width * 0.7))
                    seen_indicator = " ✓✓" if is_seen else ""
                    # Calculate if we need to wrap
                    projected_width = len(text + seen_indicator) + 4
                    p_width = max_bw if projected_width > max_bw else None
                    p = Panel(Text(text + seen_indicator), border_style="blue", padding=(0, 1), title="[bold]You", title_align="right", width=p_width, expand=False)
                    console.print(Align.right(p, width=width))
                elif sender == "Peer":
                    max_bw = min(width - 10, int(width * 0.7))
                    projected_width = len(text) + 4
                    p_width = max_bw if projected_width > max_bw else None
                    p = Panel(Text(text), border_style="green", padding=(0, 1), title="[bold]Peer", title_align="left", width=p_width, expand=False)
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

    def start(self, send_callback, receive_callback, trust_callback=None, typing_callback=None, file_send_callback=None, ack_callback=None, voice_record_callback=None, resume_callback=None):
        self.send_callback = send_callback
        self.resume_callback = resume_callback
        self.trust_callback = trust_callback
        self.typing_callback = typing_callback
        self.file_send_callback = file_send_callback
        self.ack_callback = ack_callback
        self.voice_record_callback = voice_record_callback
        
        if self.trust_status == "new":
            self.add_message("System", "This is a new peer. Type /trust to mark as trusted.")
        elif self.trust_status == "untrusted":
             self.add_message("System", "(!) WARNING: Peer's identity has changed! Someone might be intercepting your connection.")

        self._update_history() # Initial render

        def recv_thread():
            incoming_file = None
            file_meta = None
            save_path = None
            from pathlib import Path
            
            while not self._stop_event.is_set():
                try:
                    msg_type, content = receive_callback()
                    if msg_type == "text":
                        msg_id, text = content
                        self.peer_typing = False
                        self.add_message("Peer", text)
                        # Send Read receipt
                        if msg_id and self.ack_callback:
                            self.ack_callback(msg_id)
                    elif msg_type == "typing":
                        self.peer_typing = content
                        self._update_history()
                        if self.app: self.app.invalidate()
                    elif msg_type == "file_start":
                        file_meta = content
                        save_dir = Path.home() / "Downloads" / "ChatApp"
                        save_dir.mkdir(parents=True, exist_ok=True)
                        save_path = save_dir / file_meta["name"]
                        
                        # Resumption check
                        offset = 0
                        mode = "wb"
                        if save_path.exists():
                            curr_size = save_path.stat().st_size
                            if curr_size < file_meta["size"]:
                                offset = curr_size
                                mode = "ab" # Append
                                if self.resume_callback: self.resume_callback(offset)
                        
                        incoming_file = open(save_path, mode)
                        self.total_received = offset
                        from transport import format_size
                        fsize_str = format_size(file_meta['size'])
                        self.recv_progress_id = self.add_message("System", f"📥 Receiving: {file_meta['name']} ({format_size(offset)} / {fsize_str})")
                    elif msg_type == "file_chunk" and incoming_file:
                        incoming_file.write(content)
                        self.total_received += len(content)
                        if file_meta['size'] > 0:
                            pct = int((self.total_received / file_meta['size']) * 100)
                            # Throttle: Update only if 5% passed AND it's been 0.25s
                            now = time.time()
                            if (pct % 5 == 0) and (now - self.last_update_time > 0.25):
                                self.last_update_time = now
                                from transport import format_size
                                cur_str = format_size(self.total_received)
                                tot_str = format_size(file_meta['size'])
                                self.update_message(self.recv_progress_id, f"📥 Receiving: {file_meta['name']} ({cur_str} / {tot_str}, {pct}%)")
                    elif msg_type == "file_end" and incoming_file:
                        incoming_file.close()
                        from transport import format_size
                        tot_str = format_size(file_meta['size'])
                        self.update_message(self.recv_progress_id, f"💾 Verifying: {file_meta['name']}...")
                        
                        # Verify SHA-256
                        def verify_task(path, expected_hash, progress_id, name):
                            import hashlib
                            sha = hashlib.sha256()
                            with open(path, "rb") as f:
                                while chunk := f.read(65536): sha.update(chunk)
                            
                            if sha.hexdigest() == expected_hash:
                                self.update_message(progress_id, f"✅ Verified: {name} ({tot_str}, Secure)")
                            else:
                                if path.exists(): path.unlink()
                                self.update_message(progress_id, f"❌ CORRUPTED: {name} (Deleted for protection)")
                            
                            # Existing voice logic
                            if name.startswith("voice_") and name.endswith(".wav") and sha.hexdigest() == expected_hash:
                                self.voice_pending_path = path
                                self.add_message("System", f"🎙️ Voice clip ready! [Enter] Play | [Esc] Dismiss")
                                if self.app: self.app.invalidate()

                        threading.Thread(target=verify_task, args=(save_path, file_meta["sha256"], self.recv_progress_id, file_meta["name"]), daemon=True).start()
                        incoming_file = None
                    elif msg_type == "read_ack":
                        self._mark_message_seen(content)
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
        from prompt_toolkit.completion import PathCompleter
        input_field = TextArea(
            height=3,
            prompt="You: ",
            multiline=False,
            completer=PathCompleter(),
            complete_while_typing=True,
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
            
            # Simple Enter-to-Stop for Voice
            if self.is_recording:
                 self.is_recording = False
                 if self.voice_record_callback:
                     self.voice_record_callback(False)
                 self._update_history()
                 if self.app: self.app.invalidate()
                 input_field.text = ""
                 return True

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
                
                if text.lower() == "/voice":
                    self.is_recording = True
                    if self.voice_record_callback:
                        self.voice_record_callback(True)
                    self._update_history()
                    if self.app: self.app.invalidate()
                    input_field.text = ""
                    return True

                if text.lower() == "/send":
                    # Trigger File Explorer
                    self._open_file_explorer()
                    input_field.text = ""
                    return True

                elif text.lower() == "/play":
                    # Removed in favor of interactive prompt
                    input_field.text = ""
                    return True
                
                elif text.lower().startswith("/send "):
                    path = text[6:].strip()
                    self._start_file_send(path)
                    input_field.text = ""
                    return True

                if text.lower() in ["/help", "/?"]:
                    self.add_message("System", "Available Commands:")
                    self.add_message("System", "  /send <path> - Send a file securely")
                    self.add_message("System", "  /voice - Toggle recording (Walkie-Talkie)")
                    self.add_message("System", "  /trust - Mark current peer as trusted")
                    self.add_message("System", "  /quit - Exit the application")
                    input_field.text = ""
                    self._last_typing_state = False
                    if self.typing_callback: self.typing_callback(False)
                    return True

                msg_id = self.send_callback(text)
                self.add_message("You", text, msg_id=msg_id)
                input_field.text = ""
                self._last_typing_state = False # Reset typing state
                if self.typing_callback:
                    self.typing_callback(False)
            return True

        # Layout
        # Use a Window around the FormattedTextControl for scrolling
        self.history_window = Window(
            content=self.history_control,
            always_hide_cursor=True,
            wrap_lines=True,
        )

        if self.voice_pending_path:
            legend_text = ANSI(" [dim]PROMPT: [Enter] Play Voice | [Esc] Dismiss [/]")
        else:
            legend_text = ANSI(" [dim]Legend: [Enter] Send/Stop | /send (Explorer) | /voice | /help[/]")
        
        root_container = HSplit([
            # Empty Window here acts as a spacer that pushes history to the bottom
            Window(), 
            self.history_window,
            Window(height=1, char="─", style="dim"),
            input_field,
            Window(height=1, content=FormattedTextControl(lambda: legend_text), style="dim cyan"),
        ])

        # Key Bindings
        kb = KeyBindings()
        @kb.add("c-c")
        def _(event):
            self._stop_event.set()
            event.app.exit()

        @kb.add("up")
        def _(event):
            if self.explorer_visible:
                self._handle_explorer_key("up")
            else:
                event.current_buffer.history_backward()

        @kb.add("down")
        def _(event):
            if self.explorer_visible:
                self._handle_explorer_key("down")
            else:
                event.current_buffer.history_forward()

        @kb.add("enter")
        def _(event):
            if self.voice_pending_path:
                path = self.voice_pending_path
                self.voice_pending_path = None
                self._play_voice_clip(path)
            elif self.explorer_visible:
                self._handle_explorer_key("enter")
            else:
                accept_text(event.current_buffer)

        @kb.add("escape")
        def _(event):
            if self.voice_pending_path:
                path = self.voice_pending_path
                self.voice_pending_path = None
                try: 
                    import os
                    if os.path.exists(path): os.remove(path)
                except: pass
                self.add_message("System", "🗑️ Voice clip dismissed and deleted.")
                self._update_history()
                if self.app: self.app.invalidate()
            elif self.explorer_visible:
                self.explorer_visible = False
                self._update_history()
                if self.app: self.app.invalidate()

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
            self._stop_event.set()

    def _play_voice_clip(self, path):
        import os, subprocess, platform, threading, time
        
        def play_task(target_path):
            try:
                self.add_message("System", f"🔊 Playing voice clip...")
                if os.environ.get("TERMUX_VERSION"):
                    subprocess.run(["termux-media-player", "play", str(target_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif platform.system() == "Linux":
                    import shutil
                    if shutil.which("ffplay"):
                        subprocess.run(["ffplay", "-nodisp", "-autoexit", str(target_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.run(["aplay", "-q", str(target_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Auto-delete after playing
                if os.path.exists(target_path): os.remove(target_path)
                self.add_message("System", "🗑️ Voice clip played and deleted for privacy.")
                if self.app: self.app.invalidate()
            except Exception as e:
                self.add_message("System", f"⚠️ Playback failed: {e}")

        threading.Thread(target=play_task, args=(path,), daemon=True).start()

    def _open_file_explorer(self, path=None):
        import os
        from pathlib import Path
        self.explorer_path = Path(path or os.getcwd()).resolve()
        self.explorer_visible = True
        self.explorer_selection = 0
        self._update_explorer_items()
        self._update_history()
        if self.app: self.app.invalidate()

    def _update_explorer_items(self):
        import os
        try:
            items = []
            # Add ".." to go up
            items.append(("..", True)) 
            for entry in os.scandir(self.explorer_path):
                items.append((entry.name, entry.is_dir()))
            # Sort: Directories first, then files
            self.explorer_items = sorted(items, key=lambda x: (not x[1], x[0].lower()))
        except Exception as e:
            self.add_message("System", f"Explorer Error: {e}")
            self.explorer_visible = False

    def _handle_explorer_key(self, key):
        if key == "up":
            self.explorer_selection = max(0, self.explorer_selection - 1)
        elif key == "down":
            self.explorer_selection = min(len(self.explorer_items) - 1, self.explorer_selection + 1)
        elif key == "enter":
            name, is_dir = self.explorer_items[self.explorer_selection]
            if is_dir:
                if name == "..":
                    self._open_file_explorer(self.explorer_path.parent)
                else:
                    self._open_file_explorer(self.explorer_path / name)
                return
            else:
                # File selected!
                target_path = self.explorer_path / name
                self.explorer_visible = False
                self._start_file_send(str(target_path))
        elif key == "escape":
            self.explorer_visible = False
        
        self._update_history()
        if self.app: self.app.invalidate()

    def _start_file_send(self, path):
        import os, threading
        if not os.path.exists(path):
            self.add_message("System", f"❌ File not found: {path}")
            return

        def send_task():
            try:
                filename = os.path.basename(path)
                filesize = os.path.getsize(path)
                self.add_message("System", f"📤 Sending file: {filename} ({filesize} bytes)...")
                
                if self.file_send_callback:
                    self.file_send_callback(path, filename, filesize)
                    self.add_message("System", f"✅ Sent: {filename}")
            except Exception as e:
                self.add_message("System", f"❌ Send failed: {e}")

        threading.Thread(target=send_task, daemon=True).start()

if __name__ == "__main__":
    ui = ChatUI("Server", "AA:BB:CC:DD:EE:FF", "apple-beach-cloud-dance-eagle-flame")
    ui.start(lambda x: print(f"Sent: {x}"), lambda: None)
