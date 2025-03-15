"""
Compatibility layer for existing code.
This module imports and re-exports the JiraClientFacade as JiraClient
to maintain compatibility with existing code.
"""

from src.services.jira.jira_client_facade import JiraClientFacade
from src.services.jira.sprint_client import SprintClient
import os
import streamlit as st
import requests
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import re
from src.config import DEBUG

# Load environment variables
load_dotenv()

# Re-export JiraClientFacade as JiraClient for backward compatibility
JiraClient = JiraClientFacade


# Lớp JiraClientLegacy (đổi tên từ JiraClient để tránh xung đột)
class JiraClientLegacy:
    """Client kết nối đến Jira API (Legacy version - không sử dụng hãy dùng JiraClientFacade)"""

    def __init__(self):
        """Khởi tạo kết nối đến Jira"""
        self.url = os.environ.get("JIRA_URL")
        self.auth = HTTPBasicAuth(
            os.environ.get("JIRA_USER"), os.environ.get("JIRA_API_TOKEN")
        )
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Kiểm tra thông tin xác thực
        self._validate_credentials()

        # Khởi tạo sprint_client (sprint_client sử dụng Agile API)
        self.sprint_client = SprintClient(self.url, self.auth, self.headers)

    def _validate_credentials(self):
        """Kiểm tra thông tin xác thực Jira API"""
        if not self.url or not self.auth.username or not self.auth.password:
            print(
                "Thiếu thông tin xác thực Jira API. Vui lòng kiểm tra biến môi trường."
            )
            return False

        if self.auth.password == "Bạn cần tạo API token mới":
            print(
                "⚠️ API Token Jira chưa được cập nhật. Vui lòng tạo token mới tại https://id.atlassian.com/manage-profile/security/api-tokens"
            )
            return False

        # Thử gọi API kiểm tra kết nối
        try:
            # Gọi một API đơn giản để kiểm tra kết nối
            response = self.get("myself")
            if response.status_code == 200:
                print(
                    f"✅ Kết nối thành công đến Jira API với người dùng: {response.json().get('displayName', 'Unknown')}"
                )
                return True
            else:
                print(f"❌ Kết nối thất bại: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Lỗi kết nối đến Jira API: {str(e)}")
            return False

    def get(self, endpoint, params=None, use_agile_api=False):
        """Gọi Jira API với phương thức GET

        Args:
            endpoint (str): Endpoint của API
            params (dict, optional): Các tham số truyền vào. Defaults to None.
            use_agile_api (bool, optional): Sử dụng Agile API hay không. Defaults to False.

        Returns:
            requests.Response: Response từ API
        """
        try:
            if use_agile_api:
                url = f"{self.url}/rest/agile/1.0/{endpoint}"
            else:
                url = f"{self.url}/rest/api/3/{endpoint}"

            response = requests.get(
                url, auth=self.auth, headers=self.headers, params=params
            )

            # Kiểm tra lỗi xác thực
            if response.status_code == 401:
                error_msg = "Lỗi 401: Không thể xác thực với Jira API. Vui lòng kiểm tra lại thông tin đăng nhập và API token."
                if st and hasattr(st, "error"):
                    st.error(error_msg)
                print(error_msg)

            # Kiểm tra lỗi khác
            elif response.status_code >= 400:
                error_msg = f"Lỗi {response.status_code}: {response.text}"
                if st and hasattr(st, "error"):
                    st.error(error_msg)
                print(error_msg)

            return response
        except Exception as e:
            error_msg = f"Lỗi kết nối đến Jira API: {str(e)}"
            if st and hasattr(st, "error"):
                st.error(error_msg)
            print(error_msg)
            # Tạo một response giả với status_code 500
            response = requests.Response()
            response.status_code = 500
            response._content = str(e).encode()
            return response

    def get_all_sprints(self, project_key, max_results=100):
        """Lấy tất cả các sprints của dự án

        Args:
            project_key (str): Mã dự án
            max_results (int, optional): Số lượng kết quả tối đa. Defaults to 100.

        Returns:
            list: Danh sách các sprints
        """
        try:
            # Lấy danh sách board của dự án
            board_response = self.sprint_client.get(
                f"board?projectKeyOrId={project_key}", use_agile_api=True
            )
            if board_response.status_code != 200:
                print(
                    f"Error getting boards: {board_response.status_code} - {board_response.text}"
                )
                return []

            boards = board_response.json().get("values", [])
            if not boards:
                print(f"No boards found for project {project_key}")
                return []

            # Lấy danh sách sprints từ tất cả các board
            all_sprints = []
            for board in boards:
                board_id = board.get("id")
                sprint_response = self.sprint_client.get(
                    f"board/{board_id}/sprint?maxResults={max_results}",
                    use_agile_api=True,
                )
                if sprint_response.status_code != 200:
                    print(
                        f"Error getting sprints for board {board_id}: {sprint_response.status_code} - {sprint_response.text}"
                    )
                    continue

                sprints = sprint_response.json().get("values", [])
                all_sprints.extend(sprints)

            return all_sprints
        except Exception as e:
            print(f"Error getting all sprints: {str(e)}")
            return []

    def get_sprint_issues(self, sprint_id, fields=None, max_issues=50):
        """Lấy tất cả các issues trong sprint

        Args:
            sprint_id (int): ID của sprint
            fields (list, optional): Danh sách các trường cần lấy. Defaults to None.
            max_issues (int, optional): Số lượng issues tối đa. -1 để lấy tất cả. Defaults to 50.

        Returns:
            list: Danh sách các issues
        """
        try:
            all_issues = []
            start_at = 0
            max_results = 100  # Số lượng kết quả tối đa cho mỗi API call

            # Nếu có fields, gộp lại thành chuỗi
            fields_param = ",".join(fields) if fields else None

            # Lặp cho đến khi lấy hết issues hoặc đạt đến max_issues
            while True:
                params = {
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": fields_param,
                }

                response = self.sprint_client.get(
                    f"sprint/{sprint_id}/issue", params=params, use_agile_api=True
                )

                if response.status_code != 200:
                    print(
                        f"Error getting issues for sprint {sprint_id}: {response.status_code} - {response.text}"
                    )
                    break

                data = response.json()
                issues = data.get("issues", [])
                if not issues:
                    break

                all_issues.extend(issues)
                start_at += len(issues)

                # Kiểm tra nếu đã lấy đủ số lượng issues
                if max_issues > 0 and len(all_issues) >= max_issues:
                    all_issues = all_issues[:max_issues]
                    break

                # Kiểm tra nếu đã lấy hết issues
                if len(all_issues) >= data.get("total", 0):
                    break

            return all_issues
        except Exception as e:
            print(f"Error getting sprint issues: {str(e)}")
            return []

    def get_issue_worklogs(self, issue_key):
        """Lấy worklog của issue

        Args:
            issue_key (str): Mã issue

        Returns:
            list: Danh sách các worklog
        """
        try:
            response = self.get(f"issue/{issue_key}/worklog")
            if response.status_code != 200:
                print(
                    f"Error getting worklogs for issue {issue_key}: {response.status_code} - {response.text}"
                )
                return []

            return response.json().get("worklogs", [])
        except Exception as e:
            print(f"Error getting issue worklogs: {str(e)}")
            return []


