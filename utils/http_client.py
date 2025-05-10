"""
HTTP Client
Provides functionality for making HTTP requests
"""

import time
import re
import json
import requests
from requests.exceptions import RequestException, Timeout
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure request warnings
import urllib3
urllib3.disable_warnings(InsecureRequestWarning)


class HttpClient:
    """
    Client for making HTTP requests.
    Includes functionality for parsing responses and checking conditions.
    """

    def __init__(self, timeout=10, verify=False):
        """
        Initialize the HTTP client.
        
        :param timeout: Request timeout in seconds
        :param verify: Whether to verify SSL certificates
        """
        self.timeout = timeout
        self.verify = verify
        self.session = requests.Session()
        self.proxies = None
        self.last_response = None
        self.retries = 3
        self.retry_delay = 1
    
    def set_proxy(self, proxy_dict):
        """
        Set proxy for requests.
        
        :param proxy_dict: Dictionary with proxy settings
        """
        self.proxies = proxy_dict
    
    def clear_proxy(self):
        """
        Clear proxy settings.
        """
        self.proxies = None
    
    def set_timeout(self, timeout):
        """
        Set request timeout.
        
        :param timeout: Timeout in seconds
        """
        self.timeout = timeout
    
    def get(self, url, headers=None, params=None, verify=None):
        """
        Make a GET request.
        
        :param url: URL to request
        :param headers: Headers to include in the request
        :param params: Query parameters
        :param verify: Whether to verify SSL certificates (overrides instance setting)
        :return: Response object
        """
        verify = self.verify if verify is None else verify
        
        for attempt in range(self.retries):
            try:
                response = self.session.get(
                    url=url,
                    headers=headers,
                    params=params,
                    proxies=self.proxies,
                    timeout=self.timeout,
                    verify=verify
                )
                self.last_response = response
                return response
            except (RequestException, Timeout) as e:
                if attempt == self.retries - 1:
                    # Last attempt failed, return error response
                    return {
                        'status_code': 0,
                        'text': str(e),
                        'error': True,
                        'error_message': str(e)
                    }
                time.sleep(self.retry_delay)
    
    def post(self, url, headers=None, data=None, json=None, verify=None):
        """
        Make a POST request.
        
        :param url: URL to request
        :param headers: Headers to include in the request
        :param data: Form data to include in the request
        :param json: JSON data to include in the request
        :param verify: Whether to verify SSL certificates (overrides instance setting)
        :return: Response object
        """
        verify = self.verify if verify is None else verify
        
        for attempt in range(self.retries):
            try:
                response = self.session.post(
                    url=url,
                    headers=headers,
                    data=data,
                    json=json,
                    proxies=self.proxies,
                    timeout=self.timeout,
                    verify=verify
                )
                self.last_response = response
                return response
            except (RequestException, Timeout) as e:
                if attempt == self.retries - 1:
                    # Last attempt failed, return error response
                    return {
                        'status_code': 0,
                        'text': str(e),
                        'error': True,
                        'error_message': str(e)
                    }
                time.sleep(self.retry_delay)
    
    def put(self, url, headers=None, data=None, json=None, verify=None):
        """
        Make a PUT request.
        
        :param url: URL to request
        :param headers: Headers to include in the request
        :param data: Form data to include in the request
        :param json: JSON data to include in the request
        :param verify: Whether to verify SSL certificates (overrides instance setting)
        :return: Response object
        """
        verify = self.verify if verify is None else verify
        
        for attempt in range(self.retries):
            try:
                response = self.session.put(
                    url=url,
                    headers=headers,
                    data=data,
                    json=json,
                    proxies=self.proxies,
                    timeout=self.timeout,
                    verify=verify
                )
                self.last_response = response
                return response
            except (RequestException, Timeout) as e:
                if attempt == self.retries - 1:
                    # Last attempt failed, return error response
                    return {
                        'status_code': 0,
                        'text': str(e),
                        'error': True,
                        'error_message': str(e)
                    }
                time.sleep(self.retry_delay)
    
    def delete(self, url, headers=None, verify=None):
        """
        Make a DELETE request.
        
        :param url: URL to request
        :param headers: Headers to include in the request
        :param verify: Whether to verify SSL certificates (overrides instance setting)
        :return: Response object
        """
        verify = self.verify if verify is None else verify
        
        for attempt in range(self.retries):
            try:
                response = self.session.delete(
                    url=url,
                    headers=headers,
                    proxies=self.proxies,
                    timeout=self.timeout,
                    verify=verify
                )
                self.last_response = response
                return response
            except (RequestException, Timeout) as e:
                if attempt == self.retries - 1:
                    # Last attempt failed, return error response
                    return {
                        'status_code': 0,
                        'text': str(e),
                        'error': True,
                        'error_message': str(e)
                    }
                time.sleep(self.retry_delay)
    
    def extract_substring(self, text, start, end):
        """
        Extract a substring between two delimiters.
        
        :param text: Text to extract from
        :param start: Start delimiter
        :param end: End delimiter
        :return: Extracted substring or None
        """
        if not text or not start or not end:
            return None
        
        try:
            pattern = f'{re.escape(start)}(.*?){re.escape(end)}'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
            return None
        except Exception:
            return None
    
    def check_with_config(self, username, password, config):
        """
        Check an account using the given configuration.
        
        :param username: Account username
        :param password: Account password
        :param config: Configuration dictionary
        :return: Dictionary with check results
        """
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
                elif method == 'PUT':
                    response = self.put(url, headers=headers, data=data, json=json_data, verify=verify)
                elif method == 'DELETE':
                    response = self.delete(url, headers=headers, verify=verify)
                else:
                    result['error'] = True
                    result['error_message'] = f"Unsupported HTTP method: {method}"
                    return result
                
                # Check if the response is an error
                if hasattr(response, 'get') and response.get('error', False):
                    result['error'] = True
                    result['error_message'] = response.get('error_message', 'Unknown error')
                    return result
                
                # Get response text
                if hasattr(response, 'text'):
                    response_text = response.text
                else:
                    response_text = str(response)
                
                # Extract captured data if defined in the config
                if i == len(config.get('requests', [])) - 1:  # Only capture from final request
                    for capture_config in config.get('capture', []):
                        name = capture_config.get('name', '')
                        start = capture_config.get('start', '')
                        end = capture_config.get('end', '')
                        
                        if name and start and end:
                            try:
                                captured_value = self.extract_substring(response_text, start, end)
                                if captured_value:
                                    captured_data[name] = captured_value
                                    result['captured_data'][name] = captured_value
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
    
    def _prepare_request_data(self, req_data, username, password, captured_data=None):
        """
        Prepare request data by replacing variables.
        
        :param req_data: Request data dictionary
        :param username: Account username
        :param password: Account password
        :param captured_data: Dictionary with captured data from previous requests
        :return: Prepared request data
        """
        if isinstance(req_data, dict):
            # Process each key-value pair in the dictionary
            result = {}
            for key, value in req_data.items():
                # Replace variables in the key
                new_key = self._replace_variables(key, username, password, captured_data)
                
                # Replace variables in the value based on its type
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
            return req_data
    
    def _replace_variables(self, text, username, password, captured_data=None):
        """
        Replace variables in text with actual values.
        
        :param text: Text to process
        :param username: Account username
        :param password: Account password
        :param captured_data: Dictionary with captured data from previous requests
        :return: Processed text
        """
        if not isinstance(text, str):
            return text
        
        # Replace username and password
        result = text.replace('{USERNAME}', username).replace('{PASSWORD}', password)
        
        # Replace captured variables if present
        if captured_data:
            for name, value in captured_data.items():
                # Support for {VARIABLE}, {variable} and {Variable} formats
                result = result.replace(f'{{{name.upper()}}}', value)
                result = result.replace(f'{{{name.lower()}}}', value)
                result = result.replace(f'{{{name}}}', value)
        
        return result
    
    def _check_conditions(self, response, conditions):
        """
        Check if response matches the given conditions.
        
        :param response: Response object to check
        :param conditions: List of condition dictionaries
        :return: True if all conditions match, False otherwise
        """
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
            # Fallback for custom error response
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