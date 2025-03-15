import streamlit as st
from src.services.jira.base_client import BaseJiraClient


class ProjectClient(BaseJiraClient):
    """Client for handling Jira projects"""

    def get_all_projects(self):
        """Get all projects accessible to the user

        Returns:
            list: List of projects if successful, empty list otherwise
        """
        response = self.get("project")
        if response and response.status_code == 200:
            return response.json()
        return []

    def get_project_statuses(self, project_key):
        """Get all statuses for a project

        Args:
            project_key (str): The project key

        Returns:
            list: List of statuses
        """
        response = self.get(f"project/{project_key}/statuses")
        if response and response.status_code == 200:
            statuses = []
            for issue_type in response.json():
                for status in issue_type.get("statuses", []):
                    if status not in statuses:
                        statuses.append(status)
            return statuses
        return []

    def get_project_boards(self, project_key):
        """Get all boards for a project

        Args:
            project_key (str): The project key

        Returns:
            list: List of boards
        """
        params = {"projectKeyOrId": project_key}
        response = self.get("board", params=params, use_agile_api=True)
        if response and response.status_code == 200:
            return response.json().get("values", [])
        return []
