import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import from src modules
from src.config.config import (
    APP_TITLE,
    APP_LAYOUT,
    SIDEBAR_STATE,
    DEFAULT_TIMEZONE,
    DEFAULT_PROJECT,
    TAILWIND_TABLE_CSS,
)
from src.services.jira_client import JiraClient
from src.utils.date_utils import get_current_time

# Thiết lập cấu hình trang
st.set_page_config(
    page_title="Kế Hoạch Sprint | Jira Analytics",
    page_icon="📈",
    layout=APP_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)


class SprintStatService:
    """Dịch vụ thống kê Sprint"""

    def __init__(self, project_key=DEFAULT_PROJECT):
        """Khởi tạo dịch vụ thống kê Sprint

        Args:
            project_key (str, optional): Mã dự án Jira
        """
        self.jira = JiraClient()
        self.project_key = project_key

    def get_project_sprints(self, project_key=None):
        """Lấy danh sách tất cả các sprint của dự án

        Args:
            project_key (str, optional): Mã dự án để ghi đè mặc định

        Returns:
            list: Danh sách các sprint
        """
        if project_key is None:
            project_key = self.project_key

        # Lấy tất cả sprint từ tất cả các board của dự án
        all_sprints = self.jira.get_all_sprints(project_key)

        # Sắp xếp theo startDate (nếu có) hoặc tên
        return sorted(
            all_sprints,
            key=lambda s: s.get("startDate", s.get("name", "")),
            reverse=True,  # Sắp xếp từ mới đến cũ
        )

    def get_sprint_issues(self, sprint_id, fields=None):
        """Lấy danh sách issue của sprint

        Args:
            sprint_id (int): ID của sprint
            fields (list, optional): Danh sách các trường cần lấy

        Returns:
            list: Danh sách các issue trong sprint
        """
        if fields is None:
            fields = [
                "summary",
                "issuetype",
                "priority",
                "assignee",
                "status",
                "customfield_10016",  # Story Points
                "timeoriginalestimate",
                "timeestimate",
                "timespent",
                "created",
                "subtasks",  # Thêm trường subtasks để kiểm tra có subtasks không
            ]

        # Lấy tất cả issues của sprint
        return self.jira.get_sprint_issues(sprint_id, fields=fields)

    def calculate_sprint_stats(self, sprint_issues):
        """Tính toán thống kê cho sprint

        Args:
            sprint_issues (list): Danh sách các issue trong sprint

        Returns:
            dict: Thống kê của sprint
        """
        stats = {
            "total_issues": len(sprint_issues),
            "by_status": {},
            "by_assignee": {},
            "total_hours_original": 0,
            "total_hours_remaining": 0,
            "total_hours_spent": 0,
        }

        assignee_issues = {}
        assignee_hours_original = {}
        assignee_hours_remaining = {}
        assignee_hours_spent = {}

        for issue in sprint_issues:
            fields = issue.get("fields", {})

            # Thống kê theo trạng thái
            status = fields.get("status", {}).get("name", "Unknown")
            if status not in stats["by_status"]:
                stats["by_status"][status] = 0
            stats["by_status"][status] += 1

            # Thông tin assignee
            assignee = fields.get("assignee", {})
            assignee_name = (
                assignee.get("displayName", "Chưa gán") if assignee else "Chưa gán"
            )

            # Khởi tạo nếu chưa có
            if assignee_name not in assignee_issues:
                assignee_issues[assignee_name] = 0
                assignee_hours_original[assignee_name] = 0
                assignee_hours_remaining[assignee_name] = 0
                assignee_hours_spent[assignee_name] = 0

            # Đếm số issue
            assignee_issues[assignee_name] += 1

            # Tính giờ dự kiến từ thời gian ước tính hoặc story points
            time_original = fields.get("timeoriginalestimate", 0)
            story_points = fields.get("customfield_10016", 0)
            hours_original = 0

            if time_original:
                # Sử dụng thời gian ước tính nếu có
                hours_original = time_original / 3600
            elif story_points:
                # Nếu không có thời gian ước tính nhưng có story points,
                # quy đổi 1 SP = 1 giờ
                hours_original = story_points

            stats["total_hours_original"] += hours_original
            assignee_hours_original[assignee_name] += hours_original

            # Thời gian còn lại
            time_remaining = fields.get("timeestimate", 0)
            if time_remaining:
                hours_remaining = time_remaining / 3600
                stats["total_hours_remaining"] += hours_remaining
                assignee_hours_remaining[assignee_name] += hours_remaining
            elif hours_original and not fields.get("timespent"):
                # Nếu không có timeestimate và không có timespent,
                # dùng giờ ước tính ban đầu làm thời gian còn lại
                hours_remaining = hours_original
                stats["total_hours_remaining"] += hours_remaining
                assignee_hours_remaining[assignee_name] += hours_remaining

            # Thời gian đã dùng
            time_spent = fields.get("timespent", 0)
            if time_spent:
                hours_spent = time_spent / 3600
                stats["total_hours_spent"] += hours_spent
                assignee_hours_spent[assignee_name] += hours_spent

        # Tổng hợp thông tin theo assignee
        for assignee in assignee_issues:
            stats["by_assignee"][assignee] = {
                "issues": assignee_issues[assignee],
                "hours_original": assignee_hours_original[assignee],
                "hours_remaining": assignee_hours_remaining[assignee],
                "hours_spent": assignee_hours_spent[assignee],
            }

        return stats

    def get_next_sprint(self, project_key=None):
        """Lấy sprint tiếp theo (future sprint gần nhất hoặc active sprint)

        Args:
            project_key (str, optional): Mã dự án để ghi đè mặc định

        Returns:
            dict: Thông tin sprint tiếp theo hoặc None nếu không tìm thấy
        """
        if project_key is None:
            project_key = self.project_key

        # Lấy tất cả sprints
        all_sprints = self.get_project_sprints(project_key)

        if not all_sprints:
            return None

        # Tìm future sprints và active sprints
        future_sprints = [s for s in all_sprints if s.get("state") == "future"]
        active_sprints = [s for s in all_sprints if s.get("state") == "active"]

        # Ưu tiên future sprint gần nhất (sắp xếp từ mới đến cũ)
        if future_sprints:
            # Lưu ý: all_sprints đã được sắp xếp theo startDate (nếu có)
            return future_sprints[0]

        # Nếu không có future sprint, lấy active sprint
        if active_sprints:
            return active_sprints[0]

        # Nếu không có cả future và active, lấy sprint đầu tiên
        return all_sprints[0]

    def get_target_capacity_from_sprint_name(
        self, sprint_name, team_members_count=None
    ):
        """Tính tổng capacity dựa trên tên sprint (tách số)

        Args:
            sprint_name (str): Tên sprint
            team_members_count (int, optional): Số lượng thành viên team (không còn sử dụng)

        Returns:
            tuple: (số trong tên sprint, số ngày làm việc, số giờ mỗi ngày)
        """
        # Tách số từ tên sprint
        numbers = re.findall(r"\d+", sprint_name)
        if not numbers:
            # Không tìm thấy số, mặc định dùng 5 ngày làm việc
            return (None, 5, 8)

        sprint_number = int(numbers[0])

        # Tính số ngày làm việc dựa trên số chẵn/lẻ
        work_days = 5 if sprint_number % 2 == 0 else 6  # Chẵn: 5 ngày, lẻ: 6 ngày
        hours_per_day = 8

        return (sprint_number, work_days, hours_per_day)


