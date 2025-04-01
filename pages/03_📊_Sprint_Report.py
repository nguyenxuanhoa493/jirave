import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Set page configuration first
st.set_page_config(
    page_title="Báo Cáo Sprint | Jira Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import from src modules
from src.config.config import (
    APP_TITLE,
    APP_LAYOUT,
    SIDEBAR_STATE,
    DEFAULT_TIMEZONE,
    DEFAULT_PROJECT,
)
from src.services.jira_client import JiraClient
from src.services.mongodb_client import MongoDBClient


# Hàm để lấy trạng thái từ issue một cách an toàn
def safe_get_status(issue, field_name="status"):
    """Lấy trạng thái từ issue một cách an toàn

    Args:
        issue (dict): Dữ liệu issue
        field_name (str): Tên trường cần lấy (status hoặc current_status)

    Returns:
        str: Giá trị trạng thái hợp lệ
    """
    value = issue.get(field_name)

    # Kiểm tra kiểu dữ liệu và trả về chuỗi phù hợp
    if value is None:
        return ""
    elif isinstance(value, dict) and "name" in value:
        return value.get("name", "")
    elif isinstance(value, (int, float)):
        return str(value)
    elif value == "None" or value == "null":
        return ""
    else:
        return str(value)


class SprintReportService:
    """Service cho báo cáo sprint"""

    def __init__(self):
        """Khởi tạo service"""
        self.jira = JiraClient()
        self.mongo_client = MongoDBClient()

    def get_all_sprints(self, project_key=DEFAULT_PROJECT):
        """Lấy danh sách tất cả sprint từ API Jira

        Args:
            project_key (str): Mã dự án

        Returns:
            list: Danh sách các sprint
        """
        try:
            sprints = self.jira.get_all_sprints(project_key)
            if sprints:
                st.toast(f"Đã tải {len(sprints)} sprints từ Jira API!", icon="✅")
                return sprints
            else:
                st.warning(f"Không tìm thấy sprint nào cho dự án {project_key}")
                return []
        except Exception as e:
            st.error(f"Lỗi khi lấy danh sách sprint từ API: {str(e)}")
            return []

    def get_sprint_issues_from_mongo(self, sprint_id):
        """Lấy danh sách issues của sprint từ MongoDB

        Args:
            sprint_id (int): ID của sprint

        Returns:
            list: Danh sách issues của sprint từ MongoDB
        """
        if not self.mongo_client.is_connected():
            st.error("Không thể kết nối đến MongoDB!")
            return None

        issues = self.mongo_client.get_issues(sprint_id)
        return issues

    def get_sprint_info_from_mongo(self, sprint_id):
        """Lấy thông tin của sprint từ MongoDB

        Args:
            sprint_id (int): ID của sprint

        Returns:
            dict: Thông tin của sprint từ MongoDB, bao gồm updated_at
        """
        if not self.mongo_client.is_connected():
            st.error("Không thể kết nối đến MongoDB!")
            return None

        sprint_info = self.mongo_client.get_sprint_info(sprint_id)
        return sprint_info


def calculate_days_remaining(end_date_str):
    """Tính số ngày còn lại của sprint

    Args:
        end_date_str (str): Chuỗi ngày kết thúc sprint (định dạng ISO)

    Returns:
        int: Số ngày còn lại (âm nếu sprint đã kết thúc)
    """
    if not end_date_str:
        return None

    try:
        # Chuyển đổi thời gian kết thúc sprint sang đối tượng datetime với múi giờ
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))

        # Chuyển đổi sang múi giờ GMT+7
        vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        end_date = end_date.astimezone(vietnam_tz)

        # Lấy thời gian hiện tại theo múi giờ GMT+7
        now = datetime.now(vietnam_tz)

        # Tính số ngày còn lại
        days_remaining = (
            end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            - now.replace(hour=0, minute=0, second=0, microsecond=0)
        ).days

        return days_remaining
    except Exception as e:
        st.error(f"Lỗi khi tính số ngày còn lại: {str(e)}")
        return None


def calculate_sprint_progress(start_date_str, end_date_str):
    """Tính toán phần trăm tiến độ của sprint

    Args:
        start_date_str (str): Chuỗi ngày bắt đầu sprint (định dạng ISO)
        end_date_str (str): Chuỗi ngày kết thúc sprint (định dạng ISO)

    Returns:
        float: Phần trăm tiến độ (0-100), None nếu không tính được
    """
    if not start_date_str or not end_date_str:
        return None

    try:
        # Chuyển đổi thời gian sang đối tượng datetime với múi giờ
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))

        # Chuyển đổi sang múi giờ GMT+7
        vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        start_date = start_date.astimezone(vietnam_tz)
        end_date = end_date.astimezone(vietnam_tz)

        # Lấy thời gian hiện tại theo múi giờ GMT+7
        now = datetime.now(vietnam_tz)

        # Nếu chưa bắt đầu
        if now < start_date:
            return 0

        # Nếu đã kết thúc
        if now > end_date:
            return 100

        # Tính tổng thời gian của sprint
        total_duration = (end_date - start_date).total_seconds()

        # Tính thời gian đã trôi qua
        elapsed_duration = (now - start_date).total_seconds()

        # Tính phần trăm tiến độ
        progress = (elapsed_duration / total_duration) * 100

        return min(max(progress, 0), 100)  # Đảm bảo giá trị nằm trong khoảng 0-100
    except Exception as e:
        st.error(f"Lỗi khi tính tiến độ sprint: {str(e)}")
        return None


def calculate_burndown_data(
    filtered_issues, start_date, end_date, metric="issues", done_type="completed"
):
    """Tính toán dữ liệu cho Burn Down Chart

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
        start_date (datetime): Ngày bắt đầu sprint
        end_date (datetime): Ngày kết thúc sprint
        metric (str): Loại metric ('issues' hoặc 'time')
        done_type (str): Loại thời gian hoàn thành ('completed' hoặc 'dev_done_date')

    Returns:
        tuple: (dates, ideal_data, actual_data)
    """
    # Chuyển đổi start_date và end_date thành datetime object với timezone
    vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00")).astimezone(
        vietnam_tz
    )
    end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00")).astimezone(
        vietnam_tz
    )

    # Tạo danh sách các ngày từ start_date đến end_date
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    # Tính tổng số issue hoặc thời gian dự kiến
    if metric == "issues":
        total = len(filtered_issues)
    else:  # metric == 'time'
        total = sum(issue.get("time_estimate", 0) for issue in filtered_issues)

    # Tạo đường lý tưởng (ideal burndown)
    ideal_data = []
    days_total = len(dates)
    for i in range(days_total):
        ideal_remaining = total * (1 - i / (days_total - 1))
        ideal_data.append(ideal_remaining)

    # Tạo đường thực tế (actual burndown)
    actual_data = []
    for date in dates:
        if metric == "issues":
            # Đếm số issue chưa hoàn thành tại ngày này
            remaining = len(
                [
                    issue
                    for issue in filtered_issues
                    if issue.get(done_type)
                    in [None, "", "N/A"]  # Xử lý các giá trị không hợp lệ
                    or (
                        isinstance(issue.get(done_type), str)
                        and issue.get(done_type) != "N/A"
                        and datetime.strptime(
                            issue.get(done_type), "%d/%m/%Y %H:%M"
                        ).replace(tzinfo=vietnam_tz)
                        > date
                    )
                ]
            )
        else:  # metric == 'time'
            # Tính tổng thời gian của các issue chưa hoàn thành
            remaining = sum(
                issue.get("time_estimate", 0)
                for issue in filtered_issues
                if issue.get(done_type)
                in [None, "", "N/A"]  # Xử lý các giá trị không hợp lệ
                or (
                    isinstance(issue.get(done_type), str)
                    and issue.get(done_type) != "N/A"
                    and datetime.strptime(
                        issue.get(done_type), "%d/%m/%Y %H:%M"
                    ).replace(tzinfo=vietnam_tz)
                    > date
                )
            )
        actual_data.append(remaining)

    return dates, ideal_data, actual_data


