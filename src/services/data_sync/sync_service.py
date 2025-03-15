import streamlit as st
from src.services.jira_client import JiraClient
from src.services.mongodb_client import MongoDBClient, is_running_in_streamlit
from src.config.config import DEFAULT_PROJECT

from src.services.data_sync.folder_manager import ensure_data_dirs, clear_local_data
from src.services.data_sync.sprint_sync import (
    sync_all_sprints,
    get_sprint_info,
    get_sprint_date_range,
)
from src.services.data_sync.issue_sync import (
    sync_sprint_issues,
    get_default_issue_fields,
    process_issue_details,
    get_sprint_info_from_mongo,
    get_issues_from_mongo,
)


class DataSyncService:
    """Dịch vụ đồng bộ dữ liệu từ Jira về MongoDB"""

    def __init__(self):
        """Khởi tạo dịch vụ đồng bộ dữ liệu"""
        self.jira = JiraClient()
        ensure_data_dirs()
        self.mongo_client = MongoDBClient()

    def sync_all_sprints(self, project_key=DEFAULT_PROJECT, show_toast=True):
        """Đồng bộ tất cả các sprints của dự án

        Args:
            project_key (str): Mã dự án
            show_toast (bool): Hiển thị thông báo hay không

        Returns:
            list: Danh sách các sprints đã đồng bộ
        """
        return sync_all_sprints(self.jira, show_toast, project_key)

    def sync_sprint_issues(self, sprint_id, fields=None, with_progress=True):
        """Đồng bộ issues của một sprint

        Args:
            sprint_id (int): ID của sprint
            fields (list, optional): Danh sách các trường cần lấy
            with_progress (bool): Hiển thị tiến trình hay không

        Returns:
            list: Danh sách issues đã đồng bộ
        """
        return sync_sprint_issues(
            self.jira, self.mongo_client, sprint_id, None, fields, with_progress
        )

    def fix_missing_status(self, sprint_id):
        """Phương thức này đã bị vô hiệu hóa - chức năng cập nhật trạng thái không còn được hỗ trợ

        Args:
            sprint_id (int): ID của sprint

        Returns:
            tuple: (tổng số issue, 0, 0) - không còn thực hiện cập nhật
        """
        if is_running_in_streamlit():
            st.warning("Chức năng cập nhật trạng thái đã bị vô hiệu hóa")

        # Trả về tuple (total_issues, fixed_issues, error_issues)
        return (0, 0, 0)

    def get_local_sprints(self, project_key=DEFAULT_PROJECT):
        """Lấy danh sách sprints từ cache
        (Giữ nguyên tên phương thức để tương thích với code cũ, nhưng thực tế sử dụng session_state làm cache)

        Args:
            project_key (str): Mã dự án

        Returns:
            list: Danh sách các sprints
        """
        # Tạo cache trong session_state nếu chưa có
        cache_key = f"sprints_{project_key}"
        if cache_key not in st.session_state:
            # Đồng bộ mới từ Jira nếu chưa có trong cache
            sprints = self.jira.get_all_sprints(project_key)
            st.session_state[cache_key] = sprints
            return sprints

        return st.session_state[cache_key]

    def get_local_sprint_info(self, sprint_id):
        """Lấy thông tin sprint từ API Jira hoặc cache

        Args:
            sprint_id (int): ID của sprint

        Returns:
            dict: Thông tin của sprint
        """
        # Tạo cache trong session_state nếu chưa có
        cache_key = f"sprint_info_{sprint_id}"
        if cache_key not in st.session_state:
            sprint_info = get_sprint_info(self.jira, sprint_id)
            if sprint_info:
                st.session_state[cache_key] = sprint_info
            return sprint_info

        return st.session_state[cache_key]

    def get_local_sprint_issues(self, sprint_id):
        """Lấy danh sách issues của sprint từ MongoDB

        Args:
            sprint_id (int): ID của sprint

        Returns:
            list: Danh sách issues của sprint
        """
        # Chỉ lấy từ MongoDB
        if self.mongo_client.is_connected():
            mongo_issues = self.mongo_client.get_issues(sprint_id)
            if mongo_issues:
                return mongo_issues
            else:
                # Nếu không tìm thấy trong MongoDB, thông báo cần đồng bộ
                if is_running_in_streamlit():
                    st.warning(
                        f"Không tìm thấy dữ liệu Sprint {sprint_id} trong MongoDB. Vui lòng đồng bộ lại."
                    )
                return []
        else:
            # Thông báo không thể kết nối MongoDB
            if is_running_in_streamlit():
                st.error(
                    "Không thể kết nối đến MongoDB. Không có dữ liệu issues để hiển thị."
                )
            return []

    def clear_local_data(self):
        """Xóa tất cả dữ liệu local nếu có thể không cần thiết"""

        # Tạo hàm callback để xác nhận từ người dùng
        def confirm_callback():
            if is_running_in_streamlit():
                st.warning(
                    "Không cần thiết phải xóa dữ liệu local - Không còn lưu dữ liệu vào local nữa"
                )
                confirm = st.button("Vẫn muốn xóa dữ liệu local (nếu có)")
                return confirm
            return True

        result = clear_local_data(confirm_callback)

        if result and is_running_in_streamlit():
            st.toast("Đã xóa tất cả dữ liệu local", icon="✅")

        return result

    def get_issue_status_change_date(self, issue_key, target_status="Dev Done"):
        """Lấy thời gian gần nhất issue chuyển sang trạng thái cụ thể

        Args:
            issue_key (str): Mã issue
            target_status (str): Trạng thái cần lấy thời gian (mặc định là "Dev Done")

        Returns:
            str: Thời gian chuyển trạng thái, hoặc None nếu không có
        """
        try:
            # Lấy changelog từ API Jira
            response = self.jira.get(f"issue/{issue_key}?expand=changelog")
            changelog_data = response.json().get("changelog", {})

            # Lấy lịch sử thay đổi
            histories = changelog_data.get("histories", [])

            # Danh sách các trạng thái thử tìm theo thứ tự ưu tiên
            statuses_to_check = [target_status]

            # Nếu trạng thái ban đầu là "Dev Done" và không tìm thấy, thử các trạng thái khác
            if target_status == "Dev Done":
                statuses_to_check.extend(["Test Done", "Deployed", "Done"])

            # Tìm kiếm qua các trạng thái theo thứ tự
            for status in statuses_to_check:
                # Duyệt qua lịch sử thay đổi theo thứ tự từ mới nhất đến cũ nhất
                for history in reversed(histories):
                    created_date = history.get("created")
                    items = history.get("items", [])

                    # Tìm thay đổi trạng thái
                    for item in items:
                        if (
                            item.get("field") == "status"
                            and item.get("toString") == status
                        ):
                            return created_date

            return None
        except Exception as e:
            if is_running_in_streamlit():
                st.error(
                    f"Lỗi khi lấy thời gian chuyển trạng thái cho issue {issue_key}: {str(e)}"
                )
            return None