class SprintClient:
    """Client kết nối đến Jira Sprint API (Agile API)"""

    def __init__(self, url, auth, headers):
        """Khởi tạo kết nối đến Jira Sprint API

        Args:
            url (str): URL của Jira
            auth (requests.auth.HTTPBasicAuth): Thông tin xác thực
            headers (dict): Headers cho request
        """
        self.url = url
        self.auth = auth
        self.headers = headers

    def get(self, endpoint, params=None, use_agile_api=True):
        """Gọi Jira Sprint API với phương thức GET

        Args:
            endpoint (str): Endpoint của API
            params (dict, optional): Các tham số truyền vào. Defaults to None.
            use_agile_api (bool, optional): Sử dụng Agile API hay không. Defaults to True.

        Returns:
            requests.Response: Response từ API
        """
        try:
            if use_agile_api:
                url = f"{self.url}/rest/agile/1.0/{endpoint}"
            else:
                url = f"{self.url}/rest/api/3/{endpoint}"

            response = requests.get(
                url, auth=self.auth, headers=self.headers, params=params
            )

            # Xử lý lỗi 401 Unauthorized
            if response.status_code == 401:
                error_msg = "Lỗi 401 Unauthorized: Token API của bạn có thể đã hết hạn hoặc không hợp lệ. Vui lòng kiểm tra lại."
                print(error_msg)
                if st and hasattr(st, "error"):
                    st.error(error_msg)

            return response
        except Exception as e:
            error_msg = f"Error connecting to Jira API: {str(e)}"
            print(error_msg)
            if st and hasattr(st, "error"):
                st.error(error_msg)

            # Tạo một response giả với status_code 500
            response = requests.Response()
            response.status_code = 500
            response._content = str(e).encode()
            return response