def display_burndown_chart(filtered_issues, start_date, end_date):
    """Hiển thị Burn Down Chart

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
        start_date (str): Ngày bắt đầu sprint
        end_date (str): Ngày kết thúc sprint
    """
    st.subheader("Burn Down Chart")

    # Tạo các tùy chọn
    col1, col2 = st.columns(2)
    with col1:
        metric = st.selectbox(
            "Chọn metric",
            options=["issues", "time"],
            format_func=lambda x: (
                "Số lượng issue" if x == "issues" else "Thời gian dự kiến (giờ)"
            ),
        )
    with col2:
        done_type = st.selectbox(
            "Loại thời gian hoàn thành",
            options=["dev_done_date", "completed"],
            format_func=lambda x: (
                "Thời gian Dev Done"
                if x == "dev_done_date"
                else "Thời gian hoàn thành (Completed)"
            ),
        )

    # Tính toán dữ liệu cho biểu đồ
    dates, ideal_data, actual_data = calculate_burndown_data(
        filtered_issues, start_date, end_date, metric, done_type
    )

    # Tạo biểu đồ
    fig = go.Figure()

    # Thêm đường lý tưởng
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ideal_data,
            name="Lý tưởng",
            line=dict(color="gray", dash="dash"),
        )
    )

    # Thêm đường thực tế
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=actual_data,
            name="Thực tế",
            line=dict(color="blue"),
        )
    )

    # Cập nhật layout
    title = f"Burn Down Chart - {'Số lượng issue' if metric == 'issues' else 'Thời gian dự kiến'}"
    y_title = "Số lượng còn lại" if metric == "issues" else "Giờ còn lại"

    fig.update_layout(
        title=title,
        xaxis_title="Ngày",
        yaxis_title=y_title,
        hovermode="x unified",
        showlegend=True,
    )

    # Hiển thị biểu đồ
    st.plotly_chart(fig, use_container_width=True)


def display_status_chart(filtered_issues):
    """Hiển thị biểu đồ phân bố status

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
    """
    st.subheader("Phân bố trạng thái")

    # Tạo options trong cùng một hàng
    col1, col2 = st.columns(2)
    with col1:
        show_by_assignee = st.toggle("Hiển thị theo Assignee", value=False)
    with col2:
        metric = st.selectbox(
            "Hiển thị theo",
            options=["issues", "time", "sprint_time"],
            format_func=lambda x: (
                "Số lượng issue"
                if x == "issues"
                else (
                    "Thời gian dự kiến (giờ)"
                    if x == "time"
                    else "Thời gian đã làm trong sprint (giờ)"
                )
            ),
        )

    # Định nghĩa thứ tự các trạng thái
    status_order = [
        "To Do",
        "Reopen",
        "Close",
        "In Progress",
        "Dev Done",
        "Test Done",
        "Deployed",
        "Done",
    ]

    # Chuẩn bị dữ liệu
    if show_by_assignee:
        # Nhóm theo assignee và status
        data = {}
        for issue in filtered_issues:
            assignee = issue.get("assignee", "Không có assignee")
            status = issue.get("status", "Không có status")
            if assignee not in data:
                data[assignee] = {}
            if status not in data[assignee]:
                data[assignee][status] = 0
            # Tính theo metric được chọn
            if metric == "issues":
                data[assignee][status] += 1
            elif metric == "time":  # thời gian dự kiến
                data[assignee][status] += issue.get("time_estimate", 0)
            else:  # sprint_time - thời gian đã làm trong sprint
                data[assignee][status] += issue.get("sprint_time_spent", 0)

        # Lấy danh sách tất cả status có thể có và sắp xếp theo thứ tự định nghĩa
        all_statuses = set(
            status for assignee_data in data.values() for status in assignee_data.keys()
        )
        # Sắp xếp status theo thứ tự đã định nghĩa
        sorted_statuses = [s for s in status_order if s in all_statuses]
        # Thêm các status không nằm trong danh sách định nghĩa
        sorted_statuses.extend(
            sorted([s for s in all_statuses if s not in status_order])
        )

        # Tạo dữ liệu cho biểu đồ
        fig = go.Figure()
        for status in sorted_statuses:
            fig.add_trace(
                go.Bar(
                    name=status,
                    y=list(data.keys()),  # assignees là trục y
                    x=[data[assignee].get(status, 0) for assignee in data.keys()],
                    orientation="h",
                )
            )

        # Cập nhật layout
        fig.update_layout(
            barmode="stack",
            height=max(
                350, len(data) * 50
            ),  # Điều chỉnh chiều cao theo số lượng assignee
            yaxis={
                "categoryorder": "total ascending"
            },  # Sắp xếp theo tổng số issue/thời gian
            xaxis_title=(
                "Số lượng issue"
                if metric == "issues"
                else (
                    "Thời gian dự kiến (giờ)"
                    if metric == "time"
                    else "Thời gian đã làm trong sprint (giờ)"
                )
            ),
            margin=dict(l=200),  # Tăng margin bên trái để hiển thị tên assignee
        )

    else:
        # Nhóm theo status
        status_counts = {}
        for issue in filtered_issues:
            status = issue.get("status", "Không có status")
            if status not in status_counts:
                status_counts[status] = 0
            # Tính theo metric được chọn
            if metric == "issues":
                status_counts[status] += 1
            elif metric == "time":  # thời gian dự kiến
                status_counts[status] += issue.get("time_estimate", 0)
            else:  # sprint_time - thời gian đã làm trong sprint
                status_counts[status] += issue.get("sprint_time_spent", 0)

        # Lọc và sắp xếp status theo thứ tự đã định nghĩa
        sorted_statuses = [s for s in status_order if s in status_counts]
        # Thêm các status không nằm trong danh sách định nghĩa
        sorted_statuses.extend(
            sorted([s for s in status_counts.keys() if s not in status_order])
        )

        # Tạo dữ liệu cho biểu đồ
        fig = go.Figure()

        # Chỉ tạo một bar và stack các status
        for status in sorted_statuses:
            fig.add_trace(
                go.Bar(
                    name=status,
                    x=[status_counts[status]],
                    y=["Issues"],
                    orientation="h",
                )
            )

        # Cập nhật layout
        fig.update_layout(
            barmode="stack",
            height=300,  # Chiều cao cố định cho một bar
            xaxis_title=(
                "Số lượng issue"
                if metric == "issues"
                else (
                    "Thời gian dự kiến (giờ)"
                    if metric == "time"
                    else "Thời gian đã làm trong sprint (giờ)"
                )
            ),
            margin=dict(l=100),  # Margin bên trái
            showlegend=True,  # Hiển thị legend
            legend=dict(
                orientation="h",  # Legend nằm ngang
                yanchor="bottom",
                y=1.02,  # Đặt legend phía trên biểu đồ
                xanchor="right",
                x=1,
            ),
        )

    # Hiển thị biểu đồ
    st.plotly_chart(fig, use_container_width=True)


