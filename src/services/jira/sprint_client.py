import streamlit as st
from src.services.jira.base_client import BaseJiraClient


class SprintClient(BaseJiraClient):
    """Client for handling Jira sprints"""

    def get_board_sprints(self, board_id, state=None):
        """Get all sprints in a board

        Args:
            board_id (int): The board ID
            state (str, optional): Filter by sprint state (active, future, closed)

        Returns:
            list: List of sprints
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

    def get_sprint_issues(
        self, sprint_id, fields=None, status_names=None, max_issues=1000, project_key=None
    ):
        """Lấy tất cả issues trong một sprint

        Args:
            sprint_id (int): ID của sprint
            fields (list, optional): Danh sách các trường cần lấy
            status_names (list, optional): Lọc theo tên trạng thái
            max_issues (int, optional): Số lượng issues tối đa cần lấy, mặc định 1000
                                        Nếu max_issues=-1, sẽ lấy tất cả issues
            project_key (str, optional): Mã dự án cần lọc

        Returns:
            list: Danh sách issues
        """
        if fields is None:
            fields = [
                "summary",
                "status",
                "assignee",
                "issuetype",
                "priority",
                "created",
                "updated",
            ]

        # Xây dựng JQL query
        jql = f"sprint = {sprint_id}"
        if project_key:
            jql += f" AND project = {project_key}"
        if status_names:
            status_clause = " OR ".join([f'status = "{s}"' for s in status_names])
            jql += f" AND ({status_clause})"

        all_issues = []
        start_at = 0
        page_size = 100  # Kích thước trang hợp lý cho mỗi request
        total_issues = None

        # Hiển thị thông báo ban đầu
        st.toast(f"Đang lấy issues cho sprint {sprint_id}...")

        # Lặp qua các trang kết quả
        while True:  # Bỏ kiểm tra max_issues để luôn lấy tất cả
            params = {
                "jql": jql,
                "fields": ",".join(fields),
                "maxResults": page_size,  # Luôn lấy đủ page_size cho mỗi request
                "startAt": start_at,
            }

            try:
                response = self.get("search", params=params)

                if not response or response.status_code != 200:
                    st.toast(
                        f"Không thể lấy issues cho sprint {sprint_id} ở trang {start_at//page_size + 1}. "
                        f"Response code: {response.status_code if response else 'N/A'}",
                        icon="⚠️",
                    )
                    break

                response_data = response.json()
                issues = response_data.get("issues", [])

                # Cập nhật tổng số issues nếu chưa có
                if total_issues is None:
                    total_issues = response_data.get("total", 0)
                    if total_issues == 0:
                        return []  # Không có issue nào

                    # Chỉ hiển thị thông tin tổng số issues một lần
                    if max_issues != -1 and total_issues > max_issues:
                        st.toast(
                            f"Tìm thấy {total_issues} issues, giới hạn lấy {max_issues}",
                            icon="ℹ️",
                        )
                    else:
                        st.toast(
                            f"Tìm thấy {total_issues} issues trong sprint", icon="ℹ️"
                        )

                if not issues:
                    # Hết issues để lấy
                    break

                all_issues.extend(issues)

                # Thông báo tiến trình
                if total_issues > 0:
                    percent = int(len(all_issues) / total_issues * 100)
                    if (
                        percent % 25 == 0 or len(all_issues) == total_issues
                    ):  # Chỉ thông báo ở 25%, 50%, 75%, 100%
                        st.toast(
                            f"Đã tải {len(all_issues)}/{total_issues} issues ({percent}%)",
                            icon="ℹ️",
                        )

                # Kiểm tra xem đã lấy hết issues chưa
                if start_at + len(issues) >= total_issues or len(issues) < page_size:
                    # Đã lấy tất cả hoặc không còn issue nào khác
                    break

                # Kiểm tra nếu đã lấy đủ số lượng theo giới hạn max_issues
                if max_issues != -1 and len(all_issues) >= max_issues:
                    break

                # Cập nhật startAt cho trang tiếp theo
                start_at += len(issues)

            except Exception as e:
                st.toast(
                    f"Lỗi khi lấy issues cho sprint {sprint_id}: {str(e)}", icon="🛑"
                )
                break

        # Thông báo kết quả
        if not all_issues:
            st.toast(f"Không tìm thấy issue nào trong sprint {sprint_id}", icon="⚠️")
        elif max_issues != -1 and total_issues and len(all_issues) < total_issues:
            st.toast(
                f"Đã lấy {len(all_issues)}/{total_issues} issues (giới hạn: {max_issues})",
                icon="⚠️",
            )
        else:
            st.toast(
                f"Đã lấy đầy đủ {len(all_issues)} issues từ sprint {sprint_id}",
                icon="✅",
            )

        # Giới hạn số lượng issues trả về nếu cần
        if max_issues != -1:
            all_issues = all_issues[:max_issues]

        st.toast(
            f"Hoàn thành! Đã lấy {len(all_issues)} issues cho sprint {sprint_id}",
            icon="✅",
        )

        return all_issues

    def get_sprint_report(self, board_id, sprint_id):
        """Get the sprint report for a sprint

        Args:
            board_id (int): The board ID
            sprint_id (int): The sprint ID

        Returns:
            dict: The sprint report data
        """
        # Lấy thông tin chi tiết của sprint
        sprint_response = self.get(
            f"sprint/{sprint_id}",
            use_agile_api=True,
        )

        if not sprint_response or sprint_response.status_code != 200:
            st.warning(f"Không thể lấy thông tin chi tiết của sprint {sprint_id}")
            return None

        sprint_data = sprint_response.json()

        # Lấy danh sách các issues trong sprint
        fields = [
            "summary",
            "status",
            "assignee",
            "issuetype",
            "priority",
            "created",
            "updated",
        ]
        issues = self.get_sprint_issues(sprint_id, fields=fields)

        # Tạo báo cáo tự định nghĩa
        custom_report = {
            "sprint": sprint_data,
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "status_counts": {},
                "type_counts": {},
                "assignee_counts": {},
            },
        }

        # Tổng hợp dữ liệu cho báo cáo
        for issue in issues:
            # Đếm theo trạng thái
            status_name = (
                issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            )
            custom_report["summary"]["status_counts"][status_name] = (
                custom_report["summary"]["status_counts"].get(status_name, 0) + 1
            )

            # Đếm theo loại issue
            issue_type = (
                issue.get("fields", {}).get("issuetype", {}).get("name", "Unknown")
            )
            custom_report["summary"]["type_counts"][issue_type] = (
                custom_report["summary"]["type_counts"].get(issue_type, 0) + 1
            )

            # Đếm theo người được assign
            assignee = issue.get("fields", {}).get("assignee", {})
            assignee_name = (
                assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
            )
            custom_report["summary"]["assignee_counts"][assignee_name] = (
                custom_report["summary"]["assignee_counts"].get(assignee_name, 0) + 1
            )

        return custom_report

    def get_active_sprint(self, project_key):
        """Get the active sprint for a project

        Args:
            project_key (str): The project key

        Returns:
            dict: The active sprint data or None
        """
        # Lấy tất cả các board của project
        params = {"projectKeyOrId": project_key}
        boards_response = self.get("board", params=params, use_agile_api=True)

        if not boards_response or boards_response.status_code != 200:
            return None

        boards = boards_response.json().get("values", [])

        # Lặp qua từng board để tìm sprint active
        for board in boards:
            board_id = board["id"]
            sprint_response = self.get(
                f"board/{board_id}/sprint",
                params={"state": "active"},
                use_agile_api=True,
            )

            if sprint_response and sprint_response.status_code == 200:
                sprints = sprint_response.json().get("values", [])
                if sprints:
                    return sprints[0]  # Trả về sprint active đầu tiên

        return None
