#!/usr/bin/env python3
"""
CyberChecker CLI
A command-line interface version of CyberChecker without any GUI dependencies.
This version does not import Kivy at all and can run in any environment.
"""

import os
import sys
import re
import time
import threading
import json
import queue
import argparse
import requests
from datetime import datetime, timedelta
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(InsecureRequestWarning)

def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    return str(timedelta(seconds=seconds)).split('.')[0]

def ensure_directory(directory):
    """Ensure a directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)

class SimpleConfigManager:
    """Simple version of ConfigManager without Kivy dependencies"""
    
    def __init__(self, config_dir="configs"):
        """Initialize the configuration manager"""
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
    
    def get_config_files(self):
        """Get list of available config files"""
        if not os.path.exists(self.config_dir):
            return []
        
        config_files = []
        for filename in os.listdir(self.config_dir):
            if filename.endswith(".json"):
                config_files.append(filename[:-5])  # Remove .json extension
        
        return sorted(config_files)
    
    def load_config(self, name):
        """Load a configuration by name"""
        config_path = os.path.join(self.config_dir, f"{name}.json")
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return config_data
        except Exception as e:
            print(f"Error loading config {name}: {str(e)}")
            return None

class SimpleHttpClient:
    """Simple version of HttpClient without Kivy dependencies"""
    
    def __init__(self, timeout=10):
        """Initialize the HTTP client"""
        self.timeout = timeout
        self.session = requests.Session()
        self.proxies = None
    
    def set_proxy(self, proxy_dict):
        """Set proxy for requests"""
        self.proxies = proxy_dict
    
    def clear_proxy(self):
        """Clear proxy settings"""
        self.proxies = None
    
    def _make_request(self, method, url, **kwargs):
        """Make an HTTP request with error handling"""
        try:
            # Add proxy settings if available
            if self.proxies:
                kwargs['proxies'] = self.proxies
            
            # Add timeout
            kwargs['timeout'] = self.timeout
            
            # Make the request
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            # Create a mock response with error info
            return {
                'status_code': 0,
                'text': str(e),
                'error': True,
                'error_message': str(e),
                'headers': {},
                'url': url,
                'content': b'',
                'json': lambda: {}
            }
    
    def get(self, url, headers=None, params=None, verify=False):
        """Make a GET request"""
        return self._make_request('GET', url, headers=headers, params=params, verify=verify)
    
    def post(self, url, headers=None, data=None, json=None, verify=False):
        """Make a POST request"""
        return self._make_request('POST', url, headers=headers, data=data, json=json, verify=verify)
    
    def check_with_config(self, username, password, config):
        """Check an account using the given configuration"""
        result = {
            'success': False,
            'failure': False,
            'error': False,
            'error_message': '',
            'captured_data': {}
        }
        
        try:
            # Captured data from previous requests
            captured_data = {}
            
            # Process each request in the configuration
            for i, req_config in enumerate(config.get('requests', [])):
                method = req_config.get('method', 'GET').upper()
                url = req_config.get('url', '')
                headers = req_config.get('headers', {})
                data = req_config.get('data', {})
                json_data = req_config.get('json', None)
                verify = req_config.get('verify', False)
                
                # Prepare request data
                url = self._replace_variables(url, username, password, captured_data)
                headers = self._prepare_request_data(headers, username, password, captured_data)
                
                if isinstance(data, dict):
                    data = self._prepare_request_data(data, username, password, captured_data)
                elif isinstance(data, str):
                    data = self._replace_variables(data, username, password, captured_data)
                
                if isinstance(json_data, dict):
                    json_data = self._prepare_request_data(json_data, username, password, captured_data)
                
                # Make the request based on the method
                if method == 'GET':
                    response = self.get(url, headers=headers, verify=verify)
                elif method == 'POST':
                    response = self.post(url, headers=headers, data=data, json=json_data, verify=verify)
                else:
                    result['error'] = True
                    result['error_message'] = f"Unsupported HTTP method: {method}"
                    return result
                
                # Check if the response is an error
                if hasattr(response, 'get') and response.get('error', False):
                    result['error'] = True
                    result['error_message'] = response.get('text', 'Unknown error')
                    return result
                
                # Extract captured data if defined in the config
                if i == len(config.get('requests', [])) - 1:  # Only capture from final request
                    for capture_config in config.get('capture', []):
                        name = capture_config.get('name', '')
                        start = capture_config.get('start', '')
                        end = capture_config.get('end', '')
                        
                        if name and start and end:
                            try:
                                # Get response text
                                response_text = response.text if hasattr(response, 'text') else str(response)
                                pattern = f'{re.escape(start)}(.*?){re.escape(end)}'
                                match = re.search(pattern, response_text, re.DOTALL)
                                if match:
                                    captured_data[name] = match.group(1).strip()
                                    result['captured_data'][name] = match.group(1).strip()
                            except Exception as e:
                                # Capture error but continue process
                                print(f"Error capturing data {name}: {str(e)}")
                
                # Check success and failure conditions on the final request
                if i == len(config.get('requests', [])) - 1:
                    # Check success conditions
                    if config.get('success_conditions'):
                        result['success'] = self._check_conditions(response, config.get('success_conditions', []))
                    
                    # Check failure conditions
                    if config.get('failure_conditions'):
                        result['failure'] = self._check_conditions(response, config.get('failure_conditions', []))
            
            return result
            
        except Exception as e:
            result['error'] = True
            result['error_message'] = str(e)
            return result
    
    def _prepare_request_data(self, req_config, username, password, captured_data=None):
        """Prepare request data by replacing variables"""
        if isinstance(req_config, dict):
            # Process each key-value pair in the dictionary
            result = {}
            for key, value in req_config.items():
                # Replace variables in the key
                new_key = self._replace_variables(key, username, password, captured_data)
                
                # Replace variables in the value if it's a string
                if isinstance(value, str):
                    new_value = self._replace_variables(value, username, password, captured_data)
                elif isinstance(value, dict):
                    # Recursively process nested dictionaries
                    new_value = self._prepare_request_data(value, username, password, captured_data)
                elif isinstance(value, list):
                    # Process each item in the list
                    new_value = []
                    for item in value:
                        if isinstance(item, str):
                            new_value.append(self._replace_variables(item, username, password, captured_data))
                        elif isinstance(item, dict):
                            new_value.append(self._prepare_request_data(item, username, password, captured_data))
                        else:
                            new_value.append(item)
                else:
                    new_value = value
                
                result[new_key] = new_value
            
            return result
        else:
            # If it's not a dictionary, return as is
            return req_config
    
    def _replace_variables(self, text, username, password, captured_data=None):
        """Replace variables in text with actual values"""
        if not isinstance(text, str):
            return text
        
        # Replace username and password
        result = text.replace('{USERNAME}', username).replace('{PASSWORD}', password)
        
        # Replace captured variables if present
        if captured_data:
            for name, value in captured_data.items():
                # Both formats: {VARIABLE} and {variable}
                result = result.replace(f'{{{name.upper()}}}', value)
                result = result.replace(f'{{{name.lower()}}}', value)
                result = result.replace(f'{{{name}}}', value)
        
        return result
    
    def _check_conditions(self, response, conditions):
        """Check if response matches the given conditions"""
        if not conditions:
            return False
        
        # Get response properties
        if hasattr(response, 'text'):
            response_text = response.text
            status_code = response.status_code
            try:
                json_data = response.json()
            except:
                json_data = {}
        else:
            # Fallback for our custom error response
            response_text = response.get('text', '')
            status_code = response.get('status_code', 0)
            json_data = {}
        
        # Check each condition
        for condition in conditions:
            condition_type = condition.get('type', '').lower()
            condition_value = condition.get('value', '')
            
            if condition_type == 'contains':
                # Check if the response contains the value
                if condition_value not in response_text:
                    return False
            elif condition_type == 'not_contains':
                # Check if the response does not contain the value
                if condition_value in response_text:
                    return False
            elif condition_type == 'status_code':
                # Check if the response status code matches
                try:
                    expected_code = int(condition_value)
                    if status_code != expected_code:
                        return False
                except:
                    return False
            elif condition_type == 'json_contains':
                # Check if the response JSON contains the value
                try:
                    json_path = condition.get('path', '')
                    
                    # Navigate the JSON path
                    path_parts = json_path.split('.')
                    current = json_data
                    for part in path_parts:
                        if part:
                            if isinstance(current, dict) and part in current:
                                current = current[part]
                            else:
                                return False
                    
                    # Check if the final value contains the condition value
                    if isinstance(current, str) and condition_value not in current:
                        return False
                    elif not isinstance(current, str) and condition_value not in str(current):
                        return False
                except:
                    return False
        
        # All conditions matched
        return True

class ConsoleChecker:
    """CLI version of CyberChecker for testing and basic usage"""
    
    def __init__(self):
        self.config_manager = SimpleConfigManager()
        self.http_client = SimpleHttpClient()
        
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
            self.log("\nChecking completed.")
            
            # Save results
            self.export_results()
            
            return True
            
        except KeyboardInterrupt:
            self.log("\nInterrupted by user. Stopping threads...")
            self.pause_event.set()
            self.is_checking = False
            
            # Wait for threads to finish
            for t in self.worker_threads:
                t.join(0.1)
            
            self.log("Stopped.")
            return False
    
    def worker_thread(self, queue, config, proxies, proxy_type, timeout, pause_event):
        """Worker thread for checking"""
        http_client = SimpleHttpClient(timeout=timeout)
        
        proxy_index = 0
        proxy = None
        
        while not pause_event.is_set():
            try:
                # Get next combo line
                try:
                    combo_line = queue.get(block=False)
                except Exception:
                    # No more work to do (queue empty)
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
                self.stats['cpm'] = int((self.stats['cpm'] * 0.6) + (new_cpm * 0.4))
    
    def display_progress(self):
        """Display progress in terminal"""
        current_time = time.time()
        elapsed = current_time - self.stats.get('start_time', current_time)
        elapsed_str = format_time(int(elapsed))
        
        # Calculate progress percentage
        if self.stats['tocheck'] > 0:
            progress = int((self.stats['checked'] / self.stats['tocheck']) * 100)
        else:
            progress = 0
        
        # Clear line and print status
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        status = (
            f"Progress: {progress:3d}% | "
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
        
        self.log(f"Results exported to '{results_dir}' directory:")
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