def display_distribution_charts(filtered_issues):
    """Hiển thị biểu đồ phân bố theo loại issue và customer

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
    """
    # Tạo layout 2 cột cho 2 biểu đồ
    dist_col1, dist_col2 = st.columns(2)

    with dist_col1:
        st.subheader(
            "Phân bố theo loại Issue", help="Phân bố số lượng issue theo từng loại"
        )
        # Tính toán số lượng theo loại issue
        issue_types = {}
        for issue in filtered_issues:
            issue_type = issue.get("issue_type", "Không xác định")
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        # Tạo biểu đồ
        fig_type = go.Figure(
            data=[
                go.Pie(
                    labels=list(issue_types.keys()),
                    values=list(issue_types.values()),
                    hole=0.4,
                    textposition="auto",
                    textinfo="percent+label",
                )
            ]
        )
        fig_type.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            annotations=[
                dict(
                    text=f"Tổng số: {sum(issue_types.values())}",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                    xanchor="center",
                    yanchor="middle",
                )
            ],
        )
        st.plotly_chart(fig_type, use_container_width=True)

    with dist_col2:
        st.subheader(
            "Phân bố theo Customer (Top 5)",
            help="Phân bố số lượng issue theo 5 khách hàng lớn nhất",
        )
        # Tính toán số lượng theo customer
        customers = {}
        for issue in filtered_issues:
            customer = issue.get("customer", "Không xác định")
            if customer != "N/A" and customer != "Không xác định":
                customers[customer] = customers.get(customer, 0) + 1

        # Lấy top 5 customer có số lượng issue nhiều nhất
        top_customers = dict(
            sorted(customers.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        # Tạo biểu đồ
        fig_customer = go.Figure(
            data=[
                go.Pie(
                    labels=list(top_customers.keys()),
                    values=list(top_customers.values()),
                    hole=0.4,
                    textposition="auto",
                    textinfo="percent+label",
                )
            ]
        )
        fig_customer.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            annotations=[
                dict(
                    text=f"Tổng số: {sum(top_customers.values())}",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                    xanchor="center",
                    yanchor="middle",
                )
            ],
        )
        st.plotly_chart(fig_customer, use_container_width=True)


def display_time_diff_charts(
    filtered_issues, show_dashboard_final=True, include_todo=False
):
    """Hiển thị biểu đồ phân bố chênh lệch thời gian

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
        show_dashboard_final (bool): Chỉ hiển thị issues có Show In Dashboard Final
        include_todo (bool): Bổ sung issues To Do có Show In Dashboard
    """
    st.subheader("Phân bố chênh lệch thời gian")

    # Thêm toggle switch để tính cả các issue đã hoàn thành khác
    include_other_done = st.toggle(
        "Tính cả issue Dev Done, Test Done, Deployed",
        value=True,
        help="Bao gồm các issue có trạng thái Dev Done, Test Done, Deployed trong phân tích chênh lệch thời gian",
    )

    # Lọc issues theo điều kiện show_in_dashboard_final và include_todo
    issues_to_analyze = filtered_issues.copy()
    if show_dashboard_final:
        issues_to_analyze = [
            issue
            for issue in issues_to_analyze
            if issue.get("show_in_dashboard_final", False)
        ]
        # Nếu include_todo được bật, bổ sung thêm các issue To Do có show_in_dashboard
        if include_todo:
            todo_issues = [
                issue
                for issue in filtered_issues
                if issue.get("status") == "To Do"
                and issue.get("show_in_dashboard", False)
                and not issue.get("show_in_dashboard_final", False)
            ]
            issues_to_analyze.extend(todo_issues)

        if not issues_to_analyze:
            st.warning("Không có issue nào thỏa mãn điều kiện hiển thị!")
            return

    # Lọc issues theo trạng thái hoàn thành
    done_statuses = ["done"]
    if include_other_done:
        done_statuses.extend(["dev done", "test done", "deployed"])

    done_issues = [
        issue
        for issue in issues_to_analyze
        if issue.get("status", "").lower() in done_statuses
    ]

    if not done_issues:
        status_text = (
            "Done" if not include_other_done else "Done/Dev Done/Test Done/Deployed"
        )
        st.info(
            f"Không có issue nào ở trạng thái {status_text} để phân tích chênh lệch thời gian."
        )
        return

    # Tạo layout 2 cột cho 2 biểu đồ
    diff_col1, diff_col2 = st.columns(2)

    # Tính toán chênh lệch thời gian cho mỗi issue Done
    time_diffs = []
    issue_diffs = []
    for issue in done_issues:
        time_estimate = issue.get("time_estimate", 0)
        time_spent = issue.get("time_spent", 0)
        time_diff = time_estimate - time_spent
        # Chỉ thêm vào danh sách nếu có chênh lệch
        if time_diff != 0:
            time_diffs.append(time_diff)
            issue_diffs.append(
                {
                    "key": issue.get("key"),
                    "summary": issue.get("summary", ""),
                    "diff": time_diff,
                    "estimate": time_estimate,
                    "spent": time_spent,
                    "status": issue.get("status", ""),
                    "assignee": issue.get("assignee", "Không có"),
                }
            )

    with diff_col1:
        st.subheader(
            "Top 5 chênh lệch lớn nhất",
            help="5 issue có chênh lệch thời gian lớn nhất (giờ)",
        )

        if not issue_diffs:
            st.info("Không có issue nào có chênh lệch thời gian.")
            return

        # Hiển thị bảng top 5
        for issue in sorted(issue_diffs, key=lambda x: abs(x["diff"]), reverse=True)[
            :5
        ]:
            status_color = "🔴" if issue["diff"] < 0 else "🟢"
            time_diff = issue["diff"]
            time_diff_text = f"{time_diff:+.1f}h" if time_diff != 0 else "0h"
            time_diff_color = (
                "red" if time_diff < 0 else ("green" if time_diff > 0 else "black")
            )
            assignee = issue.get("assignee", "Không có")

            # Tính phần trăm chênh lệch
            time_estimate = issue["estimate"]
            time_spent = issue["spent"]
            if time_estimate > 0:
                diff_percentage = (time_diff / time_estimate) * 100
            else:
                diff_percentage = 0

            st.markdown(
                f"""
                <div style='margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                    <div><b>{issue['key']}</b> - {issue['summary'][:50]}...</div>
                    <div>Assignee: {assignee}</div>
                    <div>Thời gian: {time_estimate:.1f}h → {time_spent:.1f}h | Chênh lệch: <span style='color: {time_diff_color}; font-weight: bold'>{time_diff_text}</span> ({diff_percentage:+.1f}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with diff_col2:
        st.subheader(
            "Phân bố chênh lệch",
            help="Phân bố số lượng issue theo khoảng chênh lệch thời gian",
        )

        # Tạo dữ liệu cho population pyramid
        positive_diffs = [x for x in time_diffs if x > 0]  # Thay đổi từ >= thành >
        negative_diffs = [abs(x) for x in time_diffs if x < 0]

        # Tạo bins cho histogram
        max_value = max(max(positive_diffs, default=0), max(negative_diffs, default=0))
        if max_value == 0:
            max_value = 1  # Đảm bảo max_value luôn lớn hơn 0

        num_bins = 10
        bin_size = max(1, max_value / num_bins)  # Đảm bảo bin_size không bao giờ = 0
        bins = [i * bin_size for i in range(num_bins + 1)]

        # Tính histogram cho cả hai phía
        positive_hist, _ = np.histogram(positive_diffs, bins=bins)
        negative_hist, _ = np.histogram(negative_diffs, bins=bins)

        # Tạo biểu đồ population pyramid
        fig_dist = go.Figure()

        # Thêm phần dương (bên phải)
        fig_dist.add_trace(
            go.Bar(
                y=bins[:-1],
                x=positive_hist,
                orientation="h",
                name="Trước hạn",
                marker_color="green",
                text=positive_hist,
                textposition="auto",
            )
        )

        # Thêm phần âm (bên trái)
        fig_dist.add_trace(
            go.Bar(
                y=bins[:-1],
                x=[-x for x in negative_hist],
                orientation="h",
                name="Quá hạn",
                marker_color="red",
                text=negative_hist,
                textposition="auto",
            )
        )

        # Cập nhật layout
        fig_dist.update_layout(
            barmode="overlay",
            bargap=0.1,
            title="",
            xaxis_title="Số lượng issue",
            yaxis_title="Chênh lệch (giờ)",
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
        )

        st.plotly_chart(fig_dist, use_container_width=True)

        # Hiển thị thống kê cơ bản
        time_diffs = pd.Series(time_diffs)
        status_text = (
            "Done" if not include_other_done else "Done/Dev Done/Test Done/Deployed"
        )
        total_issues = len(done_issues)
        diff_issues = len(time_diffs)
        st.caption(
            f"Thống kê ({diff_issues}/{total_issues} issues {status_text} có chênh lệch):"
        )
        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Trung bình", f"{time_diffs.mean():.1f}h")
        with stat_cols[1]:
            st.metric("Lớn nhất", f"{time_diffs.max():.1f}h")
        with stat_cols[2]:
            st.metric("Nhỏ nhất", f"{time_diffs.min():.1f}h")
        with stat_cols[3]:
            st.metric("Trung vị", f"{time_diffs.median():.1f}h")


def display_performance_chart(filtered_issues):
    """Hiển thị biểu đồ đánh giá hiệu suất của các assignee

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
    """
    st.subheader(
        "Đánh giá hiệu suất Assignee",
        help="Đánh giá hiệu suất làm việc của từng assignee",
    )

    # Thêm toggle switch để tính cả các issue đã hoàn thành khác
    include_other_done = st.toggle(
        "Tính cả issue Dev Done, Test Done, Deployed",
        value=True,
        help="Bao gồm các issue có trạng thái Dev Done, Test Done, Deployed trong đánh giá hiệu suất",
    )

    # Xác định các trạng thái được coi là hoàn thành
    done_statuses = ["done"]
    if include_other_done:
        done_statuses.extend(["dev done", "test done", "deployed"])

    # Hiển thị các trạng thái đang được tính
    status_text = (
        "Done" if not include_other_done else "Done/Dev Done/Test Done/Deployed"
    )
    st.caption(f"Đánh giá dựa trên các issue có trạng thái: {status_text}")

    # Chỉ xem xét assignee có issue
    assignees = {}
    for issue in filtered_issues:
        assignee = issue.get("assignee", "Không có")
        if assignee not in assignees:
            assignees[assignee] = {
                "total_issues": 0,
                "done_issues": 0,
                "total_estimate": 0,
                "total_spent": 0,
                "ahead_of_schedule": 0,  # Số issue hoàn thành trước hạn
                "on_schedule": 0,  # Số issue hoàn thành đúng hạn
                "behind_schedule": 0,  # Số issue hoàn thành trễ hạn
                "avg_time_per_issue": 0,  # Thời gian trung bình cho mỗi issue
                "efficiency_score": 0,  # Điểm hiệu suất (tính sau)
            }

        # Cập nhật số liệu
        assignees[assignee]["total_issues"] += 1

        # Kiểm tra nếu issue đã hoàn thành (dựa trên danh sách trạng thái được chấp nhận)
        issue_status = issue.get("status", "").lower()
        if issue_status in done_statuses:
            assignees[assignee]["done_issues"] += 1

            # Tính trạng thái deadline
            time_estimate = issue.get("time_estimate", 0)
            time_spent = issue.get("time_spent", 0)
            if time_estimate > time_spent:
                assignees[assignee]["ahead_of_schedule"] += 1
            elif time_estimate < time_spent:
                assignees[assignee]["behind_schedule"] += 1
            else:
                assignees[assignee]["on_schedule"] += 1

        # Cập nhật thời gian
        assignees[assignee]["total_estimate"] += issue.get("time_estimate", 0)
        assignees[assignee]["total_spent"] += issue.get("time_spent", 0)

    # Loại bỏ assignee "Không có" nếu có
    if "Không có" in assignees:
        del assignees["Không có"]

    # Nếu không có assignee nào
    if not assignees:
        st.info("Không có dữ liệu assignee để hiển thị.")
        return

    # Tính toán các chỉ số hiệu suất cho mỗi assignee
    for assignee, data in assignees.items():
        # Tỷ lệ hoàn thành
        completion_rate = (
            data["done_issues"] / data["total_issues"]
            if data["total_issues"] > 0
            else 0
        )

        # Điểm hiệu quả thời gian (1 = đúng thời gian, >1 = nhanh hơn, <1 = chậm hơn)
        time_efficiency = (
            data["total_estimate"] / data["total_spent"]
            if data["total_spent"] > 0
            else 1
        )

        # Tỷ lệ đúng hạn và trước hạn
        on_time_rate_raw = (
            (data["ahead_of_schedule"] + data["on_schedule"]) / data["done_issues"]
            if data["done_issues"] > 0
            else 0
        )

        # Lưu giá trị on_time_rate nhân 10 cho biểu đồ radar (để giữ tương thích)
        on_time_rate = on_time_rate_raw * 10

        # Tạo các biến issue_count và ahead_rate với logic đơn giản hơn
        # Tránh sử dụng df_performance vì chưa tồn tại
        # Issue count sẽ được cập nhật lại sau khi có df_performance
        data["issue_count"] = data["done_issues"]

        # Tính ahead_rate ngay tại đây
        data["ahead_rate"] = (
            data["ahead_of_schedule"] / data["done_issues"]
            if data["done_issues"] > 0
            else 0
        ) * 10

        # Thời gian trung bình cho mỗi issue hoàn thành
        data["avg_time_per_issue"] = (
            data["total_spent"] / data["done_issues"] if data["done_issues"] > 0 else 0
        )

        # Tính hệ số trọng số khối lượng dựa trên thời gian dự kiến
        # Để biết assignee nào đang xử lý công việc lớn/nhiều hơn
        avg_estimate_per_issue = (
            data["total_estimate"] / data["total_issues"]
            if data["total_issues"] > 0
            else 0
        )
        data["workload_factor"] = avg_estimate_per_issue

        # Tính khối lượng công việc đã hoàn thành (tính theo % thời gian dự kiến)
        completed_workload = 0
        if data["done_issues"] > 0:
            # Tính theo % thời gian dự kiến đã hoàn thành
            estimate_done_ratio = (
                data["total_estimate"]
                / sum(
                    assignee_data["total_estimate"]
                    for assignee_data in assignees.values()
                )
                if sum(
                    assignee_data["total_estimate"]
                    for assignee_data in assignees.values()
                )
                > 0
                else 0
            )
            completed_workload = estimate_done_ratio * 10  # Thang điểm 0-10
            # Giới hạn max 10 điểm
            completed_workload = min(10, completed_workload)

        # Tính điểm hiệu suất tổng hợp (thang điểm 0-100)
        time_efficiency_capped = min(
            2, time_efficiency
        )  # Giới hạn tối đa là 2 (gấp đôi hiệu quả)

        # Công thức mới, bao gồm trọng số cho khối lượng công việc dự kiến
        # 30% dựa trên tỷ lệ hoàn thành
        # 30% dựa trên hiệu quả thời gian
        # 20% dựa trên tỷ lệ đúng hạn
        # 20% dựa trên khối lượng công việc dự kiến đã hoàn thành
        data["efficiency_score"] = (
            (completion_rate * 30)
            + (min(1, time_efficiency_capped / 2) * 30)
            + (on_time_rate_raw * 20)  # Sử dụng tỷ lệ gốc, không nhân 10
            + (min(1, completed_workload / 10) * 20)  # Chuẩn hóa về 0-1 và nhân với 20
        )

    # Tạo DataFrame cho hiển thị dữ liệu đánh giá
    performance_data = []
    for assignee, data in assignees.items():
        performance_data.append(
            {
                "Assignee": assignee,
                "Tổng số issue": data["total_issues"],
                "Đã hoàn thành": data["done_issues"],
                "Tỷ lệ hoàn thành": f"{(data['done_issues']/data['total_issues']*100) if data['total_issues'] > 0 else 0:.1f}%",
                "Trước hạn": data["ahead_of_schedule"],
                "Đúng hạn": data["on_schedule"],
                "Trễ hạn": data["behind_schedule"],
                "Thời gian dự kiến (h)": data["total_estimate"],
                "Thời gian thực tế (h)": data["total_spent"],
                "TB dự kiến/issue (h)": data["workload_factor"],
                "Chênh lệch (h)": data["total_estimate"] - data["total_spent"],
                "Điểm hiệu suất": data["efficiency_score"],
            }
        )

    df_performance = pd.DataFrame(performance_data)

    # Sắp xếp DataFrame theo điểm hiệu suất giảm dần
    df_performance = df_performance.sort_values(by="Điểm hiệu suất", ascending=False)

    # Tìm giá trị tối đa của số issue hoàn thành
    max_done_issues = (
        df_performance["Đã hoàn thành"].max() if not df_performance.empty else 1
    )

    # Cập nhật lại issue_count cho tất cả assignee dựa trên max_done_issues
    for assignee, data in assignees.items():
        if max_done_issues > 0:
            data["issue_count"] = min(10, data["done_issues"] / max_done_issues * 10)

    # Tạo layout cho biểu đồ và bảng
    perf_col1, perf_col2 = st.columns([3, 2])

    with perf_col1:
        # Tạo biểu đồ so sánh điểm hiệu suất
        fig = go.Figure()

        # Thêm thanh điểm hiệu suất tổng hợp
        fig.add_trace(
            go.Bar(
                x=df_performance["Assignee"],
                y=df_performance["Điểm hiệu suất"],
                name="Điểm hiệu suất",
                marker_color="#5470C6",
                text=df_performance["Điểm hiệu suất"].apply(lambda x: f"{x:.1f}"),
                textposition="auto",
            )
        )

        # Thêm biểu đồ xếp chồng cho tỷ lệ hoàn thành
        fig.add_trace(
            go.Bar(
                x=df_performance["Assignee"],
                y=df_performance["Tổng số issue"],
                name="Tổng số issue",
                marker_color="#91CC75",
                opacity=0.7,
                visible="legendonly",  # Mặc định ẩn
            )
        )

        fig.add_trace(
            go.Bar(
                x=df_performance["Assignee"],
                y=df_performance["Đã hoàn thành"],
                name="Đã hoàn thành",
                marker_color="#73C0DE",
                opacity=0.7,
                visible="legendonly",  # Mặc định ẩn
            )
        )

        # Cấu hình layout
        fig.update_layout(
            title="Điểm hiệu suất làm việc của Assignee",
            xaxis_title="Assignee",
            yaxis_title="Điểm (0-100)",
            barmode="group",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=400,
        )

        # Hiển thị biểu đồ
        st.plotly_chart(fig, use_container_width=True)

        # Thêm biểu đồ radar cho top 5 assignee có điểm cao nhất
        top_assignees = df_performance.head(min(5, len(df_performance)))

        if len(top_assignees) > 1:  # Chỉ vẽ biểu đồ radar nếu có ít nhất 2 assignee
            categories = [
                "Tỷ lệ hoàn thành",
                "Hiệu quả thời gian",
                "Tỷ lệ đúng hạn",
                "Số issue đã làm",
                "Trước hạn",
            ]

            fig_radar = go.Figure()

            for i, row in top_assignees.iterrows():
                assignee = row["Assignee"]
                data = assignees[assignee]

                # Chuẩn hóa các chỉ số để hiển thị trên radar chart (thang điểm 0-10)
                completion_rate = (
                    data["done_issues"] / data["total_issues"]
                    if data["total_issues"] > 0
                    else 0
                ) * 10
                time_efficiency = min(
                    10,
                    (
                        data["total_estimate"] / data["total_spent"]
                        if data["total_spent"] > 0
                        else 1
                    )
                    * 5,
                )
                on_time_rate_raw = (
                    (data["ahead_of_schedule"] + data["on_schedule"])
                    / data["done_issues"]
                    if data["done_issues"] > 0
                    else 0
                )

                # Lưu giá trị on_time_rate nhân 10 cho biểu đồ radar (để giữ tương thích)
                on_time_rate = on_time_rate_raw * 10

                # Sử dụng giá trị đã được tính trước đó
                issue_count = data["issue_count"]
                ahead_rate = data["ahead_rate"]

                # Thêm trace cho mỗi assignee
                fig_radar.add_trace(
                    go.Scatterpolar(
                        r=[
                            completion_rate,
                            time_efficiency,
                            on_time_rate,
                            issue_count,
                            ahead_rate,
                        ],
                        theta=categories,
                        fill="toself",
                        name=assignee,
                    )
                )

            # Cấu hình layout cho radar chart
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                showlegend=True,
                title="Phân tích hiệu suất của Top Assignee",
                height=400,
            )

            st.plotly_chart(fig_radar, use_container_width=True)

    with perf_col2:
        # Thông tin các chỉ số đánh giá
        st.info(
            """
        **Các chỉ số đánh giá hiệu suất:**
        
        - **Điểm hiệu suất**: Thang điểm 0-100, kết hợp các yếu tố:
          - 30% dựa trên tỷ lệ hoàn thành
          - 30% dựa trên hiệu quả thời gian
          - 20% dựa trên tỷ lệ đúng hạn
          - 20% dựa trên khối lượng công việc đã hoàn thành
        
        - **Hiệu quả thời gian**: So sánh thời gian dự kiến và thời gian thực tế
          - >1: Làm nhanh hơn dự kiến
          - =1: Đúng thời gian dự kiến
          - <1: Làm chậm hơn dự kiến
          
        - **TB dự kiến/issue**: Thời gian trung bình dự kiến cho mỗi issue
          (chỉ số này phản ánh độ phức tạp công việc của assignee)
        """
        )

        # Hiển thị bảng dữ liệu hiệu suất
        st.dataframe(
            df_performance[
                [
                    "Assignee",
                    "Tổng số issue",
                    "Đã hoàn thành",
                    "Tỷ lệ hoàn thành",
                    "Thời gian dự kiến (h)",
                    "TB dự kiến/issue (h)",
                    "Trước hạn",
                    "Đúng hạn",
                    "Trễ hạn",
                    "Điểm hiệu suất",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def display_time_analysis_by_user(filtered_issues):
    """Hiển thị biểu đồ phân tích thời gian theo user

    Args:
        filtered_issues (list): Danh sách issues đã được lọc
    """
    st.subheader(
        "Phân tích thời gian theo User",
        help="Phân tích thời gian đã log theo từng user, phân chia theo loại issue",
    )

    # Tạo dictionary để lưu thời gian theo user
    user_time = {}

    # Lọc các issue có sprint_time_spent
    issues_with_sprint_time = [
        issue for issue in filtered_issues if issue.get("sprint_time_spent", 0) > 0
    ]

    for issue in issues_with_sprint_time:
        assignee = issue.get("assignee", "Không có")
        if assignee not in user_time:
            user_time[assignee] = {
                "non_dev": 0,  # Thời gian cho issue non-dev
                "popup": 0,  # Thời gian cho issue popup
                "development": 0,  # Thời gian cho issue development
                "issues": {  # Lưu danh sách issues cho mỗi loại
                    "non_dev": [],
                    "popup": [],
                    "development": [],
                },
            }

        sprint_time_spent = issue.get("sprint_time_spent", 0)
        show_in_dashboard_value = issue.get("show_in_dashboard", "")
        show_in_dashboard = show_in_dashboard_value is True or (
            isinstance(show_in_dashboard_value, str)
            and show_in_dashboard_value.upper() == "YES"
        )
        popup_value = issue.get("popup", "")
        is_popup = popup_value is True or (
            isinstance(popup_value, str) and popup_value.upper() == "YES"
        )

        if not show_in_dashboard:
            user_time[assignee]["non_dev"] += sprint_time_spent
            user_time[assignee]["issues"]["non_dev"].append(issue)
        elif is_popup:
            user_time[assignee]["popup"] += sprint_time_spent
            user_time[assignee]["issues"]["popup"].append(issue)
        else:
            user_time[assignee]["development"] += sprint_time_spent
            user_time[assignee]["issues"]["development"].append(issue)

    # Loại bỏ user "Không có" nếu có
    if "Không có" in user_time:
        del user_time["Không có"]

    if not user_time:
        st.info("Không có dữ liệu thời gian để phân tích.")
        return

    # Tạo DataFrame cho dữ liệu
    data = []
    for assignee, times in user_time.items():
        total_time = sum([times["non_dev"], times["popup"], times["development"]])
        data.append(
            {
                "Assignee": assignee,
                "Non-dev": times["non_dev"],
                "Popup": times["popup"],
                "Development": times["development"],
                "Tổng thời gian": total_time,
                "% Non-dev": (
                    (times["non_dev"] / total_time * 100) if total_time > 0 else 0
                ),
                "% Popup": (times["popup"] / total_time * 100) if total_time > 0 else 0,
                "% Development": (
                    (times["development"] / total_time * 100) if total_time > 0 else 0
                ),
            }
        )

    df_time = pd.DataFrame(data)

    # Tạo layout 2 cột

    # Tạo biểu đồ stacked bar
    fig = go.Figure()

    # Thêm các loại thời gian
    fig.add_trace(
        go.Bar(
            name="Non-dev",
            x=df_time["Assignee"],
            y=df_time["Non-dev"],
            marker_color="#FF9999",
            text=df_time["% Non-dev"].apply(lambda x: f"{x:.1f}%"),
            textposition="auto",
            customdata=df_time[["Assignee", "Non-dev"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Thời gian: %{y:.1f}h<br>"
            + "Tỷ lệ: %{text}<br>"
            + "<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Popup",
            x=df_time["Assignee"],
            y=df_time["Popup"],
            marker_color="#FFCC99",
            text=df_time["% Popup"].apply(lambda x: f"{x:.1f}%"),
            textposition="auto",
            customdata=df_time[["Assignee", "Popup"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Thời gian: %{y:.1f}h<br>"
            + "Tỷ lệ: %{text}<br>"
            + "<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Development",
            x=df_time["Assignee"],
            y=df_time["Development"],
            marker_color="#99CC99",
            text=df_time["% Development"].apply(lambda x: f"{x:.1f}%"),
            textposition="auto",
            customdata=df_time[["Assignee", "Development"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>"
            + "Thời gian: %{y:.1f}h<br>"
            + "Tỷ lệ: %{text}<br>"
            + "<extra></extra>",
        )
    )

    # Cập nhật layout
    fig.update_layout(
        barmode="stack",
        title="Phân bố thời gian theo loại issue",
        xaxis_title="Assignee",
        yaxis_title="Thời gian (giờ)",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        clickmode="event+select",
    )

    # Hiển thị biểu đồ
    st.plotly_chart(fig, use_container_width=True)

    # # Thêm selectbox để chọn assignee và loại thời gian
    # col1, col2 = st.columns(2)
    # with col1:
    #     selected_assignee = st.selectbox(
    #         "Chọn Assignee",
    #         options=df_time["Assignee"].tolist(),
    #         key="selected_assignee",
    #     )
    # with col2:
    #     selected_category = st.selectbox(
    #         "Chọn loại thời gian",
    #         options=["non_dev", "popup", "development"],
    #         format_func=lambda x: {
    #             "non_dev": "Non-dev",
    #             "popup": "Popup",
    #             "development": "Development",
    #         }[x],
    #         key="selected_category",
    #     )

    # # Hiển thị danh sách issues tương ứng
    # if selected_assignee and selected_category:
    #     selected_issues = user_time[selected_assignee]["issues"][selected_category]

    #     if selected_issues:
    #         st.subheader(
    #             f"Danh sách issues của {selected_assignee} - {selected_category}"
    #         )

    #         # Tạo DataFrame cho danh sách issues
    #         issues_data = []
    #         for issue in selected_issues:
    #             issues_data.append(
    #                 {
    #                     "Key": issue.get("key", ""),
    #                     "Summary": issue.get("summary", ""),
    #                     "Status": issue.get("status", ""),
    #                     "Thời gian (h)": issue.get("sprint_time_spent", 0),
    #                     "Show in Dashboard": issue.get("show_in_dashboard", ""),
    #                     "Popup": issue.get("popup", ""),
    #                 }
    #             )

    #         df_selected = pd.DataFrame(issues_data)
    #         st.dataframe(df_selected, use_container_width=True, hide_index=True)
    #     else:
    #         st.info(
    #             f"Không có issues nào cho {selected_assignee} trong danh mục {selected_category}"
    #         )

    # with time_col2:
    #     # Hiển thị bảng dữ liệu chi tiết
    #     st.dataframe(
    #         df_time[
    #             [
    #                 "Assignee",
    #                 "Tổng thời gian",
    #                 "Non-dev",
    #                 "Popup",
    #                 "Development",
    #                 "% Non-dev",
    #                 "% Popup",
    #                 "% Development",
    #             ]
    #         ].round(1),
    #         use_container_width=True,
    #         hide_index=True,
    #     )


def main():
    """Hàm chính của ứng dụng"""
    st.title("Báo Cáo Sprint")

    # Khởi tạo service
    sprint_service = SprintReportService()

    # Hiển thị dự án đang sử dụng
    st.toast(f"Đang sử dụng dự án: {DEFAULT_PROJECT}", icon="🔍")

    # Kiểm tra kết nối MongoDB
    mongo_available = sprint_service.mongo_client.is_connected()
    if mongo_available:
        st.toast("Kết nối đến MongoDB thành công!", icon="✅")

    else:
        st.error("Không thể kết nối đến MongoDB. Vui lòng kiểm tra cấu hình kết nối!")
        st.stop()

    # Tải danh sách sprint từ API
    with st.spinner("Đang tải danh sách sprint từ Jira API..."):
        # Kiểm tra xem sprints đã có trong session_state chưa
        if "sprints" not in st.session_state:
            st.session_state.sprints = sprint_service.get_all_sprints(DEFAULT_PROJECT)
        sprints = st.session_state.sprints

    if not sprints:
        st.error(f"Không tìm thấy sprint nào cho dự án {DEFAULT_PROJECT}")
        st.stop()

    # Format sprint options cho dropdown selection
    sprint_options = []
    active_sprint_index = 0  # Mặc định là sprint đầu tiên

    for i, sprint in enumerate(sprints):
        state = sprint.get("state", "unknown").upper()
        name = sprint.get("name", "Unnamed Sprint")
        option = f"{name} ({state})"
        sprint_options.append(
            {
                "display": option,
                "id": sprint.get("id"),
                "board_id": sprint.get("originBoardId"),
                "data": sprint,
            }
        )

        # Nếu sprint đang active, ghi nhớ vị trí
        if sprint.get("state") == "active":
            active_sprint_index = i

    # Sắp xếp sprints: Active first, then by name
    sprint_options.sort(
        key=lambda x: (
            (
                0
                if x["data"].get("state") == "active"
                else (1 if x["data"].get("state") == "future" else 2)
            ),
            x["data"].get("name", ""),
        )
    )

    # Tìm lại vị trí của sprint active sau khi sắp xếp
    for i, sprint in enumerate(sprint_options):
        if sprint["data"].get("state") == "active":
            active_sprint_index = i
            break

    # Selection với sprint active được chọn mặc định
    selected_sprint_idx = st.selectbox(
        "Chọn Sprint",
        options=range(len(sprint_options)),
        format_func=lambda i: sprint_options[i]["display"],
        index=active_sprint_index,  # Mặc định chọn sprint đang active
        key="selected_sprint_idx",
    )

    selected_sprint = sprint_options[selected_sprint_idx]
    sprint_id = selected_sprint["id"]

    # Lấy dữ liệu issues từ MongoDB ngay khi chọn sprint
    # Kiểm tra xem sprint_id hiện tại có khác với sprint_id đã lưu không
    should_reload_data = (
        "current_sprint_id" not in st.session_state
        or st.session_state.current_sprint_id != sprint_id
        or "issues" not in st.session_state
    )

    if should_reload_data:
        with st.spinner("Đang tải dữ liệu từ MongoDB..."):
            issues = sprint_service.get_sprint_issues_from_mongo(sprint_id)
            st.session_state.issues = issues
            st.session_state.current_sprint_id = sprint_id

            # Cũng tải thông tin sprint từ MongoDB
            sprint_mongo_info = sprint_service.get_sprint_info_from_mongo(sprint_id)
            st.session_state.sprint_mongo_info = sprint_mongo_info
    else:
        issues = st.session_state.issues
        sprint_mongo_info = st.session_state.sprint_mongo_info

    if not issues:
        st.warning(f"Không tìm thấy dữ liệu cho sprint này trong MongoDB!")
        st.info(
            "Vui lòng đồng bộ dữ liệu sprint này trong trang **Đồng bộ dữ liệu** trước khi xem báo cáo."
        )
        st.stop()

    # Hiển thị thời gian cập nhật cuối cùng nếu có
    if sprint_mongo_info and "updated_at" in sprint_mongo_info:
        updated_at = sprint_mongo_info["updated_at"]
        # Hiển thị thời gian theo múi giờ GMT+0
        if isinstance(updated_at, datetime):
            # Nếu thời gian đã có thông tin timezone
            if updated_at.tzinfo is not None:
                # Chuyển sang múi giờ UTC (GMT+0)
                utc_tz = pytz.timezone("UTC")
                updated_at = updated_at.astimezone(utc_tz)
            else:
                # Nếu không có thông tin timezone, giả định thời gian đã là UTC
                # Chỉ cần gán nhãn UTC cho nó
                utc_tz = pytz.timezone("UTC")
                updated_at = utc_tz.localize(updated_at)

            formatted_time = updated_at.strftime("%d/%m/%Y %H:%M:%S")
            st.info(f"Dữ liệu được cập nhật lần cuối: {formatted_time}")

    # Tạo tabs cho các loại báo cáo khác nhau
    tab1, tab2 = st.tabs(["📊 Báo cáo Sprint", "⏱️ Phân tích thời gian"])

    with tab1:
        # Thêm bộ lọc show_in_dashboard_final và include_todo trong cùng một hàng
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            show_dashboard_final = st.toggle(
                "Chỉ hiển thị issues có Show In Dashboard Final",
                value=True,
                key="show_dashboard_final_tab1",
            )

        with filter_col2:
            include_todo = st.toggle(
                "Bổ sung issues To Do có Show In Dashboard",
                value=False,
                help="Bổ sung các issue có trạng thái To Do và có Show In Dashboard vào danh sách",
                key="include_todo_tab1",
            )

        # Lọc issues theo show_in_dashboard_final và include_todo
        if show_dashboard_final:
            issues_final = [
                issue for issue in issues if issue.get("show_in_dashboard_final", False)
            ]
            # Nếu include_todo được bật, bổ sung thêm các issue To Do có show_in_dashboard
            if include_todo:
                todo_issues = [
                    issue
                    for issue in issues
                    if issue.get("status") == "To Do"
                    and issue.get("show_in_dashboard", False)
                    and not issue.get("show_in_dashboard_final", False)
                ]
                issues_final.extend(todo_issues)

            # Thêm các issue có log time và SHOW IN DASHBOARD = YES
            additional_issues = [
                issue
                for issue in issues
                if issue.get("show_in_dashboard", False)
                and issue.get("time_spent", 0) > 0  # Có log time
                and not issue.get(
                    "show_in_dashboard_final", False
                )  # Chưa có trong danh sách
                and issue.get("status") != "To Do"  # Không phải issue To Do
            ]
            issues_final.extend(additional_issues)

            if not issues_final:
                st.warning("Không có issue nào thỏa mãn điều kiện hiển thị!")
                st.stop()
        else:
            issues_final = issues

        # Hiển thị thông tin cơ bản của sprint trong bố cục cột
        st.subheader(
            f"Sprint: {selected_sprint['data'].get('name', '')} ({selected_sprint['data'].get('state', '').upper()})"
        )

        # Lấy thông tin thời gian của sprint
        start_date_str = selected_sprint["data"].get("startDate", "")
        end_date_str = selected_sprint["data"].get("endDate", "")

        # Format thời gian hiển thị theo GMT+7
        start_date = format_date(start_date_str)
        end_date = format_date(end_date_str)

        # Tính số ngày còn lại và tiến độ sprint
        days_remaining = calculate_days_remaining(end_date_str)
        progress_percent = calculate_sprint_progress(start_date_str, end_date_str)

        # Bố trí thông tin sprint thành 2 cột
        col1, col2 = st.columns(2)

        with col1:
            if start_date and end_date:
                st.write(f"**Thời gian:** {start_date} → {end_date}")
            if days_remaining is not None:
                if days_remaining >= 0:
                    st.write(f"**Ngày còn lại:** {days_remaining} ngày")
                else:
                    st.write(f"**Quá hạn:** {abs(days_remaining)} ngày")

        with col2:
            goal = selected_sprint["data"].get("goal", "")
            if goal:
                st.write(f"**Mục tiêu:** {goal}")

        # Hiển thị thanh tiến độ thời gian
        if progress_percent is not None:
            st.write("**Tiến độ thời gian sprint:**")
            progress_color = "normal"
            if progress_percent > 80:
                progress_color = "red"
            elif progress_percent > 50:
                progress_color = "orange"

            st.progress(progress_percent / 100, text=f"{progress_percent:.1f}%")

            if progress_percent < 100:
                elapsed_text = f"Đã trôi qua {progress_percent:.1f}% thời gian sprint"
            else:
                elapsed_text = "Sprint đã kết thúc"
            st.caption(elapsed_text)

        # Thêm bộ lọc dev_group và assignee trong cùng một hàng
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            dev_groups = ["DEV FULL + DEV FE", "DEV FULL", "DEV FE", "NON DEV"]
            selected_dev_group = st.selectbox(
                "Lọc theo nhóm developer",
                options=dev_groups,
                index=0,  # Mặc định là "DEV FULL + DEV FE"
            )

        with filter_col2:
            # Lấy danh sách assignee từ issues_final
            assignees = sorted(
                list(
                    set(
                        issue.get("assignee", "")
                        for issue in issues_final
                        if issue.get("assignee")
                    )
                )
            )
            assignees.insert(0, "Tất cả")  # Thêm option "Tất cả" vào đầu danh sách
            selected_assignee = st.selectbox(
                "Lọc theo Assignee", options=assignees, index=0
            )

        # Lọc issues theo dev_group và assignee đã chọn
        filtered_issues = [
            issue
            for issue in issues_final
            if (
                selected_dev_group == "DEV FULL + DEV FE"
                and issue.get("dev_group") in ["DEV FULL", "DEV FE"]
            )
            or issue.get("dev_group") == selected_dev_group
            and (
                selected_assignee == "Tất cả"
                or issue.get("assignee") == selected_assignee
            )
        ]

        # Hiển thị thống kê
        st.subheader("Thống kê")

        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

        with stat_col1:
            total_issues = len(filtered_issues)
            done_issues = len(
                [
                    issue
                    for issue in filtered_issues
                    if issue.get("status", "").lower() in ["done"]
                ]
            )
            st.metric(
                "Tổng số issue Done",
                f"{done_issues}/{total_issues} ({(done_issues/total_issues)*100:.1f}%)",
            )

        with stat_col2:
            dev_done_issues = len(
                [
                    issue
                    for issue in filtered_issues
                    if issue.get("status", "").lower()
                    in ["dev done", "test done", "deployed", "done"]
                ]
            )
            st.metric(
                "Số issue dev done",
                f"{dev_done_issues}/{total_issues} ({(dev_done_issues/total_issues)*100:.1f}%)",
            )

        with stat_col3:
            popup_issues = len(
                [issue for issue in filtered_issues if issue.get("popup") is True]
            )
            st.metric(
                "Số issue Popup",
                f"{popup_issues}/{total_issues} ({(popup_issues/total_issues)*100:.1f}%)",
            )

        with stat_col4:
            dashboard_final_issues = len(
                [
                    issue
                    for issue in filtered_issues
                    if issue.get("show_in_dashboard_final") is True
                ]
            )
            st.metric("Số issue Dashboard Final", dashboard_final_issues)

        # Hiển thị danh sách issues
        if filtered_issues:
            # Hiển thị Burn Down Chart
            display_burndown_chart(
                filtered_issues,
                selected_sprint["data"].get("startDate", ""),
                selected_sprint["data"].get("endDate", ""),
            )
            # Hiển thị Status Chart
            display_status_chart(filtered_issues)

            # Hiển thị phân bố theo loại issue và customer
            display_distribution_charts(filtered_issues)

            # Hiển thị biểu đồ đánh giá hiệu suất của assignee
            display_performance_chart(filtered_issues)

            # Hiển thị phân bố chênh lệch thời gian
            display_time_diff_charts(
                filtered_issues, show_dashboard_final, include_todo
            )

            # Hiển thị danh sách các issues đã lọc
            st.subheader("Danh sách các issues đã lọc")

            # Tạo expander để không chiếm quá nhiều không gian trên trang
            with st.expander("Nhấn để xem danh sách chi tiết", expanded=False):
                # Chuyển danh sách issues sang DataFrame
                df_issues = pd.DataFrame(filtered_issues)

                # Hiển thị DataFrame
                st.dataframe(
                    df_issues,
                    use_container_width=True,
                    height=500,
                    hide_index=True,
                )

                # Thông tin về số lượng issues đang hiển thị
                st.caption(
                    f"Hiển thị {len(filtered_issues)} issues từ tổng số {len(issues_final)} trong filter hiện tại."
                )

        else:
            st.info(f"Không có issue nào thuộc nhóm {selected_dev_group}")

    with tab2:
        # Hiển thị phân tích thời gian theo user
        display_time_analysis_by_user(issues)


def format_date(date_str):
    """Format ISO date string sang định dạng dễ đọc hơn theo múi giờ GMT+7

    Args:
        date_str (str): Chuỗi ngày định dạng ISO

    Returns:
        str: Chuỗi ngày đã định dạng
    """
    if not date_str:
        return ""

    try:
        # Chuyển đổi chuỗi ISO sang đối tượng datetime với timezone
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Chuyển đổi sang múi giờ GMT+7 (Asia/Ho_Chi_Minh)
        vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        date_obj = date_obj.astimezone(vietnam_tz)

        # Định dạng ngày giờ
        return date_obj.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return date_str


if __name__ == "__main__":
    main()
