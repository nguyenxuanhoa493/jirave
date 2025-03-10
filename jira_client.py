import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

class JiraClient:
    def __init__(self):
        load_dotenv()
        self.API_TOKEN = os.getenv('API_TOKEN')
        self.EMAIL = os.getenv('EMAIL')
        self.JIRA_URL = f"{os.getenv('JIRA_URL')}/rest/api/3/"
        self.auth = HTTPBasicAuth(self.EMAIL, self.API_TOKEN)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
    def get(self, endpoint, params=None):
        response = requests.get(
            f"{self.JIRA_URL}{endpoint}",
            headers=self.headers,
            auth=self.auth,
            params=params
        )
        return response

    def post(self, endpoint, payload):
        response = requests.post(
            f"{self.JIRA_URL}{endpoint}",
            headers=self.headers,
            auth=self.auth,
            json=payload
        )
        return response
    def delete(self, endpoint):
        response = requests.delete(
            f"{self.JIRA_URL}{endpoint}",
            headers=self.headers,
            auth=self.auth
        )
        return response