def display_sprint_stats():
    """Hiển thị thống kê sprint"""

    st.title("📊 Thống Kê Kế Hoạch Sprint")

    # Khởi tạo các giá trị trong session_state nếu chưa có
    if "selected_sprint_id" not in st.session_state:
        st.session_state.selected_sprint_id = None
    if "selected_project" not in st.session_state:
        st.session_state.selected_project = None
    if "sprint_issues" not in st.session_state:
        st.session_state.sprint_issues = None
    if "non_project_count" not in st.session_state:
        st.session_state.non_project_count = 0
    if "excluded_count" not in st.session_state:
        st.session_state.excluded_count = 0

    # Khởi tạo dịch vụ
    stat_service = SprintStatService()

    # Nút tải lại dữ liệu ở đầu trang
    reload_button = st.button("🔄 Tải lại dữ liệu", help="Tải lại dữ liệu mới nhất từ Jira")
    
    # Sidebar cho cấu hình
    st.sidebar.header("Cấu hình")

    # Chọn dự án
    projects = stat_service.jira.get_all_projects()
    project_options = {p["key"]: p["name"] for p in projects}

    selected_project = st.sidebar.selectbox(
        "Chọn dự án",
        options=list(project_options.keys()),
        format_func=lambda x: f"{x} - {project_options.get(x, '')}",
        index=(
            list(project_options.keys()).index(DEFAULT_PROJECT)
            if DEFAULT_PROJECT in project_options
            else 0
        ),
    )

    # Cập nhật dự án được chọn
    stat_service.project_key = selected_project

    # Lấy danh sách sprint
    sprints = stat_service.get_project_sprints(selected_project)

    if not sprints:
        st.warning(f"Không tìm thấy sprint nào cho dự án {selected_project}")
        return

    # Tìm sprint tiếp theo để chọn mặc định
    next_sprint = stat_service.get_next_sprint(selected_project)

    # Chọn sprint để phân tích
    sprint_options = {s["id"]: s["name"] for s in sprints}

    # Xác định index mặc định cho selectbox
    default_index = 0  # Mặc định là sprint đầu tiên
    if next_sprint:
        try:
            default_index = list(sprint_options.keys()).index(next_sprint["id"])
        except (ValueError, KeyError):
            pass

    selected_sprint_id = st.sidebar.selectbox(
        "Chọn Sprint",
        options=list(sprint_options.keys()),
        format_func=lambda x: f"{sprint_options.get(x, '')} (ID: {x})",
        index=default_index,
    )

    # Lấy thông tin chi tiết của sprint đã chọn
    selected_sprint = next((s for s in sprints if s["id"] == selected_sprint_id), None)

    if not selected_sprint:
        st.error("Không thể tìm thấy thông tin sprint đã chọn")
        return

    # Hiển thị thông tin cơ bản của sprint
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Thông tin Sprint")
        st.info(f"**Tên Sprint:** {selected_sprint.get('name')}")

        # Ngày bắt đầu và kết thúc
        start_date = selected_sprint.get("startDate")
        end_date = selected_sprint.get("endDate")
        state = selected_sprint.get("state", "")

        if start_date:
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            st.info(f"**Ngày bắt đầu:** {start_date.strftime('%d/%m/%Y')}")

        if end_date:
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            st.info(f"**Ngày kết thúc:** {end_date.strftime('%d/%m/%Y')}")

        st.info(f"**Trạng thái:** {state.capitalize()}")

        # Tính toán target capacity dựa trên tên sprint
        # Lấy số lượng thành viên có issue trong sprint
        active_members_count = (
            len(stats["by_assignee"].keys()) if "stats" in locals() else 0
        )

        # Tính thời gian mục tiêu
        sprint_number, work_days, hours_per_day = (
            stat_service.get_target_capacity_from_sprint_name(
                selected_sprint.get("name", "")
            )
        )

        # Hiển thị định mức làm việc (không phụ thuộc số người)
        if sprint_number is not None:
            st.info(
                f"**Định mức làm việc:** {work_days} ngày × {hours_per_day} giờ/ngày"
            )
        else:
            st.info(f"**Định mức làm việc:** 5 ngày × 8 giờ/ngày")

        # Tính tổng giờ mục tiêu cho team
        target_hours = work_days * hours_per_day * active_members_count

    # Lấy và hiển thị thống kê issues của sprint
    def get_and_filter_sprint_issues(sprint_id, project_key):
        """Lấy và lọc dữ liệu issues từ Jira"""
        # Lấy issues từ sprint
        sprint_issues = stat_service.get_sprint_issues(sprint_id)

        if not sprint_issues:
            return None, 0, 0
            
        # Lọc các issue không thuộc dự án hiện tại
        project_issues = []
        non_project_count = 0
        
        for issue in sprint_issues:
            # Kiểm tra dự án của issue
            issue_key = issue.get("key", "")
            if issue_key.startswith(project_key + "-"):
                project_issues.append(issue)
            else:
                non_project_count += 1
        
        # Lọc các issue không hợp lệ
        excluded_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]
        filtered_issues = []
        excluded_count = 0

        for issue in project_issues:
            fields = issue.get("fields", {})

            # Kiểm tra loại issue
            issue_type = fields.get("issuetype", {}).get("name", "")
            if issue_type.lower() == "epic":
                excluded_count += 1
                continue

            # Kiểm tra trạng thái
            status = fields.get("status", {}).get("name", "")
            if status in excluded_statuses:
                excluded_count += 1
                continue

            # Kiểm tra có subtasks không
            subtasks = fields.get("subtasks", [])
            if subtasks and len(subtasks) > 0:
                excluded_count += 1
                continue

            # Thêm vào danh sách đã lọc
            filtered_issues.append(issue)
            
        return filtered_issues, non_project_count, excluded_count
    
    # Kiểm tra và tải dữ liệu mới nếu cần
    need_reload = (
        reload_button or 
        st.session_state.sprint_issues is None or
        st.session_state.selected_sprint_id != selected_sprint_id or
        st.session_state.selected_project != selected_project
    )
    
    if need_reload:
        with st.spinner("Đang tải dữ liệu issues..."):
            try:
                filtered_issues, non_project_count, excluded_count = get_and_filter_sprint_issues(
                    selected_sprint_id, selected_project
                )
                
                # Lưu vào session state để sử dụng lại
                st.session_state.sprint_issues = filtered_issues
                st.session_state.non_project_count = non_project_count
                st.session_state.excluded_count = excluded_count
                st.session_state.selected_sprint_id = selected_sprint_id
                st.session_state.selected_project = selected_project
            except Exception as e:
                st.error(f"Lỗi khi tải dữ liệu: {str(e)}")
                return
    else:
        # Sử dụng dữ liệu đã lưu trong session state
        filtered_issues = st.session_state.sprint_issues
        non_project_count = st.session_state.non_project_count
        excluded_count = st.session_state.excluded_count
    
    # Hiển thị thông báo
    if non_project_count > 0:
        st.info(f"Đã loại bỏ {non_project_count} issues không thuộc dự án {selected_project}")
    
    if excluded_count > 0:
        st.info(f"Đã loại bỏ {excluded_count} issues không phù hợp (Epic, có subtasks, hoặc đã hoàn thành)")
    
    # Kiểm tra nếu không có issues hợp lệ
    if not filtered_issues:
        st.warning(f"Sprint {selected_sprint.get('name')} không có issues hợp lệ sau khi lọc")
        return
    
    # Sử dụng issues đã lọc
    sprint_issues = filtered_issues

    # Tính toán thống kê
    stats = stat_service.calculate_sprint_stats(sprint_issues)

    # Hiển thị tổng quan
    with col2:
        st.subheader("Tổng Quan")

        # Metrics
        st.metric("Tổng số issues", stats["total_issues"])

        # Tính toán target capacity nếu chưa có
        if "target_hours" not in locals():
            active_members_count = len(stats["by_assignee"].keys())
            sprint_number, work_days, hours_per_day = (
                stat_service.get_target_capacity_from_sprint_name(
                    selected_sprint.get("name", "")
                )
            )
            target_hours = work_days * hours_per_day * active_members_count

        # Tính tỷ lệ hoàn thành (vẫn tính nhưng không hiển thị)
        completion_rate = (
            (stats["total_hours_original"] / target_hours) * 100
            if target_hours > 0
            else 0
        )
        remaining_rate = (
            (stats["total_hours_remaining"] / target_hours) * 100
            if target_hours > 0
            else 0
        )

        # Hiển thị các chỉ số thời gian trên cùng một hàng
        time_col1, time_col2, time_col3 = st.columns(3)
        with time_col1:
            st.metric("Dự kiến (giờ)", f"{stats['total_hours_original']:.1f}h")
        with time_col2:
            st.metric("Đã est (giờ)", f"{stats['total_hours_remaining']:.1f}h")
        with time_col3:
            st.metric("Đã có log (giờ)", f"{stats['total_hours_spent']:.1f}h")

    # Hiển thị phân bổ theo người được gán
    st.subheader("Thống kê theo người được gán")

    # Tính toán thời gian mục tiêu cho mỗi người
    if "average_target_per_person" not in locals():
        sprint_number, work_days, hours_per_day = (
            stat_service.get_target_capacity_from_sprint_name(
                selected_sprint.get("name", "")
            )
        )
        average_target_per_person = work_days * hours_per_day

    # Chuyển slider từ dạng % sang dạng số giờ
    max_hours = work_days * hours_per_day  # Số giờ làm việc tối đa trong tuần
    adjusted_target = st.slider(
        "Điều chỉnh mục tiêu (giờ)",
        min_value=0,
        max_value=max_hours,
        value=max_hours,
        step=4,
        help="Điều chỉnh số giờ mục tiêu làm việc cho mỗi người",
    )

    # Tính toán phần trăm tương ứng để hiển thị
    if average_target_per_person > 0:
        target_percentage = int((adjusted_target / average_target_per_person) * 100)
    else:
        target_percentage = 100

    st.info(
        f"Mục tiêu gốc: {average_target_per_person:.1f}h/người | Mục tiêu điều chỉnh: {adjusted_target:.1f}h/người ({target_percentage}%)"
    )

    # Tạo dataframe cho bảng assignee
    assignee_data = []

    for assignee, data in stats["by_assignee"].items():
        # Tính % so với mục tiêu tùy chỉnh
        target_percentage_value = (
            (data["hours_remaining"] / adjusted_target * 100)
            if adjusted_target > 0
            else 0
        )
        
        # Tính số giờ còn trống (free hours)
        free_hours = adjusted_target - data["hours_remaining"]

        assignee_data.append(
            {
                "Người được gán": assignee,
                "Số issues": data["issues"],
                "Dự kiến (giờ)": f"{data['hours_original']:.1f}h",
                "Đã có log (giờ)": f"{data['hours_spent']:.1f}h",
                "Đã est (giờ)": f"{data['hours_remaining']:.1f}h",
                "Giờ trống": f"{free_hours:.1f}h",
                "% so với mục tiêu": f"{target_percentage_value:.1f}%",
                "% mục tiêu (số)": target_percentage_value,  # Cột ẩn dùng để định dạng màu
            }
        )

    # Sắp xếp theo số issues giảm dần
    assignee_data = sorted(assignee_data, key=lambda x: x["Số issues"], reverse=True)

    if assignee_data:
        df_assignee = pd.DataFrame(assignee_data)

        # Áp dụng định dạng màu nền xanh cho các hàng có % so với mục tiêu >= 80%
        def highlight_rows(row):
            # Tạo chuỗi CSS trống cho tất cả các cột
            default = ""
            target_value = row["% mục tiêu (số)"]

            # Nếu giá trị % so với mục tiêu >= 80%, bôi xanh toàn bộ hàng
            if target_value >= 80:
                return ["background-color: #d4edda"] * len(row)  # Màu xanh lá nhạt
            return [default] * len(row)

        # Tạo một bản sao của DataFrame ban đầu (có chứa tất cả các cột cần thiết cho việc định dạng)
        df_display = df_assignee.copy()

        # Áp dụng định dạng trên DataFrame ban đầu
        styled_original = df_assignee.style.apply(highlight_rows, axis=1)

        # Tạo một DataFrame mới không có cột cần ẩn
        df_display = df_assignee.drop(columns=["% mục tiêu (số)"])

        # Định dạng hàm highlight mới cho DataFrame đã loại bỏ cột
        def highlight_rows_display(row):
            value_dict = row.to_dict()
            target_value = float(value_dict["% so với mục tiêu"].replace("%", ""))

            # Nếu giá trị % so với mục tiêu >= 80%, bôi xanh toàn bộ hàng
            if target_value >= 80:
                return ["background-color: #d4edda"] * len(row)  # Màu xanh lá nhạt
            return [""] * len(row)

        # Áp dụng định dạng cho DataFrame đã loại bỏ cột
        styled_df = df_display.style.apply(highlight_rows_display, axis=1)

        st.dataframe(styled_df, use_container_width=True)

        # Vẽ biểu đồ phân bổ công việc
        try:
            # Chuẩn bị dữ liệu cho biểu đồ
            chart_data = []
            for assignee, data in stats["by_assignee"].items():
                free_hours = adjusted_target - data["hours_remaining"]
                chart_data.append(
                    {
                        "Người được gán": assignee,
                        "Số giờ dự kiến": data["hours_original"],
                        "Đã est (giờ)": data["hours_remaining"],
                        "Số giờ đã có log": data["hours_spent"],
                        "Giờ trống": free_hours,
                    }
                )

            if chart_data:
                df_chart = pd.DataFrame(chart_data)

                # Vẽ biểu đồ cột so sánh ước tính và còn lại
                fig = go.Figure()

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Số giờ dự kiến"],
                        name="Dự kiến",
                        marker_color="rgb(55, 83, 109)",
                        visible="legendonly",  # Ẩn mặc định
                    )
                )

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Đã est (giờ)"],
                        name="Đã est",
                        marker_color="rgb(26, 118, 255)",
                        visible=True,  # Hiển thị mặc định
                    )
                )

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Giờ trống"],
                        name="Giờ trống",
                        marker_color="rgb(46, 204, 113)",
                        visible="legendonly",  # Ẩn mặc định
                    )
                )

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Số giờ đã có log"],
                        name="Đã có log",
                        marker_color="rgb(219, 64, 82)",
                        visible="legendonly",  # Ẩn mặc định, chỉ hiện khi bấm vào legend
                    )
                )

                # Thêm đường target line gốc (đổi thành dạng "legendonly")
                fig.add_trace(
                    go.Scatter(
                        x=df_chart["Người được gán"],
                        y=[average_target_per_person] * len(df_chart),
                        mode="lines",
                        name=f"Mục tiêu gốc ({average_target_per_person:.1f}h/người)",
                        line=dict(color="gray", width=2, dash="dash"),
                        visible="legendonly",  # Ẩn mặc định
                    )
                )

                # Thêm đường target line được điều chỉnh
                fig.add_trace(
                    go.Scatter(
                        x=df_chart["Người được gán"],
                        y=[adjusted_target] * len(df_chart),
                        mode="lines",
                        name=f"Mục tiêu điều chỉnh ({adjusted_target:.1f}h/người - {target_percentage}%)",
                        line=dict(color="red", width=2, dash="dash"),
                    )
                )

                fig.update_layout(
                    title="Phân bổ thời gian làm việc theo người được gán<br><sup>(Bấm vào chú thích để hiển thị/ẩn các loại thời gian)</sup>",
                    xaxis=dict(tickfont=dict(size=12)),
                    yaxis=dict(
                        title=dict(text="Số giờ", font=dict(size=14)),
                        tickfont=dict(size=12),
                    ),
                    legend=dict(
                        x=1.02,  # Đặt legend bên ngoài biểu đồ, phía bên phải
                        y=1.0,  # Căn chỉnh theo phía trên cùng
                        xanchor="left",  # Neo bên trái của legend
                        yanchor="top",  # Neo phía trên của legend
                        orientation="v",  # Sắp xếp theo chiều dọc (v thay vì vertical)
                        bgcolor="rgba(255, 255, 255, 0.8)",  # Nền hơi đục để dễ đọc
                        bordercolor="rgba(0, 0, 0, 0.1)",  # Viền mỏng
                        borderwidth=1,  # Độ dày viền
                        font=dict(size=12),  # Kích thước font
                    ),
                    barmode="group",
                    bargap=0.15,
                    bargroupgap=0.1,
                    margin=dict(r=150),  # Tăng lề bên phải để có chỗ cho legend
                )

                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Lỗi khi tạo biểu đồ: {str(e)}")

    # Hiển thị danh sách issues
    with st.expander("Xem danh sách issues của sprint", expanded=False):
        # Tạo dataframe hiển thị
        issue_data = []
        for issue in sprint_issues:
            # Trích xuất thông tin
            fields = issue.get("fields", {})

            # Assignee
            assignee = fields.get("assignee", {})
            assignee_name = (
                assignee.get("displayName", "Chưa gán") if assignee else "Chưa gán"
            )

            # Thời gian dự kiến (từ story points hoặc timeoriginalestimate)
            time_original = fields.get("timeoriginalestimate")
            story_points = fields.get("customfield_10016")
            time_original_hours = None

            if time_original:
                time_original_hours = time_original / 3600
            elif story_points:
                time_original_hours = story_points

            # Thời gian còn lại
            time_remaining = fields.get("timeestimate")
            time_remaining_hours = time_remaining / 3600 if time_remaining else None

            if (
                not time_remaining_hours
                and time_original_hours
                and not fields.get("timespent")
            ):
                time_remaining_hours = time_original_hours

            # Thời gian đã dùng
            time_spent = fields.get("timespent")
            time_spent_hours = time_spent / 3600 if time_spent else None

            issue_data.append(
                {
                    "Key": issue.get("key"),
                    "Loại": fields.get("issuetype", {}).get("name", ""),
                    "Tiêu đề": fields.get("summary", ""),
                    "Trạng thái": fields.get("status", {}).get("name", ""),
                    "Người được gán": assignee_name,
                    "Dự kiến (giờ)": (
                        f"{time_original_hours:.1f}h" if time_original_hours else ""
                    ),
                    "Đã est (giờ)": (
                        f"{time_remaining_hours:.1f}h" if time_remaining_hours else ""
                    ),
                    "Đã có log (giờ)": (
                        f"{time_spent_hours:.1f}h" if time_spent_hours else ""
                    ),
                }
            )

        if issue_data:
            df_issues = pd.DataFrame(issue_data)
            
            # Container cho bộ lọc và thanh tìm kiếm
            filter_container = st.container()
            
            with filter_container:
                # Thêm thanh tìm kiếm
                search_col, est_col, assigned_col = st.columns(3)
                
                with search_col:
                    search_query = st.text_input("🔍 Tìm kiếm", placeholder="Nhập từ khóa...")
                    
                with est_col:
                    show_no_estimate = st.checkbox(
                        "Hiển thị issues chưa có est", value=True
                    )
                    
                with assigned_col:
                    # Lấy danh sách tất cả người được gán
                    assignees = df_issues["Người được gán"].unique().tolist()
                    assignees.insert(0, "Tất cả")  # Thêm lựa chọn "Tất cả" vào đầu danh sách
                    
                    selected_assignee = st.selectbox(
                        "Lọc theo người được gán",
                        options=assignees,
                        index=0
                    )
            
            # Áp dụng bộ lọc
            filtered_df = df_issues.copy()
            
            # Lọc theo từ khóa tìm kiếm
            if search_query:
                mask = filtered_df.apply(
                    lambda row: any(
                        search_query.lower() in str(val).lower() 
                        for val in row.values
                    ), 
                    axis=1
                )
                filtered_df = filtered_df[mask]

            if not show_no_estimate:
                # Lọc chỉ giữ lại các issue có thời gian est
                filtered_df = filtered_df[filtered_df["Đã est (giờ)"] != ""]
                
            # Lọc theo người được gán
            if selected_assignee != "Tất cả":
                filtered_df = filtered_df[filtered_df["Người được gán"] == selected_assignee]

            # Hiển thị số lượng issues sau khi lọc
            st.caption(f"Hiển thị {len(filtered_df)} trên tổng số {len(df_issues)} issues")
            
            # Hiển thị dataframe đã lọc
            st.dataframe(filtered_df, use_container_width=True)


def main():
    # Hiển thị CSS cho bảng
    st.markdown(TAILWIND_TABLE_CSS, unsafe_allow_html=True)

    # Hiển thị thống kê sprint
    display_sprint_stats()


if __name__ == "__main__":
    main()
