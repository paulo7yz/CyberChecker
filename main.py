#!/usr/bin/env python3
"""
CyberChecker Main Application

This is the main entry point for the CyberChecker application.
In headless environments like Replit, it will automatically run in CLI mode.
In environments with a display, it will run the Kivy GUI.
"""

import os
import sys
import platform

# Check if we're running in a headless environment (like Replit)
is_replit = 'REPLIT_DB_URL' in os.environ
is_headless = is_replit or os.environ.get('DISPLAY') is None

if is_replit:
    print("Running in Replit environment - Headless mode enabled")
    
if is_headless:
    # In headless environments, use the CLI mode
    try:
        from cli_checker import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"Error importing CLI mode: {e}")
        print("Please run 'python cli_checker.py' directly for CLI mode.")
        sys.exit(1)
else:
    # In environments with a display, use the Kivy GUI
    try:
        import kivy
        from kivy.app import App
        from kivy.core.window import Window
        from kivy.uix.screenmanager import ScreenManager, Screen
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.spinner import Spinner
        from kivy.uix.textinput import TextInput
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup
        from kivy.uix.progressbar import ProgressBar
        from kivy.clock import Clock
        from kivy.graphics import Color, Rectangle
        
        from utils.config_manager import ConfigManager
        from utils.http_client import HttpClient
        from utils.ui_components import ModernLabel, ModernButton, ModernSpinner, GradientButton
        
        # Format time function (seconds to HH:MM:SS)
        def format_time(seconds):
            """Format seconds to HH:MM:SS"""
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        
        def ensure_directory(directory):
            """Ensure a directory exists"""
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        class MainScreen(Screen):
            """Main application screen"""
            def __init__(self, **kwargs):
                super(MainScreen, self).__init__(**kwargs)
                Window.clearcolor = (0.1, 0.1, 0.1, 1)  # Dark background
                
                # Set up the main layout
                self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
                with self.layout.canvas.before:
                    Color(0.15, 0.15, 0.15, 1)  # Slightly lighter than window background
                    self.rect = Rectangle(pos=self.layout.pos, size=self.layout.size)
                self.layout.bind(pos=self._update_rect, size=self._update_rect)
                
                # Status variables
                self.is_checking = False
                self.worker_threads = []
                self.combo_data = []
                self.proxies = []
                self.stats = {'checked': 0, 'hits': 0, 'start_time': 0}
                
                # Configuration and clients
                self.config_manager = ConfigManager()
                self.http_client = HttpClient()
                
                # Header section
                header = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=10)
                title = ModernLabel(text="CyberChecker", font_size=24, bold=True, 
                                    color=(0.6, 0.8, 1, 1), size_hint=(0.3, 1))
                
                # Configuration selector
                config_label = ModernLabel(text="Config:", size_hint=(0.1, 1))
                self.config_spinner = ModernSpinner(
                    text="Select Config", 
                    values=self._get_config_files(),
                    size_hint=(0.3, 1),
                    background_color=(0.2, 0.2, 0.2, 1)
                )
                self.config_spinner.bind(text=self.on_config_selection)
                
                # Proxy type selector
                proxy_label = ModernLabel(text="Proxy:", size_hint=(0.1, 1))
                self.proxy_spinner = ModernSpinner(
                    text="None",
                    values=["None", "HTTP", "SOCKS4", "SOCKS5"],
                    size_hint=(0.2, 1),
                    background_color=(0.2, 0.2, 0.2, 1)
                )
                self.proxy_spinner.bind(text=self.on_proxy_selection)
                
                header.add_widget(title)
                header.add_widget(config_label)
                header.add_widget(self.config_spinner)
                header.add_widget(proxy_label)
                header.add_widget(self.proxy_spinner)
                
                # File selection buttons
                file_buttons = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=10)
                
                self.combo_button = GradientButton(
                    text="Load Combo",
                    size_hint=(0.5, 1),
                    gradient_colors=[(0.2, 0.5, 0.9, 1), (0.1, 0.3, 0.7, 1)]
                )
                self.combo_button.bind(on_release=self.load_combo)
                
                self.proxies_button = GradientButton(
                    text="Load Proxies",
                    size_hint=(0.5, 1),
                    gradient_colors=[(0.2, 0.5, 0.9, 1), (0.1, 0.3, 0.7, 1)]
                )
                self.proxies_button.bind(on_release=self.load_proxies)
                
                file_buttons.add_widget(self.combo_button)
                file_buttons.add_widget(self.proxies_button)
                
                # Logs display
                logs_container = BoxLayout(orientation='vertical', size_hint=(1, 0.6), spacing=5)
                logs_label = ModernLabel(text="Logs:", size_hint=(1, 0.05), halign='left')
                self.logs = TextInput(
                    readonly=True,
                    multiline=True,
                    background_color=(0.1, 0.1, 0.1, 1),
                    foreground_color=(0.7, 0.7, 0.7, 1),
                    size_hint=(1, 0.95)
                )
                logs_container.add_widget(logs_label)
                logs_container.add_widget(self.logs)
                
                # Results display
                results_container = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
                
                # Hits counter
                hits_box = BoxLayout(orientation='vertical', size_hint=(0.25, 1))
                hits_label = ModernLabel(text="Hits:", size_hint=(1, 0.3))
                self.hits_count = ModernLabel(text="0", size_hint=(1, 0.7), font_size=20)
                hits_box.add_widget(hits_label)
                hits_box.add_widget(self.hits_count)
                
                # Progress bar
                progress_box = BoxLayout(orientation='vertical', size_hint=(0.5, 1))
                progress_label = ModernLabel(text="Progress:", size_hint=(1, 0.3))
                self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, 0.7))
                progress_box.add_widget(progress_label)
                progress_box.add_widget(self.progress_bar)
                
                # CPM (Checks Per Minute)
                cpm_box = BoxLayout(orientation='vertical', size_hint=(0.25, 1))
                cpm_label = ModernLabel(text="CPM:", size_hint=(1, 0.3))
                self.cpm_count = ModernLabel(text="0", size_hint=(1, 0.7), font_size=20)
                cpm_box.add_widget(cpm_label)
                cpm_box.add_widget(self.cpm_count)
                
                results_container.add_widget(hits_box)
                results_container.add_widget(progress_box)
                results_container.add_widget(cpm_box)
                
                # Control buttons
                control_buttons = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=10)
                
                self.start_button = GradientButton(
                    text="Start",
                    size_hint=(0.5, 1),
                    gradient_colors=[(0.1, 0.6, 0.1, 1), (0.1, 0.4, 0.1, 1)]
                )
                self.start_button.bind(on_release=self.start_checking)
                
                self.stop_button = GradientButton(
                    text="Stop",
                    size_hint=(0.5, 1),
                    gradient_colors=[(0.6, 0.1, 0.1, 1), (0.4, 0.1, 0.1, 1)],
                    disabled=True
                )
                self.stop_button.bind(on_release=self.stop_checking)
                
                control_buttons.add_widget(self.start_button)
                control_buttons.add_widget(self.stop_button)
                
                # Advanced buttons
                advanced_buttons = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=10)
                
                self.config_editor_button = ModernButton(
                    text="Config Editor",
                    size_hint=(0.33, 1),
                    background_color=(0.3, 0.3, 0.3, 1)
                )
                self.config_editor_button.bind(on_release=self.show_config_editor)
                
                self.export_button = ModernButton(
                    text="Export Results",
                    size_hint=(0.33, 1),
                    background_color=(0.3, 0.3, 0.3, 1)
                )
                self.export_button.bind(on_release=self.export_results)
                
                self.clear_button = ModernButton(
                    text="Clear Logs",
                    size_hint=(0.33, 1),
                    background_color=(0.3, 0.3, 0.3, 1)
                )
                self.clear_button.bind(on_release=lambda x: setattr(self.logs, 'text', ""))
                
                advanced_buttons.add_widget(self.config_editor_button)
                advanced_buttons.add_widget(self.export_button)
                advanced_buttons.add_widget(self.clear_button)
                
                # Add all sections to the main layout
                self.layout.add_widget(header)
                self.layout.add_widget(file_buttons)
                self.layout.add_widget(logs_container)
                self.layout.add_widget(results_container)
                self.layout.add_widget(control_buttons)
                self.layout.add_widget(advanced_buttons)
                
                self.add_widget(self.layout)
                
                # Initialize the directory for configs and results
                ensure_directory('configs')
                ensure_directory('results')
                
                # Add initial log
                self.add_log("CyberChecker started. Select a config and load combo file to begin.")
            
            def _update_rect(self, instance, value):
                """Update the rectangle position and size"""
                self.rect.pos = instance.pos
                self.rect.size = instance.size
            
            def _get_config_files(self):
                """Get a list of available config files"""
                return self.config_manager.get_config_files() or ["No configs found"]
            
            def on_config_selection(self, spinner, text):
                """Handle config selection from spinner"""
                if text != "Select Config" and text != "No configs found":
                    self.add_log(f"Selected configuration: {text}")
            
            def on_proxy_selection(self, spinner, text):
                """Handle proxy type selection"""
                if text != "None":
                    if not self.proxies:
                        self.add_log("Please load proxies first.")
                    else:
                        self.add_log(f"Using {text} proxies.")
                else:
                    self.add_log("Proxies disabled.")
            
            def load_combo(self, instance):
                """Open file chooser to load combo file"""
                popup = Popup(
                    title="Select Combo File",
                    size_hint=(0.8, 0.8),
                    auto_dismiss=True
                )
                
                layout = BoxLayout(orientation='vertical')
                filechooser = FileChooserListView(
                    path=os.getcwd(),
                    filters=['*.txt']
                )
                
                buttons = BoxLayout(size_hint=(1, 0.1))
                cancel_button = ModernButton(text="Cancel")
                select_button = ModernButton(text="Select")
                
                cancel_button.bind(on_release=popup.dismiss)
                select_button.bind(on_release=lambda x: self._on_combo_selected(filechooser.selection, popup))
                
                buttons.add_widget(cancel_button)
                buttons.add_widget(select_button)
                
                layout.add_widget(filechooser)
                layout.add_widget(buttons)
                
                popup.content = layout
                popup.open()
            
            def _on_combo_selected(self, selection, popup):
                """Handle combo file selection"""
                if selection:
                    try:
                        with open(selection[0], 'r', encoding='utf-8', errors='ignore') as f:
                            lines = [line.strip() for line in f if line.strip() and ":" in line]
                        
                        self.combo_data = lines
                        self.add_log(f"Loaded {len(lines)} combos from {os.path.basename(selection[0])}")
                        popup.dismiss()
                    except Exception as e:
                        self.show_error(f"Error loading combo file: {str(e)}")
                else:
                    self.show_error("No file selected")
            
            def load_proxies(self, instance):
                """Open file chooser to load proxies file"""
                popup = Popup(
                    title="Select Proxies File",
                    size_hint=(0.8, 0.8),
                    auto_dismiss=True
                )
                
                layout = BoxLayout(orientation='vertical')
                filechooser = FileChooserListView(
                    path=os.getcwd(),
                    filters=['*.txt']
                )
                
                buttons = BoxLayout(size_hint=(1, 0.1))
                cancel_button = ModernButton(text="Cancel")
                select_button = ModernButton(text="Select")
                
                cancel_button.bind(on_release=popup.dismiss)
                select_button.bind(on_release=lambda x: self._on_proxies_selected(filechooser.selection, popup))
                
                buttons.add_widget(cancel_button)
                buttons.add_widget(select_button)
                
                layout.add_widget(filechooser)
                layout.add_widget(buttons)
                
                popup.content = layout
                popup.open()
            
            def _on_proxies_selected(self, selection, popup):
                """Handle proxies file selection"""
                if selection:
                    try:
                        with open(selection[0], 'r', encoding='utf-8', errors='ignore') as f:
                            lines = [line.strip() for line in f if line.strip()]
                        
                        self.proxies = lines
                        self.add_log(f"Loaded {len(lines)} proxies from {os.path.basename(selection[0])}")
                        
                        # Automatically set proxy type if it was 'None'
                        if self.proxy_spinner.text == "None":
                            self.proxy_spinner.text = "HTTP"
                        
                        popup.dismiss()
                    except Exception as e:
                        self.show_error(f"Error loading proxies file: {str(e)}")
                else:
                    self.show_error("No file selected")
            
            def start_checking(self, instance):
                """Start the checking process"""
                # Validate input
                if self.config_spinner.text in ["Select Config", "No configs found"]:
                    self.show_error("Please select a configuration first.")
                    return
                
                if not self.combo_data:
                    self.show_error("Please load a combo file first.")
                    return
                
                if self.proxy_spinner.text != "None" and not self.proxies:
                    self.show_error("Please load proxies or set proxy type to None.")
                    return
                
                # Load the configuration
                config = self.config_manager.load_config(self.config_spinner.text)
                if not config:
                    self.show_error(f"Failed to load configuration: {self.config_spinner.text}")
                    return
                
                # Reset statistics
                self.stats = {
                    'checked': 0,
                    'hits': 0,
                    'start_time': Clock.get_time(),
                    'total': len(self.combo_data),
                    'cpm': 0,
                    'last_checked': 0,
                    'last_cpm_update': Clock.get_time()
                }
                
                # Update UI
                self.start_button.disabled = True
                self.stop_button.disabled = False
                self.is_checking = True
                
                # Clear logs
                self.logs.text = ""
                self.add_log(f"Starting check with config: {self.config_spinner.text}")
                self.add_log(f"Total combos to check: {len(self.combo_data)}")
                
                # TODO: Implement the actual checking logic with threads
                # For now, we'll just simulate it with a Clock schedule
                Clock.schedule_interval(self.update_progress, 0.5)
                
                # In a real implementation, we would start worker threads here
                # self.worker_threads = []
                # for _ in range(10):  # 10 threads
                #     thread = threading.Thread(target=self.worker_thread, args=(queue, config, proxies, proxy_type))
                #     thread.daemon = True
                #     thread.start()
                #     self.worker_threads.append(thread)
            
            def stop_checking(self, instance):
                """Stop the checking process"""
                if self.is_checking:
                    self.is_checking = False
                    self.add_log("Stopping check...")
                    
                    # Cancel the clock schedule
                    Clock.unschedule(self.update_progress)
                    
                    # In a real implementation, we would join threads here
                    # def join_threads():
                    #     for thread in self.worker_threads:
                    #         thread.join(0.1)
                    #     self.worker_threads = []
                    #     self.add_log("All threads stopped.")
                    #     self.reset_ui()
                    
                    # TODO: Implementing joining of threads in a non-blocking way
                    # For now, just reset the UI
                    self.reset_ui()
            
            def reset_ui(self):
                """Reset the UI to initial state"""
                self.start_button.disabled = False
                self.stop_button.disabled = True
                self.add_log("Check stopped.")
            
            def worker_thread(self, queue, config, proxies, proxy_type, timeout, pause_event):
                """Worker thread for checking"""
                # Implementation would go here
                pass
            
            def check_account(self, username, password, config, http_client, proxy=None):
                """Check an account using the selected config"""
                # Implementation would go here
                pass
            
            def replace_variables(self, text, variables):
                """Replace variables in text with their values"""
                result = text
                for key, value in variables.items():
                    result = result.replace(f"{{{key}}}", value)
                return result
            
            def process_result(self, result, combo_line):
                """Process a result from a worker thread"""
                # Implementation would go here
                pass
            
            def update_progress(self, dt):
                """Update the progress bar"""
                if not self.is_checking:
                    return
                
                # Simulate checking progress (in a real app, this would be actual data)
                self.stats['checked'] += 1
                
                # Randomly add hits in the simulation
                import random
                if random.random() < 0.1:  # 10% chance of hit
                    self.stats['hits'] += 1
                
                # Update progress bar
                progress_value = (self.stats['checked'] / self.stats['total']) * 100
                self.progress_bar.value = progress_value
                
                # Update hits display
                self.hits_count.text = str(self.stats['hits'])
                
                # Update CPM
                current_time = Clock.get_time()
                if current_time - self.stats.get('last_cpm_update', 0) >= 1.0:
                    # Calculate checks in the last interval
                    checks_diff = self.stats['checked'] - self.stats.get('last_checked', 0)
                    self.stats['last_checked'] = self.stats['checked']
                    self.stats['last_cpm_update'] = current_time
                    
                    # Update CPM with some smoothing
                    new_cpm = checks_diff * 60  # Convert to per minute
                    if self.stats['cpm'] == 0:
                        self.stats['cpm'] = new_cpm
                    else:
                        # Smooth CPM changes
                        self.stats['cpm'] = int((self.stats['cpm'] * 0.6) + (new_cpm * 0.4))
                
                self.cpm_count.text = str(int(self.stats['cpm']))
                
                # Add an occasional log message in the simulation
                if random.random() < 0.2:  # 20% chance of log message
                    if random.random() < 0.3:  # 30% chance of hit message
                        combo = random.choice(self.combo_data)
                        self.add_log(f"Hit: {combo}")
                    else:
                        self.add_log(f"Checked {self.stats['checked']} of {self.stats['total']}")
                
                # End the checking if all combos were checked
                if self.stats['checked'] >= self.stats['total']:
                    self.is_checking = False
                    Clock.unschedule(self.update_progress)
                    self.add_log(f"Check completed. Found {self.stats['hits']} hits.")
                    self.reset_ui()
            
            def update_stats(self, dt):
                """Update statistics display"""
                # Implementation would go here
                pass
            
            def add_log(self, message):
                """Add a message to the logs panel"""
                from datetime import datetime
                timestamp = datetime.now().strftime('%H:%M:%S')
                log_line = f"[{timestamp}] {message}\n"
                
                # Append to the logs TextInput
                self.logs.text += log_line
                
                # Auto-scroll to the bottom
                self.logs.cursor = (0, len(self.logs.text))
            
            def show_error(self, message):
                """Show an error popup"""
                popup = Popup(
                    title="Error",
                    content=Label(text=message),
                    size_hint=(0.6, 0.3)
                )
                popup.open()
            
            def show_config_editor(self, instance):
                """Show the config editor popup"""
                popup = Popup(
                    title="Config Editor",
                    size_hint=(0.9, 0.9),
                    auto_dismiss=True
                )
                
                layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
                
                # Config selection
                config_row = BoxLayout(size_hint=(1, 0.05))
                config_row.add_widget(Label(text="Configuration:", size_hint=(0.3, 1)))
                
                config_spinner = Spinner(
                    text="Select Config",
                    values=self._get_config_files(),
                    size_hint=(0.5, 1)
                )
                
                new_button = ModernButton(text="New", size_hint=(0.2, 1))
                
                config_row.add_widget(config_spinner)
                config_row.add_widget(new_button)
                
                # Config editor
                editor = TextInput(
                    readonly=False,
                    multiline=True,
                    background_color=(0.05, 0.05, 0.05, 1),
                    foreground_color=(0.9, 0.9, 0.9, 1),
                    size_hint=(1, 0.85)
                )
                
                # Button row
                button_row = BoxLayout(size_hint=(1, 0.1))
                cancel_button = ModernButton(text="Cancel")
                load_button = ModernButton(text="Load")
                save_button = ModernButton(text="Save")
                
                cancel_button.bind(on_release=popup.dismiss)
                
                def on_load(instance):
                    if config_spinner.text not in ["Select Config", "No configs found"]:
                        try:
                            config_data = self.config_manager.get_config_text(config_spinner.text)
                            if config_data:
                                editor.text = config_data
                            else:
                                editor.text = "Failed to load configuration."
                        except Exception as e:
                            editor.text = f"Error loading configuration: {str(e)}"
                
                def on_save(instance):
                    if config_spinner.text not in ["Select Config", "No configs found"]:
                        try:
                            # Validate JSON first
                            import json
                            json.loads(editor.text)
                            
                            # Save if valid
                            self.config_manager.save_config(config_spinner.text, editor.text)
                            self.add_log(f"Saved configuration: {config_spinner.text}")
                            
                            # Update the spinner in the main UI
                            self.config_spinner.values = self._get_config_files()
                            
                            popup.dismiss()
                        except json.JSONDecodeError as e:
                            self.show_error(f"Invalid JSON format: {str(e)}")
                        except Exception as e:
                            self.show_error(f"Error saving configuration: {str(e)}")
                
                load_button.bind(on_release=on_load)
                save_button.bind(on_release=on_save)
                
                button_row.add_widget(cancel_button)
                button_row.add_widget(load_button)
                button_row.add_widget(save_button)
                
                layout.add_widget(config_row)
                layout.add_widget(editor)
                layout.add_widget(button_row)
                
                popup.content = layout
                popup.open()
            
            def export_results(self, instance):
                """Export results to files"""
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Create results directory if it doesn't exist
                ensure_directory('results')
                
                # Export logs
                log_file = os.path.join('results', f'logs_{timestamp}.txt')
                try:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write(self.logs.text)
                    
                    self.add_log(f"Logs exported to {log_file}")
                except Exception as e:
                    self.show_error(f"Error exporting logs: {str(e)}")
                
                # In a real implementation, we would also export hits and other results
                
                def get_panel_lines(panel):
                    if hasattr(panel, 'text'):
                        return panel.text.splitlines()
                    return []
        
        class CyberCheckerApp(App):
            """Main application class"""
            def build(self):
                """Build the application"""
                return MainScreen()
        
        if __name__ == '__main__':
            CyberCheckerApp().run()
            
    except ImportError as e:
        print(f"Error importing Kivy: {e}")
        print("Please install Kivy or run 'python cli_checker.py' for CLI mode.")
        sys.exit(1)