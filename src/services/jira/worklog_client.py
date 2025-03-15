import streamlit as st
from src.services.jira.base_client import BaseJiraClient


class WorklogClient(BaseJiraClient):
    """Client for handling Jira worklogs"""

    def get_issue_worklogs(self, issue_key):
        """Get worklogs for a specific issue

        Args:
            issue_key (str): The issue key (e.g., 'CLD-123')

        Returns:
            list: The worklogs if successful, empty list otherwise
        """
        response = self.get(f"issue/{issue_key}/worklog")
        if response and response.status_code == 200:
            return response.json().get("worklogs", [])
        return []

    def add_worklog(self, issue_key, time_spent, start_time=None, comment=None):
        """Add a worklog to an issue

        Args:
            issue_key (str): The issue key (e.g., 'CLD-123')
            time_spent (str): Time spent in Jira format (e.g., '1h 30m')
            start_time (str, optional): Start time in ISO 8601 format
            comment (str, optional): Comment for the worklog

        Returns:
            dict: The created worklog if successful, None otherwise
        """
        payload = {"timeSpent": time_spent}

        if start_time:
            payload["started"] = start_time

        if comment:
            payload["comment"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }

        response = self.post(f"issue/{issue_key}/worklog", payload)
        if response and response.status_code == 201:
            return response.json()
        return None
