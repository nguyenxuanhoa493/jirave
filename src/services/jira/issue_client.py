import streamlit as st
from src.services.jira.base_client import BaseJiraClient


class IssueClient(BaseJiraClient):
    """Client for handling Jira issues"""

    def get_issue(self, issue_key, custom_field_ids=None):
        """Get details for a specific issue

        Args:
            issue_key (str): The issue key (e.g., 'CLD-123')
            custom_field_ids (list, optional): List of custom field IDs to include

        Returns:
            dict: The issue data if successful, None otherwise
        """
        # Lấy tất cả các trường cần thiết
        fields = "summary,status,issuetype,priority,assignee,reporter,created,updated,description,customfield_10016,timeoriginalestimate,timeestimate,timespent"

        # Nếu có custom fields, thêm vào fields
        if custom_field_ids:
            fields += "," + ",".join(custom_field_ids)

        params = {"fields": fields}

        response = self.get(f"issue/{issue_key}", params=params)
        if response and response.status_code == 200:
            return response.json()
        return None

    def search_issues(self, jql, fields=None, max_results=1000):
        """Search for issues using JQL

        Args:
            jql (str): The JQL query string
            fields (list, optional): List of fields to include in the response
            max_results (int, optional): Maximum number of results to return

        Returns:
            list: The matching issues if successful, empty list otherwise
        """
        if fields is None:
            fields = ["summary", "status", "assignee"]

        params = {"jql": jql, "fields": ",".join(fields), "maxResults": max_results}

        response = self.get("search", params=params)
        if response and response.status_code == 200:
            return response.json().get("issues", [])
        return []

    def get_issue_types(self, project_key):
        """Get all issue types for a project

        Args:
            project_key (str): The project key

        Returns:
            list: List of issue types
        """
        response = self.get(f"project/{project_key}/statuses")
        if response and response.status_code == 200:
            issue_types = []
            for item in response.json():
                issue_types.append({"id": item["id"], "name": item["name"]})
            return issue_types
        return []

    def update_issue(self, issue_key, fields_data):
        """Update fields of an issue

        Args:
            issue_key (str): The issue key to update
            fields_data (dict): Field data to update

        Returns:
            bool: True if successful, False otherwise
        """
        payload = {"fields": fields_data}
        response = self.put(f"issue/{issue_key}", payload)
        if response and response.status_code == 204:
            return True
        return False
