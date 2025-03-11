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
            fields = ["summary", "status", "assignee"]

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
            list: The boards if successful, empty list otherwise
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
            list: The sprints if successful, empty list otherwise
        """
        params = {"state": state} if state else {}
        response = self.get(
            f"board/{board_id}/sprint", params=params, use_agile_api=True
        )
        if response and response.status_code == 200:
            return response.json().get("values", [])
        return []

    def get_sprint_issues(self, sprint_id, fields=None, status_names=None):
        """Get all issues in a sprint

        Args:
            sprint_id (int): The sprint ID
            fields (list, optional): List of fields to include in the response
            status_names (list, optional): List of status names to filter issues by

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

        # Tạo JQL query với điều kiện status nếu được chỉ định
        jql = f"sprint = {sprint_id}"
        if status_names:
            status_conditions = [f'status = "{status}"' for status in status_names]
            jql += f" AND ({' OR '.join(status_conditions)})"

        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "maxResults": 50,
            "expand": "",
        }

        all_issues = []
        start_at = 0

        while True:
            params["startAt"] = start_at
            response = self.get("search", params=params)
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
        """Get all custom fields

        Returns:
            list: All custom fields if successful, empty list otherwise
        """
        response = self.get("field")
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

        # Loop through each board and get all sprints
        for board in boards:
            board_id = board["id"]

            # Get all sprints for this board (active, future, closed)
            for state in ["active", "future", "closed"]:
                sprints = self.get_board_sprints(board_id, state=state)
                all_sprints.extend(sprints)

        # Sort sprints by start date (newest first)
        all_sprints.sort(key=lambda x: x.get("startDate", ""), reverse=True)

        return all_sprints

    def _make_request(self, endpoint):
        """
        Make a request to the Jira API.
        :param endpoint: The API endpoint to call.
        :return: The response from the API.
        """
        # Implement your API request logic here
        pass

    def get_field_details(self, field_id):
        """Get details of a field including whether it's editable

        Args:
            field_id (str): The ID of the field

        Returns:
            dict: Field details if successful, None otherwise
        """
        response = self.get(f"field/{field_id}")
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_custom_field_id(self, field_name):
        """Get custom field ID by name

        Args:
            field_name (str): The name of the custom field

        Returns:
            str: The custom field ID if found, None otherwise
        """
        custom_fields = self.get_custom_fields()
        for field in custom_fields:
            if field.get("name") == field_name:
                return field.get("id")
        return None

    def update_custom_fields(self, issues, data_set):
        """Cập nhật nhiều custom field cho danh sách issues

        Args:
            issues (list): Danh sách các issue cần cập nhật
            data_set (dict): Dictionary chứa cặp {field_name: value} cần cập nhật

        Returns:
            dict: Kết quả cập nhật cho từng field
                {
                    field_name: {
                        'success': bool,
                        'message': str,
                        'updated_issues': int
                    }
                }
        """
        if not issues:
            return {"error": "Không có issue nào để cập nhật"}

        results = {}
        test_issue = [issues[0]]

        for field_name, value in data_set.items():
            field_id = self.get_custom_field_id(field_name)
            if not field_id:
                results[field_name] = {
                    "success": False,
                    "message": f'Không tìm thấy custom field "{field_name}"',
                    "updated_issues": 0,
                }
                continue

            # Thử nghiệm với issue đầu tiên
            test_success = self.update_issues_custom_field(
                issues=test_issue, custom_field_id=field_id, value=value
            )

            if not test_success:
                results[field_name] = {
                    "success": False,
                    "message": f"Thử nghiệm cập nhật {field_name} thất bại",
                    "updated_issues": 0,
                }

    def post(self, endpoint, payload):
        """Make a POST request to the Jira API

        Args:
            endpoint (str): The API endpoint to call
            payload (dict): The data to send in the request body

        Returns:
            requests.Response: The response from the API
        """
        try:
            response = requests.post(
                f"{self.JIRA_URL}{endpoint}",
                headers=self.headers,
                auth=self.auth,
                json=payload,
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Jira API: {str(e)}")
            return None

    def put(self, endpoint, payload):
        """Make a PUT request to the Jira API

        Args:
            endpoint (str): The API endpoint to call
            payload (dict): The data to send in the request body

        Returns:
            requests.Response: The response from the API
        """
        try:
            response = requests.put(
                f"{self.JIRA_URL}{endpoint}",
                headers=self.headers,
                auth=self.auth,
                json=payload,
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Jira API: {str(e)}")
            return None

    def update_issue(self, issue_key, fields_data):
        """Update fields for a specific issue

        Args:
            issue_key (str): The issue key (e.g., 'CLD-123')
            fields_data (dict): Dictionary containing the fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        payload = {"fields": fields_data}

        response = self.put(f"issue/{issue_key}", payload)

        if response and response.status_code in [200, 204]:
            return True

        if response:
            try:
                error_data = response.json()
                print(f"Error updating issue {issue_key}:")
                print(f"Status code: {response.status_code}")
                print(f"Error messages: {error_data.get('errorMessages', [])}")
                print(f"Errors: {error_data.get('errors', {})}")
            except:
                print(f"Error updating issue {issue_key}: {response.text}")

        return False
