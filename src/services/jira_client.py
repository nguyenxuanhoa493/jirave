import requests
from requests.auth import HTTPBasicAuth
import streamlit as st
from src.config.config import API_TOKEN, EMAIL, JIRA_URL


class JiraClient:
    """Client for interacting with the Jira REST API"""

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

    def get_issue(self, issue_key):
        """Get details for a specific issue

        Args:
            issue_key (str): The issue key (e.g., 'CLD-123')

        Returns:
            dict: The issue data if successful, None otherwise
        """
        # Lấy tất cả các trường cần thiết
        fields = "summary,status,issuetype,priority,assignee,reporter,created,updated,description,customfield_10016,timeoriginalestimate,timeestimate,timespent"

        params = {"fields": fields}

        response = self.get(f"issue/{issue_key}", params=params)
        if response and response.status_code == 200:
            return response.json()
        return None

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
            fields = ["summary", "worklog", "assignee"]

        params = {"jql": jql, "fields": ",".join(fields), "maxResults": max_results}

        response = self.get("search", params=params)
        if response and response.status_code == 200:
            return response.json().get("issues", [])
        return []

    def get_all_projects(self):
        """Get all accessible projects

        Returns:
            list: All projects if successful, empty list otherwise
        """
        response = self.get("project")
        if response and response.status_code == 200:
            return response.json()
        return []

    def get_project_boards(self, project_key):
        """Get all boards for a project

        Args:
            project_key (str): The project key

        Returns:
            list: All boards if successful, empty list otherwise
        """
        params = {"projectKeyOrId": project_key}

        response = self.get("board", params=params, use_agile_api=True)
        if response and response.status_code == 200:
            return response.json().get("values", [])
        return []

    def get_board_sprints(self, board_id, state=None):
        """Get all sprints for a board

        Args:
            board_id (int): The board ID
            state (str, optional): Filter sprints by state (active, future, closed)

        Returns:
            list: All sprints if successful, empty list otherwise
        """
        params = {}
        if state:
            params["state"] = state

        response = self.get(
            f"board/{board_id}/sprint", params=params, use_agile_api=True
        )
        if response and response.status_code == 200:
            return response.json().get("values", [])
        return []

    def get_sprint_issues(self, sprint_id, fields=None):
        """Get all issues in a sprint

        Args:
            sprint_id (int): The sprint ID
            fields (list, optional): List of fields to include in the response

        Returns:
            list: All issues if successful, empty list otherwise
        """
        if fields is None:
            fields = [
                "summary",
                "status",
                "issuetype",
                "assignee",
                "priority",
                "customfield_10016",
                "customfield_10130",
                "timespent",
                "timeoriginalestimate",
            ]

        params = {
            "fields": ",".join(fields),
            "maxResults": 50,
            "expand": "",
        }

        all_issues = []
        start_at = 0

        while True:
            params["startAt"] = start_at
            response = self.get(
                f"sprint/{sprint_id}/issue", params=params, use_agile_api=True
            )
            if response and response.status_code == 200:
                issues = response.json().get("issues", [])
                all_issues.extend(issues)
                if len(issues) < 50:
                    break
                start_at += 50
            else:
                break

        return all_issues

    def get_issue_types(self, project_key):
        """Get all issue types for a project

        Args:
            project_key (str): The project key

        Returns:
            list: All issue types if successful, empty list otherwise
        """
        response = self.get(f"project/{project_key}")
        if response and response.status_code == 200:
            project_data = response.json()
            return project_data.get("issueTypes", [])
        return []

    def get_project_statuses(self, project_key):
        """Get all statuses for a project

        Args:
            project_key (str): The project key

        Returns:
            list: All statuses if successful, empty list otherwise
        """
        response = self.get(f"project/{project_key}/statuses")
        if response and response.status_code == 200:
            return response.json()
        return []

    def get_sprint_report(self, board_id, sprint_id):
        """Get sprint report

        Args:
            board_id (int): The board ID
            sprint_id (int): The sprint ID

        Returns:
            dict: Sprint report if successful, empty dict otherwise
        """
        # Chức năng này không được sử dụng nữa vì không tìm thấy API phù hợp
        # Trả về dict rỗng để các logic khác vẫn hoạt động
        return {}

    def get_custom_fields(self):
        """Get custom fields from Jira"""
        endpoint = "field"
        response = self.get(endpoint)
        if response:
            fields = response.json()
            custom_fields = [field for field in fields if field.get("custom")]
            return custom_fields
        return []

    def get_active_sprint(self, project_key):
        """Get the currently active sprint for a project

        Args:
            project_key (str): The project key

        Returns:
            dict: Sprint data if found, None otherwise
        """
        # Get all boards for the project
        boards = self.get_project_boards(project_key)

        if not boards:
            return None

        # Find the main scrum board (usually the first one)
        board_id = boards[0]["id"]

        # Get active sprints for the board
        active_sprints = self.get_board_sprints(board_id, state="active")

        if not active_sprints:
            return None

        # Return the most recent active sprint
        return active_sprints[0]

    def get_all_sprints(self, project_key):
        """
        Fetch all sprints for a given project.

        Args:
            project_key (str): The key of the project to fetch sprints for.

        Returns:
            list: A list of all sprints for the project.
        """
        # Get all boards for the project
        boards = self.get_project_boards(project_key)

        if not boards:
            return []

        all_sprints = []

        # Get sprints from the main board (usually the first one)
        board_id = boards[0]["id"]

        # Get all sprints (active, closed, future) for the board
        sprints = self.get_board_sprints(board_id)

        # Sort sprints by name in reverse order (assuming names contain sprint numbers)
        if sprints:
            # Kiểm tra và thêm các trường cần thiết nếu thiếu
            for sprint in sprints:
                # Đảm bảo có trường startDate và endDate
                if "startDate" not in sprint:
                    sprint["startDate"] = None
                if "endDate" not in sprint:
                    sprint["endDate"] = None
                if "completeDate" not in sprint:
                    sprint["completeDate"] = None

            # Sắp xếp các sprint theo tên (giả định tên chứa số sprint)
            sprints.sort(key=lambda x: x.get("name", ""), reverse=True)
            all_sprints.extend(sprints)

        return all_sprints

    def _make_request(self, endpoint):
        """
        Make a request to the Jira API.
        :param endpoint: The API endpoint to call.
        :return: The response from the API.
        """
        # Implement your API request logic here
        pass
