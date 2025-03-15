import requests
from requests.auth import HTTPBasicAuth
import streamlit as st
from src.config.config import API_TOKEN, EMAIL, JIRA_URL


class BaseJiraClient:
    """Base client for interacting with the Jira REST API"""

    def __init__(self):
        """Initialize the Jira client with authentication details"""
        self.API_TOKEN = API_TOKEN
        self.EMAIL = EMAIL
        self.JIRA_URL = f"{JIRA_URL}/rest/api/3/"
        self.AGILE_URL = f"{JIRA_URL}/rest/agile/1.0/"
        self.auth = HTTPBasicAuth(self.EMAIL, self.API_TOKEN)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self, endpoint, params=None, use_agile_api=False):
        """Make a GET request to the Jira API

        Args:
            endpoint (str): The API endpoint to call
            params (dict, optional): Query parameters for the request
            use_agile_api (bool, optional): Whether to use the Agile API instead of the REST API

        Returns:
            requests.Response: The response from the API
        """
        try:
            base_url = self.AGILE_URL if use_agile_api else self.JIRA_URL
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=self.headers,
                auth=self.auth,
                params=params,
            )
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to Jira API: {str(e)}")
            return None

    def post(self, endpoint, payload):
        """Make a POST request to the Jira API

        Args:
            endpoint (str): The API endpoint to call
            payload (dict): The JSON payload to send

        Returns:
            requests.Response: The response from the API
        """
        try:
            response = requests.post(
                f"{self.JIRA_URL}{endpoint}",
                json=payload,
                headers=self.headers,
                auth=self.auth,
            )
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to Jira API: {str(e)}")
            return None

    def put(self, endpoint, payload):
        """Make a PUT request to the Jira API

        Args:
            endpoint (str): The API endpoint to call
            payload (dict): The JSON payload to send

        Returns:
            requests.Response: The response from the API
        """
        try:
            response = requests.put(
                f"{self.JIRA_URL}{endpoint}",
                json=payload,
                headers=self.headers,
                auth=self.auth,
            )
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to Jira API: {str(e)}")
            return None

    def _make_request(self, endpoint):
        """Make a simple GET request to the Jira API

        Args:
            endpoint (str): The API endpoint to call

        Returns:
            dict: The JSON response data if successful, None otherwise
        """
        response = self.get(endpoint)
        if response and response.status_code == 200:
            return response.json()
        return None
