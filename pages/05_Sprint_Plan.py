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
    page_title="Kế Hoạch Sprint",
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

    # Khởi tạo dịch vụ
    stat_service = SprintStatService()

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
        format_func=lambda x: sprint_options.get(x, ""),
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
    with st.spinner("Đang tải dữ liệu issues..."):
        sprint_issues = stat_service.get_sprint_issues(selected_sprint_id)

        if not sprint_issues:
            st.warning(f"Sprint {selected_sprint.get('name')} không có issues nào")
            return

        # Lọc các issue không hợp lệ
        excluded_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]
        filtered_issues = []
        excluded_count = 0

        for issue in sprint_issues:
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

        # Hiển thị thông tin số lượng issue bị loại
        if excluded_count > 0:
            st.info(
                f"Đã loại bỏ {excluded_count} issues không phù hợp (Epic, có subtasks, hoặc đã hoàn thành)"
            )

        # Sử dụng danh sách issues đã lọc
        sprint_issues = filtered_issues

        if not sprint_issues:
            st.warning(
                f"Sprint {selected_sprint.get('name')} không có issues hợp lệ sau khi lọc"
            )
            return

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
            st.metric("Còn lại (giờ)", f"{stats['total_hours_remaining']:.1f}h")
        with time_col3:
            st.metric("Đã dùng (giờ)", f"{stats['total_hours_spent']:.1f}h")

    # Hiển thị phân bổ theo người được gán
    st.subheader("Thống kê theo người được gán")

    # Tạo dataframe cho bảng assignee
    assignee_data = []

    for assignee, data in stats["by_assignee"].items():
        assignee_data.append(
            {
                "Người được gán": assignee,
                "Số issues": data["issues"],
                "Dự kiến (giờ)": f"{data['hours_original']:.1f}h",
                "Còn lại (giờ)": f"{data['hours_remaining']:.1f}h",
                "Đã dùng (giờ)": f"{data['hours_spent']:.1f}h",
            }
        )

    # Sắp xếp theo số issues giảm dần
    assignee_data = sorted(assignee_data, key=lambda x: x["Số issues"], reverse=True)

    if assignee_data:
        df_assignee = pd.DataFrame(assignee_data)
        st.dataframe(df_assignee, use_container_width=True)

        # Vẽ biểu đồ phân bổ công việc
        try:
            # Chuẩn bị dữ liệu cho biểu đồ
            chart_data = []
            for assignee, data in stats["by_assignee"].items():
                chart_data.append(
                    {
                        "Người được gán": assignee,
                        "Số giờ dự kiến": data["hours_original"],
                        "Số giờ còn lại": data["hours_remaining"],
                        "Số giờ đã dùng": data["hours_spent"],
                    }
                )

            if chart_data:
                df_chart = pd.DataFrame(chart_data)

                # Tính toán thời gian mục tiêu cho mỗi người
                sprint_number, work_days, hours_per_day = (
                    stat_service.get_target_capacity_from_sprint_name(
                        selected_sprint.get("name", "")
                    )
                )
                average_target_per_person = work_days * hours_per_day

                # Vẽ biểu đồ cột so sánh ước tính và còn lại
                fig = go.Figure()

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Số giờ dự kiến"],
                        name="Dự kiến",
                        marker_color="rgb(55, 83, 109)",
                        visible=True,  # Hiển thị mặc định
                    )
                )

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Số giờ còn lại"],
                        name="Còn lại",
                        marker_color="rgb(26, 118, 255)",
                        visible=True,  # Hiển thị mặc định
                    )
                )

                fig.add_trace(
                    go.Bar(
                        x=df_chart["Người được gán"],
                        y=df_chart["Số giờ đã dùng"],
                        name="Đã dùng",
                        marker_color="rgb(219, 64, 82)",
                        visible="legendonly",  # Ẩn mặc định, chỉ hiện khi bấm vào legend
                    )
                )

                # Thêm đường target line
                fig.add_trace(
                    go.Scatter(
                        x=df_chart["Người được gán"],
                        y=[average_target_per_person] * len(df_chart),
                        mode="lines",
                        name=f"Mục tiêu ({average_target_per_person:.1f}h/người)",
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
                        x=0,
                        y=1.0,
                        bgcolor="rgba(255, 255, 255, 0)",
                        bordercolor="rgba(255, 255, 255, 0)",
                    ),
                    barmode="group",
                    bargap=0.15,
                    bargroupgap=0.1,
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
                    "Còn lại (giờ)": (
                        f"{time_remaining_hours:.1f}h" if time_remaining_hours else ""
                    ),
                    "Đã dùng (giờ)": (
                        f"{time_spent_hours:.1f}h" if time_spent_hours else ""
                    ),
                }
            )

        if issue_data:
            df_issues = pd.DataFrame(issue_data)

            # Thêm bộ lọc
            filter_cols = st.columns(2)
            with filter_cols[0]:
                show_no_estimate = st.checkbox(
                    "Hiển thị issues chưa có thời gian dự kiến", value=True
                )
            with filter_cols[1]:
                show_no_remaining = st.checkbox(
                    "Hiển thị issues không còn thời gian còn lại", value=True
                )

            # Áp dụng bộ lọc
            filtered_df = df_issues.copy()

            if not show_no_estimate:
                # Lọc chỉ giữ lại các issue có thời gian dự kiến
                filtered_df = filtered_df[filtered_df["Dự kiến (giờ)"] != ""]

            if not show_no_remaining:
                # Lọc chỉ giữ lại các issue có thời gian còn lại
                filtered_df = filtered_df[filtered_df["Còn lại (giờ)"] != ""]

            # Hiển thị dataframe đã lọc
            st.dataframe(filtered_df, use_container_width=True)


def main():
    # Hiển thị CSS cho bảng
    st.markdown(TAILWIND_TABLE_CSS, unsafe_allow_html=True)

    # Hiển thị thống kê sprint
    display_sprint_stats()


if __name__ == "__main__":
    main()
