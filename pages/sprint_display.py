import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import io
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Set page configuration if this is a standalone page
if __name__ == "__main__":
    st.set_page_config(
        page_title="Sprint Analysis",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

# Cấu hình danh sách tên người dùng sẽ bị loại bỏ khỏi phân tích hiệu suất
EXCLUDED_USERS = [
    "Không được giao",
    "Unassigned",
    "Nguyễn Xuân Hoà",
]  # Thêm tên người dùng cần loại bỏ vào đây


def get_issue_key(issue):
    """Lấy key của issue"""
    return issue.get("key", "Unknown")


def get_issue_summary(issue):
    """Lấy summary của issue"""
    return issue.get("fields", {}).get("summary", "Không có tóm tắt")


def get_issue_type(issue):
    """Lấy loại issue"""
    return issue.get("fields", {}).get("issuetype", {}).get("name", "Không rõ")


def is_subtask(issue):
    """Kiểm tra xem issue có phải là subtask không"""
    return issue.get("fields", {}).get("issuetype", {}).get("subtask", False)


def get_issue_status(issue):
    """Lấy trạng thái của issue"""
    return issue.get("fields", {}).get("status", {}).get("name", "Không rõ")


def get_assignee(issue):
    """Lấy người được gán cho issue"""
    if issue.get("fields", {}).get("assignee"):
        return (
            issue.get("fields", {})
            .get("assignee", {})
            .get("displayName", "Không được giao")
        )
    return "Không được giao"


def is_popup(issue):
    """Kiểm tra xem issue có phải là popup không"""
    customfield = issue.get("fields", {}).get("customfield_10130")
    if customfield and customfield.get("value") == "YES":
        return True
    return False


def get_time_original_estimate(issue):
    """Lấy thời gian ước tính ban đầu"""
    return issue.get("fields", {}).get("timeoriginalestimate", 0) or 0


def get_time_spent(issue):
    """Lấy thời gian đã sử dụng"""
    return issue.get("fields", {}).get("timespent", 0) or 0


def calculate_remaining_estimate(issue):
    """Tính toán thời gian còn lại"""
    original = get_time_original_estimate(issue)
    spent = get_time_spent(issue)
    # Đảm bảo cả hai giá trị đều là số
    original = 0 if original is None else original
    spent = 0 if spent is None else spent
    return max(0, original - spent)


def create_issues_dataframe(issues):
    """
    Tạo DataFrame từ danh sách issues của Jira

    Args:
        issues (list): Danh sách các issue từ Jira API

    Returns:
        pd.DataFrame: DataFrame chứa thông tin các issue đã được xử lý
    """
    # Tạo danh sách các dictionary chứa thông tin đã xử lý
    processed_issues = []

    for issue in issues:
        processed_issue = {
            "key": get_issue_key(issue),
            "summary": get_issue_summary(issue),
            "issuetype": get_issue_type(issue),
            "is_subtask": is_subtask(issue),
            "status": get_issue_status(issue),
            "assignee": get_assignee(issue),
            "is_popup": is_popup(issue),
            "timeoriginalestimate": get_time_original_estimate(issue),
            "timespent": get_time_spent(issue),
            "remainingestimate": calculate_remaining_estimate(issue),
        }
        processed_issues.append(processed_issue)

    return pd.DataFrame(processed_issues)


def display_sprint_metrics(df_issues, sprint):
    """
    Hiển thị các chỉ số phân tích cho sprint

    Args:
        df_issues (pd.DataFrame): DataFrame chứa thông tin các issue
        sprint (dict): Thông tin về sprint
    """
    # Định nghĩa các trạng thái hoàn thành
    done_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]

    # Phân loại task
    tasks = df_issues[
        (df_issues["issuetype"] != "Epic") & (df_issues["is_subtask"] == False)
    ]
    subtasks = df_issues[df_issues["is_subtask"] == True]

    # Tính toán số lượng task hoàn thành
    tasks_done = tasks[tasks["status"].isin(done_statuses)]
    subtasks_done = subtasks[subtasks["status"].isin(done_statuses)]

    # Tính toán thời gian
    total_estimate = df_issues["timeoriginalestimate"].sum()
    total_spent = df_issues["timespent"].sum()
    total_remaining = df_issues["remainingestimate"].sum()

    # Chuyển đổi thời gian từ giây sang giờ
    total_estimate_hours = total_estimate / 3600
    total_spent_hours = total_spent / 3600
    total_remaining_hours = total_remaining / 3600

    # Tính tỷ lệ thời gian đã sử dụng và còn lại
    time_progress = (total_spent / total_estimate * 100) if total_estimate > 0 else 0
    time_efficiency = (
        (total_spent / (total_spent + total_remaining) * 100)
        if (total_spent + total_remaining) > 0
        else 0
    )

    # Hiển thị thông tin thời gian
    st.subheader("⏱️ Thời gian Sprint")

    # Xử lý thông tin thời gian bắt đầu và kết thúc sprint
    start_date = None
    end_date = None
    days_remaining = None

    if sprint.get("startDate") and sprint.get("endDate"):
        try:
            # Chuyển đổi chuỗi thời gian thành đối tượng datetime
            start_date = datetime.strptime(
                sprint.get("startDate"), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            end_date = datetime.strptime(sprint.get("endDate"), "%Y-%m-%dT%H:%M:%S.%fZ")

            # Tính số ngày còn lại
            now = datetime.now()
            if now < end_date:
                days_remaining = (end_date - now).days
            else:
                days_remaining = 0
        except Exception as e:
            st.warning(f"Không thể phân tích thời gian sprint: {str(e)}")

    # Hiển thị thông tin thời gian sprint
    if start_date and end_date:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ngày bắt đầu", start_date.strftime("%d/%m/%Y"))
        with col2:
            st.metric("Ngày kết thúc", end_date.strftime("%d/%m/%Y"))
        with col3:
            if days_remaining is not None:
                st.metric("Số ngày còn lại", f"{days_remaining} ngày")

        # Tính tổng số ngày của sprint và số ngày đã trôi qua
        total_days = (end_date - start_date).days
        days_passed = (
            (datetime.now() - start_date).days if datetime.now() > start_date else 0
        )
        days_passed = min(
            days_passed, total_days
        )  # Đảm bảo không vượt quá tổng số ngày

        # Hiển thị thanh tiến độ thời gian của sprint
        if total_days > 0:
            sprint_progress = days_passed / total_days
            st.write("Tiến độ thời gian sprint:")
            st.progress(sprint_progress)

    # Hiển thị thông tin thời gian làm việc
    st.write("#### Thời gian làm việc")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Thời gian ước tính", f"{total_estimate_hours:.1f} giờ")
    with col2:
        st.metric("Thời gian đã sử dụng", f"{total_spent_hours:.1f} giờ")
    with col3:
        st.metric("Thời gian còn lại", f"{total_remaining_hours:.1f} giờ")
    with col4:
        st.metric("Tỷ lệ thời gian đã sử dụng", f"{time_progress:.1f}%")
    with col5:
        st.metric("Hiệu suất thời gian", f"{time_efficiency:.1f}%")

    # Hiển thị metrics
    st.subheader("📊 Chỉ số Sprint")

    # Tính toán số lượng task popup
    popup_tasks = tasks[tasks["is_popup"] == True]
    popup_tasks_done = popup_tasks[popup_tasks["status"].isin(done_statuses)]

    total_tasks = len(tasks)
    total_tasks_done = len(tasks_done)
    total_popup_tasks = len(popup_tasks)

    percent_tasks_done = (
        (total_tasks_done / total_tasks * 100) if total_tasks > 0 else 0
    )
    percent_popup = (total_popup_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Hiển thị thông tin về task popup
    col1, col2 = st.columns(2)

    # Hiển thị thông tin về task và subtask
    st.write("#### Thông tin Task và Subtask")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Tasks hoàn thành",
            f"{total_tasks_done}/{total_tasks} ({percent_tasks_done:.0f}%)",
        )

    with col2:
        total_subtasks = len(subtasks)
        total_subtasks_done = len(subtasks_done)
        percent_subtasks_done = (
            (total_subtasks_done / total_subtasks * 100) if total_subtasks > 0 else 0
        )

        st.metric(
            "Sub-tasks hoàn thành",
            f"{total_subtasks_done}/{total_subtasks} ({percent_subtasks_done:.0f}%)",
        )

    with col3:
        st.metric(
            "Task Popup",
            f"{total_popup_tasks}/{total_tasks} ({percent_popup:.0f}%)",
            help="Số lượng task popup so với tổng số task",
        )

    # Hiển thị biểu đồ so sánh tiến độ công việc và tiến độ thời gian
    st.subheader("📈 So sánh tiến độ công việc và tiến độ thời gian")

    # Tính tỷ lệ công việc hoàn thành (dựa trên số lượng task và subtask)
    total_issues = total_tasks + total_subtasks
    total_issues_done = total_tasks_done + total_subtasks_done
    work_progress = (total_issues_done / total_issues * 100) if total_issues > 0 else 0

    # Tạo DataFrame cho biểu đồ
    progress_data = pd.DataFrame(
        {
            "Loại": ["Tiến độ công việc", "Tiến độ thời gian"],
            "Phần trăm": [work_progress, time_progress],
        }
    )

    # Tạo biểu đồ
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(
        progress_data["Loại"], progress_data["Phần trăm"], color=["#4CAF50", "#2196F3"]
    )

    # Thêm nhãn giá trị
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1,
            f"{height:.1f}%",
            ha="center",
            va="bottom",
        )

    # Thêm đường tham chiếu 100%
    ax.axhline(y=100, color="black", linestyle="--", alpha=0.7)

    ax.set_ylim(0, 110)
    ax.set_ylabel("Phần trăm (%)")
    ax.set_title("So sánh tiến độ công việc và tiến độ thời gian")

    plt.tight_layout()
    st.pyplot(fig)


def display_team_performance(df_issues):
    """
    Hiển thị hiệu suất của team và từng người

    Args:
        df_issues (pd.DataFrame): DataFrame chứa thông tin các issue
    """
    # Định nghĩa các trạng thái hoàn thành
    done_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]

    # Lọc các task (không phải Epic và không phải subtask)
    tasks = df_issues[
        (df_issues["issuetype"] != "Epic")
    ]

    # Tính toán hiệu suất theo người
    st.subheader("👥 Hiệu suất team")

    # Tạo DataFrame hiệu suất theo người
    user_performance = []

    for assignee in tasks["assignee"].unique():
        # Bỏ qua những người dùng trong danh sách loại trừ
        if assignee in EXCLUDED_USERS:
            continue

        user_tasks = tasks[tasks["assignee"] == assignee]
        user_tasks_done = user_tasks[user_tasks["status"].isin(done_statuses)]

        total_tasks = len(user_tasks)
        total_done = len(user_tasks_done)
        completion_rate = (total_done / total_tasks * 100) if total_tasks > 0 else 0

        total_estimate = user_tasks["timeoriginalestimate"].sum()
        total_spent = user_tasks["timespent"].sum()

        # Tính tỷ lệ thời gian sử dụng so với ước tính
        time_efficiency = (
            (total_spent / total_estimate * 100) if total_estimate > 0 else 0
        )

        # Tính thời gian còn lại
        time_remaining = total_estimate - total_spent

        user_performance.append(
            {
                "Assignee": assignee,
                "Tasks": total_tasks,
                "Done": total_done,
                "Completion Rate": f"{completion_rate:.0f}%",
                "Original Estimate (h)": f"{total_estimate/3600:.1f}",
                "Time Spent (h)": f"{total_spent/3600:.1f}",
                "Time Efficiency": f"{time_efficiency:.0f}%",
                "Time Efficiency Numeric": time_efficiency,
                "Completion Rate Numeric": completion_rate,
                "Original Estimate": total_estimate,
                "Time Spent": total_spent,
                "Time Remaining (h)": f"{time_remaining/3600:.1f}",  # Thêm cột thời gian còn lại
            }
        )

    # Tạo DataFrame và hiển thị
    df_performance = pd.DataFrame(user_performance)

    if not df_performance.empty:
        st.dataframe(
            df_performance[
                [
                    "Assignee",
                    "Tasks",
                    "Done",
                    "Completion Rate",
                    "Original Estimate (h)",
                    "Time Spent (h)",
                    "Time Remaining (h)",  # Thêm cột thời gian còn lại vào hiển thị
                    "Time Efficiency",
                ]
            ]
        )

        # Hiển thị biểu đồ hiệu suất
        st.subheader("📈 Biểu đồ tỷ lệ hoàn thành công việc")

        # Tạo biểu đồ cột
        fig, ax = plt.subplots(figsize=(10, 6))

        # Sắp xếp theo tỷ lệ hoàn thành
        df_sorted = df_performance.sort_values(
            "Completion Rate Numeric", ascending=False
        )

        # Tạo biểu đồ
        bars = ax.bar(
            df_sorted["Assignee"], df_sorted["Completion Rate Numeric"], color="skyblue"
        )

        # Thêm nhãn giá trị
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 1,
                f"{height:.0f}%",
                ha="center",
                va="bottom",
            )

        ax.set_ylim(0, 110)  # Đặt giới hạn y để có không gian cho nhãn
        ax.set_ylabel("Tỷ lệ hoàn thành (%)")
        ax.set_title("Tỷ lệ hoàn thành công việc theo người")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        st.pyplot(fig)

        return df_performance
    else:
        st.info("Không có dữ liệu hiệu suất để hiển thị.")
        return pd.DataFrame()


def display_time_efficiency_chart(df_performance):
    """
    Hiển thị biểu đồ hiệu suất về thời gian

    Args:
        df_performance (pd.DataFrame): DataFrame chứa thông tin hiệu suất của team
    """
    if df_performance.empty:
        return

    st.subheader("⏱️ Biểu đồ hiệu suất về thời gian")

    # Tạo dữ liệu cho biểu đồ
    fig, ax = plt.subplots(figsize=(12, 6))

    # Sắp xếp theo thời gian ước tính
    df_sorted = df_performance.sort_values("Original Estimate", ascending=False)

    # Tạo biểu đồ cột ghép
    width = 0.35
    x = np.arange(len(df_sorted))

    # Chuyển đổi thời gian từ giây sang giờ
    estimate_hours = df_sorted["Original Estimate"] / 3600
    spent_hours = df_sorted["Time Spent"] / 3600

    bar1 = ax.bar(
        x - width / 2, estimate_hours, width, label="Ước tính (giờ)", color="#2196F3"
    )
    bar2 = ax.bar(
        x + width / 2, spent_hours, width, label="Đã dùng (giờ)", color="#FF9800"
    )

    # Thêm nhãn giá trị
    for bar in bar1:
        height = bar.get_height()
        if height > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.5,
                f"{height:.1f}h",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    for bar in bar2:
        height = bar.get_height()
        if height > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.5,
                f"{height:.1f}h",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    # Thêm tỷ lệ hiệu suất thời gian
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        efficiency = row["Time Efficiency Numeric"]
        color = "green" if efficiency <= 100 else "red"
        ax.text(
            i,
            max(estimate_hours.iloc[i], spent_hours.iloc[i]) + 2,
            f"{efficiency:.0f}%",
            ha="center",
            va="bottom",
            color=color,
            fontweight="bold",
        )

    ax.set_ylabel("Thời gian (giờ)")
    ax.set_title("So sánh thời gian ước tính và thời gian đã sử dụng")
    ax.set_xticks(x)
    ax.set_xticklabels(df_sorted["Assignee"], rotation=45, ha="right")
    ax.legend()

    # Đặt giới hạn y để có không gian cho nhãn
    y_max = max(max(estimate_hours), max(spent_hours)) * 1.3
    ax.set_ylim(0, y_max)

    plt.tight_layout()
    st.pyplot(fig)

    # Hiển thị biểu đồ hiệu suất thời gian
    fig2, ax2 = plt.subplots(figsize=(10, 6))

    # Sắp xếp theo hiệu suất thời gian
    df_time_sorted = df_performance.sort_values("Time Efficiency Numeric")

    # Tạo biểu đồ
    bars = ax2.bar(
        df_time_sorted["Assignee"],
        df_time_sorted["Time Efficiency Numeric"],
        color=[
            "green" if x <= 100 else "red"
            for x in df_time_sorted["Time Efficiency Numeric"]
        ],
    )

    # Thêm nhãn giá trị
    for bar in bars:
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1,
            f"{height:.0f}%",
            ha="center",
            va="bottom",
        )

    # Thêm đường tham chiếu 100%
    ax2.axhline(y=100, color="black", linestyle="--", alpha=0.7)

    ax2.set_ylabel("Hiệu suất thời gian (%)")
    ax2.set_title(
        "Hiệu suất thời gian theo người (Thời gian đã dùng / Thời gian ước tính)"
    )
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    st.pyplot(fig2)


def display_issue_type_chart(df_issues):
    """
    Hiển thị biểu đồ thống kê theo loại issue, phân chia riêng cho task và subtask

    Args:
        df_issues (pd.DataFrame): DataFrame chứa thông tin các issue
    """
    st.subheader("📊 Thống kê theo loại issue")

    # Tách DataFrame thành task và subtask
    tasks = df_issues[df_issues["is_subtask"] == False]
    subtasks = df_issues[df_issues["is_subtask"] == True]

    # Tạo layout 2 cột
    col1, col2 = st.columns((2, 3))

    with col1:
        st.write("#### Phân bố loại Task")
        if not tasks.empty:
            # hiện pie chart phân bố
            task_type_counts = tasks["issuetype"].value_counts()
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(
                task_type_counts.values,
                labels=task_type_counts.index,
                autopct="%1.1f%%",
            )
            st.pyplot(fig)
        else:
            st.info("Không có task nào trong sprint này.")

    with col2:
        st.write("#### Biểu đồ thể hiện số lượng trạng thái của các task và sub task")
        # Đếm số lượng trạng thái của các task và sub task
        task_status_counts = tasks["status"].value_counts()
        subtask_status_counts = subtasks["status"].value_counts()

        # Sắp xếp các trạng thái theo thứ tự mong muốn
        ordered_statuses = [
            "To Do",
            "Re Open",
            "In Progress",
            "Dev Done",
            "Test Done",
            "Deployed",
            "Done",
        ]
        task_status_counts = task_status_counts.reindex(ordered_statuses)
        subtask_status_counts = subtask_status_counts.reindex(ordered_statuses)

        # Tạo biểu đồ
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(
            task_status_counts.index,
            task_status_counts.values,
            color="skyblue",
            label="Task",
        )
        ax.bar(
            subtask_status_counts.index,
            subtask_status_counts.values,
            color="red",
            label="Sub Task",
        )
        ax.set_xlabel("Trạng thái")
        ax.set_ylabel("Số lượng")
        ax.set_title("Số lượng trạng thái của các task và sub task")
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig)


def display_sprint_overview(sprint, issues):
    """Display sprint overview information

    Args:
        sprint (dict): Sprint data
        issues (list): List of issues in the sprint
    """
    st.header("🏃‍♂️ Sprint Overview")

    try:
        # Hiển thị thông tin cơ bản của sprint
        st.write(f"Sprint: {sprint.get('name', 'Unknown')}")

        # Kiểm tra xem issues có dữ liệu không
        if not issues:
            st.warning("Không có issue nào trong sprint này.")
            return

        # Ẩn phần hiển thị cấu trúc dữ liệu issue đầu tiên
        # st.subheader("Cấu trúc dữ liệu issue đầu tiên")
        # st.json(issues[0])

        # Kiểm tra xem issue có thuộc tính 'fields' không
        if "fields" not in issues[0]:
            st.error(
                "Issue không có thuộc tính 'fields'. Cấu trúc dữ liệu không đúng định dạng."
            )
            return

        # Tạo DataFrame sử dụng hàm riêng
        df_issues = create_issues_dataframe(issues)

        # Hiển thị các chỉ số phân tích cho sprint
        display_sprint_metrics(df_issues, sprint)

        # Hiển thị biểu đồ thống kê theo loại issue
        display_issue_type_chart(df_issues)

        # Hiển thị hiệu suất của team và từng người
        df_performance = display_team_performance(df_issues)

        # Hiển thị biểu đồ hiệu suất tổng hợp cho các developer
        # display_developer_summary_chart(df_issues, df_performance)

        # Hiển thị biểu đồ hiệu suất về thời gian
        display_time_efficiency_chart(df_performance)

        # Hiển thị burndown chart dựa trên thời gian ước tính
        display_burndown_chart(df_issues, sprint)

        # Hiển thị burndown chart dựa trên số lượng task và subtask
        display_task_burndown_chart(df_issues, sprint)

        # Hiển thị DataFrame trong expander để tiết kiệm không gian
        with st.expander("Xem danh sách tất cả các issues"):
            # Thêm bộ lọc theo key
            filter_keys = st.text_input(
                "Lọc theo key (nhập các key, phân cách bằng dấu phẩy hoặc khoảng trắng):",
                help="Ví dụ: CLD-123, CLD-456",
            )

            # Xử lý các key được nhập
            if filter_keys:
                # Tách các key và loại bỏ khoảng trắng
                keys = [k.strip() for k in filter_keys.replace(",", " ").split()]

                # Lọc DataFrame theo các key
                if keys:
                    filtered_df = df_issues[df_issues["key"].isin(keys)]
                    st.write(
                        f"Đang hiển thị {len(filtered_df)} issues khớp với các key đã nhập."
                    )
                    st.dataframe(filtered_df)
                else:
                    st.dataframe(df_issues)
            else:
                # Hiển thị tất cả issues nếu không có key nào được nhập
                st.dataframe(df_issues)

            # Thêm tùy chọn tải xuống dữ liệu
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_issues.to_excel(writer, sheet_name="Issues", index=False)

            buffer.seek(0)

            st.download_button(
                label="Tải xuống dữ liệu Excel",
                data=buffer,
                file_name=f"sprint_issues_{sprint.get('name', 'Unknown').replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # Sprint goal
        if sprint.get("goal"):
            st.subheader("🎯 Sprint Goal")
            st.info(sprint.get("goal", "Không có mục tiêu được xác định"))

    except Exception as e:
        st.error(f"Không thể hiển thị thông tin sprint: {str(e)}")
        st.info("Vui lòng kiểm tra kết nối Jira của bạn hoặc cấu hình sprint.")

        # Hiển thị thông tin cơ bản nếu có
        if "name" in sprint:
            st.metric("Sprint", sprint["name"])
        if "goal" in sprint:
            st.subheader("Sprint Goal")
            st.info(sprint["goal"])


def display_developer_summary_chart(df_issues, df_performance):
    """
    Hiển thị biểu đồ hiệu suất tổng hợp cho các developer

    Args:
        df_issues (pd.DataFrame): DataFrame chứa thông tin các issue
        df_performance (pd.DataFrame): DataFrame chứa thông tin hiệu suất của team
    """
    if df_performance.empty:
        return

    st.subheader("🌟 Hiệu suất tổng hợp của developer")

    # Định nghĩa các trạng thái hoàn thành
    done_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]

    # Tạo DataFrame tổng hợp
    summary_data = []

    for assignee in df_performance["Assignee"].unique():
        # Lấy thông tin từ df_performance
        user_perf = df_performance[df_performance["Assignee"] == assignee].iloc[0]

        # Tính số lượng và hiệu suất thời gian cho sub-task
        user_subtasks = df_issues[
            (df_issues["assignee"] == assignee) & (df_issues["is_subtask"] == True)
        ]

        user_subtasks_done = user_subtasks[user_subtasks["status"].isin(done_statuses)]

        total_subtasks = len(user_subtasks)
        subtasks_done = len(user_subtasks_done)
        subtask_completion_rate = (
            (subtasks_done / total_subtasks * 100) if total_subtasks > 0 else 0
        )

        # Tính hiệu suất thời gian cho sub-task
        subtask_estimate = user_subtasks["timeoriginalestimate"].sum()
        subtask_spent = user_subtasks["timespent"].sum()
        subtask_time_efficiency = (
            (subtask_spent / subtask_estimate * 100) if subtask_estimate > 0 else 0
        )

        # Tính hiệu suất thời gian cho task (không phải sub-task)
        user_tasks = df_issues[
            (df_issues["assignee"] == assignee)
            & (df_issues["is_subtask"] == False)
            & (df_issues["issuetype"] != "Epic")
        ]

        task_estimate = user_tasks["timeoriginalestimate"].sum()
        task_spent = user_tasks["timespent"].sum()
        task_time_efficiency = (
            (task_spent / task_estimate * 100) if task_estimate > 0 else 0
        )

        # Chuẩn hóa các chỉ số (để biểu đồ radar dễ đọc)
        # Hiệu suất thời gian: <= 100% là tốt, > 100% là kém
        time_efficiency_score = (
            max(0, 100 - (user_perf["Time Efficiency Numeric"] - 100))
            if user_perf["Time Efficiency Numeric"] > 100
            else 100
        )

        task_time_efficiency_score = (
            max(0, 100 - (task_time_efficiency - 100))
            if task_time_efficiency > 100
            else 100
        )

        subtask_time_efficiency_score = (
            max(0, 100 - (subtask_time_efficiency - 100))
            if subtask_time_efficiency > 100
            else 100
        )

        summary_data.append(
            {
                "Developer": assignee,
                "Tasks": int(user_perf["Tasks"]),
                "Tasks Done": int(user_perf["Done"]),
                "Task Completion": user_perf["Completion Rate Numeric"],
                "Subtasks": total_subtasks,
                "Subtasks Done": subtasks_done,
                "Subtask Completion": subtask_completion_rate,
                "Time Efficiency": user_perf["Time Efficiency Numeric"],
                "Time Efficiency Score": time_efficiency_score,
                "Task Time Efficiency": task_time_efficiency,
                "Task Time Efficiency Score": task_time_efficiency_score,
                "Subtask Time Efficiency": subtask_time_efficiency,
                "Subtask Time Efficiency Score": subtask_time_efficiency_score,
            }
        )

    # Tạo DataFrame
    df_summary = pd.DataFrame(summary_data)

    # Hiển thị bảng tổng hợp
    st.dataframe(
        df_summary[
            [
                "Developer",
                "Tasks",
                "Tasks Done",
                "Task Completion",
                "Task Time Efficiency",
                "Subtasks",
                "Subtasks Done",
                "Subtask Completion",
                "Subtask Time Efficiency",
                "Time Efficiency",
            ]
        ]
        .rename(
            columns={
                "Task Completion": "Task Completion (%)",
                "Subtask Completion": "Subtask Completion (%)",
                "Time Efficiency": "Overall Time Efficiency (%)",
                "Task Time Efficiency": "Task Time Efficiency (%)",
                "Subtask Time Efficiency": "Subtask Time Efficiency (%)",
            }
        )
        .style.format(
            {
                "Task Completion (%)": "{:.0f}%",
                "Subtask Completion (%)": "{:.0f}%",
                "Overall Time Efficiency (%)": "{:.0f}%",
                "Task Time Efficiency (%)": "{:.0f}%",
                "Subtask Time Efficiency (%)": "{:.0f}%",
            }
        )
    )

    # Tạo biểu đồ tổng hợp dạng radar (spider chart)
    if len(df_summary) > 0:
        # Tạo biểu đồ radar
        fig = plt.figure(figsize=(10, 8))

        # Số lượng chỉ số
        categories = [
            "Task Completion",
            "Subtask Completion",
            "Task Time Efficiency Score",
            "Subtask Time Efficiency Score",
            "Overall Time Efficiency Score",
        ]
        N = len(categories)

        # Góc cho mỗi trục
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Đóng vòng tròn

        # Tạo subplot với tọa độ cực
        ax = plt.subplot(111, polar=True)

        # Đặt góc bắt đầu ở trên cùng
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        # Vẽ các trục
        plt.xticks(angles[:-1], categories)

        # Đặt giới hạn y từ 0 đến 100
        ax.set_ylim(0, 100)

        # Thêm nhãn y
        ax.set_rlabel_position(0)
        plt.yticks(
            [25, 50, 75, 100], ["25%", "50%", "75%", "100%"], color="grey", size=8
        )

        # Màu sắc cho mỗi developer
        colors = plt.cm.tab10(np.linspace(0, 1, len(df_summary)))

        # Vẽ dữ liệu cho mỗi developer
        for i, (idx, row) in enumerate(df_summary.iterrows()):
            values = [
                row["Task Completion"],
                row["Subtask Completion"],
                row["Task Time Efficiency Score"],
                row["Subtask Time Efficiency Score"],
                row["Time Efficiency Score"],
            ]
            values += values[:1]  # Đóng vòng tròn

            # Vẽ đường
            ax.plot(
                angles,
                values,
                linewidth=2,
                linestyle="solid",
                color=colors[i],
                label=row["Developer"],
            )
            # Tô màu vùng
            ax.fill(angles, values, color=colors[i], alpha=0.1)

        # Thêm chú thích
        plt.legend(loc="upper right", bbox_to_anchor=(0.1, 0.1))

        plt.title("Hiệu suất tổng hợp của developer", size=15, y=1.1)
        st.pyplot(fig)

        # Tạo biểu đồ cột ghép cho số lượng task và subtask
        fig2, ax2 = plt.subplots(figsize=(12, 6))

        # Sắp xếp theo tổng số task
        df_sorted = df_summary.sort_values("Tasks", ascending=False)

        # Vị trí các cột
        x = np.arange(len(df_sorted))
        width = 0.2

        # Vẽ các cột
        ax2.bar(
            x - width * 1.5, df_sorted["Tasks"], width, label="Tasks", color="#2196F3"
        )
        ax2.bar(
            x - width / 2,
            df_sorted["Tasks Done"],
            width,
            label="Tasks Done",
            color="#4CAF50",
        )
        ax2.bar(
            x + width / 2,
            df_sorted["Subtasks"],
            width,
            label="Subtasks",
            color="#FF9800",
        )
        ax2.bar(
            x + width * 1.5,
            df_sorted["Subtasks Done"],
            width,
            label="Subtasks Done",
            color="#9C27B0",
        )

        # Thêm nhãn và tiêu đề
        ax2.set_xlabel("Developer")
        ax2.set_ylabel("Số lượng")
        ax2.set_title("Số lượng task và subtask theo developer")
        ax2.set_xticks(x)
        ax2.set_xticklabels(df_sorted["Developer"], rotation=45, ha="right")
        ax2.legend()

        plt.tight_layout()
        st.pyplot(fig2)

        # Tạo biểu đồ hiệu suất thời gian cho task và subtask
        fig3, ax3 = plt.subplots(figsize=(12, 6))

        # Sắp xếp theo hiệu suất thời gian tổng thể
        df_time_sorted = df_summary.sort_values("Time Efficiency")

        # Vị trí các cột
        x = np.arange(len(df_time_sorted))
        width = 0.25

        # Vẽ các cột
        ax3.bar(
            x - width,
            df_time_sorted["Task Time Efficiency"],
            width,
            label="Task Time Efficiency",
            color=(
                "#4CAF50"
                if all(df_time_sorted["Task Time Efficiency"] <= 100)
                else [
                    "green" if x <= 100 else "red"
                    for x in df_time_sorted["Task Time Efficiency"]
                ]
            ),
        )
        ax3.bar(
            x,
            df_time_sorted["Subtask Time Efficiency"],
            width,
            label="Subtask Time Efficiency",
            color=(
                "#2196F3"
                if all(df_time_sorted["Subtask Time Efficiency"] <= 100)
                else [
                    "blue" if x <= 100 else "orange"
                    for x in df_time_sorted["Subtask Time Efficiency"]
                ]
            ),
        )
        ax3.bar(
            x + width,
            df_time_sorted["Time Efficiency"],
            width,
            label="Overall Time Efficiency",
            color=(
                "#9C27B0"
                if all(df_time_sorted["Time Efficiency"] <= 100)
                else [
                    "purple" if x <= 100 else "red"
                    for x in df_time_sorted["Time Efficiency"]
                ]
            ),
        )

        # Thêm đường tham chiếu 100%
        ax3.axhline(y=100, color="black", linestyle="--", alpha=0.7)

        # Thêm nhãn và tiêu đề
        ax3.set_xlabel("Developer")
        ax3.set_ylabel("Hiệu suất thời gian (%)")
        ax3.set_title("So sánh hiệu suất thời gian giữa task và subtask")
        ax3.set_xticks(x)
        ax3.set_xticklabels(df_time_sorted["Developer"], rotation=45, ha="right")
        ax3.legend()

        plt.tight_layout()
        st.pyplot(fig3)


def display_burndown_chart(df_issues, sprint):
    """
    Hiển thị burndown chart cho sprint dựa trên dữ liệu thực tế từ API
    và tính toán dựa trên timeoriginalestimate

    Args:
        df_issues (pd.DataFrame): DataFrame chứa thông tin các issue
        sprint (dict): Thông tin về sprint
    """
    st.subheader("📉 Sprint Burndown Chart")

    # Kiểm tra xem sprint có thông tin thời gian không
    if not (sprint.get("startDate") and sprint.get("endDate")):
        st.warning("Không có đủ thông tin thời gian để tạo burndown chart.")
        return

    try:
        # Chuyển đổi chuỗi thời gian thành đối tượng datetime
        start_date = datetime.strptime(sprint.get("startDate"), "%Y-%m-%dT%H:%M:%S.%fZ")
        end_date = datetime.strptime(sprint.get("endDate"), "%Y-%m-%dT%H:%M:%S.%fZ")

        # Tính tổng số ngày của sprint
        total_days = (end_date - start_date).days + 1

        # Tạo danh sách các ngày trong sprint
        sprint_days = [start_date + timedelta(days=i) for i in range(total_days)]

        # Tính tổng số giờ ước tính cho tất cả các issue
        total_estimate_hours = df_issues["timeoriginalestimate"].sum() / 3600

        # Tạo dữ liệu cho đường lý tưởng (ideal burndown)
        ideal_burndown = [
            total_estimate_hours * (1 - i / (total_days - 1)) for i in range(total_days)
        ]

        # Tạo DataFrame cho biểu đồ
        burndown_data = pd.DataFrame(
            {
                "Ngày": sprint_days,
                "Lý tưởng": ideal_burndown,
                "Thực tế": [None] * total_days,  # Sẽ được cập nhật sau
            }
        )

        # Ngày hiện tại
        today = datetime.now()

        # Tính số giờ còn lại thực tế cho mỗi ngày đã qua
        # Trong thực tế, chúng ta chỉ có dữ liệu cho ngày hiện tại
        # Vì vậy, chúng ta sẽ sử dụng giá trị hiện tại cho tất cả các ngày đã qua

        # Tính tổng số giờ còn lại dựa trên remainingestimate
        remaining_estimate_hours = df_issues["remainingestimate"].sum() / 3600

        # Cập nhật dữ liệu thực tế
        for i, day in enumerate(sprint_days):
            if day <= today:
                if i == len(sprint_days) - 1 or day.date() == today.date():
                    # Ngày hiện tại hoặc ngày cuối cùng: sử dụng giá trị thực tế
                    burndown_data.at[i, "Thực tế"] = remaining_estimate_hours
                else:
                    # Ngày trong quá khứ: nội suy tuyến tính giữa ngày đầu tiên và ngày hiện tại
                    days_passed = (day - start_date).days
                    days_total = (today - start_date).days
                    if days_total > 0:
                        ratio = days_passed / days_total
                        burndown_data.at[i, "Thực tế"] = (
                            total_estimate_hours
                            - ratio * (total_estimate_hours - remaining_estimate_hours)
                        )
                    else:
                        burndown_data.at[i, "Thực tế"] = total_estimate_hours

        # Tạo biểu đồ
        fig, ax = plt.subplots(figsize=(12, 6))

        # Vẽ đường lý tưởng
        ax.plot(
            burndown_data["Ngày"],
            burndown_data["Lý tưởng"],
            marker="o",
            linestyle="-",
            color="#2196F3",
            label="Lý tưởng",
        )

        # Vẽ đường thực tế
        ax.plot(
            burndown_data["Ngày"][: today.day - start_date.day + 1],
            burndown_data["Thực tế"][: today.day - start_date.day + 1],
            marker="o",
            linestyle="-",
            color="#F44336",
            label="Thực tế",
        )

        # Thêm đường tham chiếu 0
        ax.axhline(y=0, color="black", linestyle="--", alpha=0.3)

        # Thêm đường dọc cho ngày hiện tại
        if start_date <= today <= end_date:
            ax.axvline(
                x=today, color="green", linestyle="--", alpha=0.5, label="Hôm nay"
            )

        # Định dạng trục x để hiển thị ngày
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d/%m"))
        plt.xticks(rotation=45)

        # Thêm nhãn và tiêu đề
        ax.set_xlabel("Ngày")
        ax.set_ylabel("Giờ còn lại")
        ax.set_title("Sprint Burndown Chart")
        ax.legend()

        # Đảm bảo y không âm
        ax.set_ylim(bottom=0)

        plt.tight_layout()
        st.pyplot(fig)

        # Hiển thị thông tin chi tiết
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tổng thời gian ước tính", f"{total_estimate_hours:.1f} giờ")
        with col2:
            st.metric("Thời gian còn lại", f"{remaining_estimate_hours:.1f} giờ")
        with col3:
            progress_percent = (
                (
                    (total_estimate_hours - remaining_estimate_hours)
                    / total_estimate_hours
                    * 100
                )
                if total_estimate_hours > 0
                else 0
            )
            st.metric("Tiến độ hoàn thành", f"{progress_percent:.1f}%")

        # Thêm giải thích
        st.info(
            """
        **Giải thích Burndown Chart:**
        - **Đường màu xanh (Lý tưởng)**: Thể hiện tốc độ lý tưởng mà team nên hoàn thành công việc.
        - **Đường màu đỏ (Thực tế)**: Thể hiện thời gian còn lại thực tế dựa trên dữ liệu từ Jira.
        - Nếu đường thực tế nằm **trên** đường lý tưởng: Team đang làm việc **chậm hơn** kế hoạch.
        - Nếu đường thực tế nằm **dưới** đường lý tưởng: Team đang làm việc **nhanh hơn** kế hoạch.
        
        *Lưu ý: Dữ liệu thực tế được tính dựa trên `timeoriginalestimate` và `remainingestimate` từ Jira API.*
        """
        )

    except Exception as e:
        st.error(f"Không thể tạo burndown chart: {str(e)}")
        import traceback

        st.error(traceback.format_exc())


def display_task_burndown_chart(df_issues, sprint):
    """
    Hiển thị burndown chart dựa trên số lượng task và subtask

    Args:
        df_issues (pd.DataFrame): DataFrame chứa thông tin các issue
        sprint (dict): Thông tin về sprint
    """
    st.subheader("📉 Sprint Burndown Chart (Số lượng Task)")

    # Kiểm tra xem sprint có thông tin thời gian không
    if not (sprint.get("startDate") and sprint.get("endDate")):
        st.warning("Không có đủ thông tin thời gian để tạo burndown chart.")
        return

    try:
        # Chuyển đổi chuỗi thời gian thành đối tượng datetime
        start_date = datetime.strptime(sprint.get("startDate"), "%Y-%m-%dT%H:%M:%S.%fZ")
        end_date = datetime.strptime(sprint.get("endDate"), "%Y-%m-%dT%H:%M:%S.%fZ")

        # Tính tổng số ngày của sprint
        total_days = (end_date - start_date).days + 1

        # Tạo danh sách các ngày trong sprint
        sprint_days = [start_date + timedelta(days=i) for i in range(total_days)]

        # Định nghĩa các trạng thái hoàn thành
        done_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]

        # Tính tổng số task và subtask
        tasks = df_issues[
            (df_issues["issuetype"] != "Epic") & (df_issues["is_subtask"] == False)
        ]
        subtasks = df_issues[df_issues["is_subtask"] == True]

        total_tasks = len(tasks)
        total_subtasks = len(subtasks)
        total_issues = total_tasks + total_subtasks

        # Tính số task và subtask đã hoàn thành
        tasks_done = len(tasks[tasks["status"].isin(done_statuses)])
        subtasks_done = len(subtasks[subtasks["status"].isin(done_statuses)])
        total_done = tasks_done + subtasks_done

        # Tính số task và subtask còn lại
        remaining_issues = total_issues - total_done

        # Tạo dữ liệu cho đường lý tưởng (ideal burndown)
        ideal_burndown = [
            total_issues * (1 - i / (total_days - 1)) for i in range(total_days)
        ]

        # Tạo DataFrame cho biểu đồ
        burndown_data = pd.DataFrame(
            {
                "Ngày": sprint_days,
                "Lý tưởng": ideal_burndown,
                "Thực tế": [None] * total_days,  # Sẽ được cập nhật sau
            }
        )

        # Ngày hiện tại
        today = datetime.now()

        # Cập nhật dữ liệu thực tế
        for i, day in enumerate(sprint_days):
            if day <= today:
                if i == len(sprint_days) - 1 or day.date() == today.date():
                    # Ngày hiện tại hoặc ngày cuối cùng: sử dụng giá trị thực tế
                    burndown_data.at[i, "Thực tế"] = remaining_issues
                else:
                    # Ngày trong quá khứ: nội suy tuyến tính giữa ngày đầu tiên và ngày hiện tại
                    days_passed = (day - start_date).days
                    days_total = (today - start_date).days
                    if days_total > 0:
                        ratio = days_passed / days_total
                        burndown_data.at[i, "Thực tế"] = (
                            total_issues - ratio * total_done
                        )
                    else:
                        burndown_data.at[i, "Thực tế"] = total_issues

        # Tạo biểu đồ
        fig, ax = plt.subplots(figsize=(12, 6))

        # Vẽ đường lý tưởng
        ax.plot(
            burndown_data["Ngày"],
            burndown_data["Lý tưởng"],
            marker="o",
            linestyle="-",
            color="#2196F3",
            label="Lý tưởng",
        )

        # Vẽ đường thực tế
        ax.plot(
            burndown_data["Ngày"][: today.day - start_date.day + 1],
            burndown_data["Thực tế"][: today.day - start_date.day + 1],
            marker="o",
            linestyle="-",
            color="#F44336",
            label="Thực tế",
        )

        # Thêm đường tham chiếu 0
        ax.axhline(y=0, color="black", linestyle="--", alpha=0.3)

        # Thêm đường dọc cho ngày hiện tại
        if start_date <= today <= end_date:
            ax.axvline(
                x=today, color="green", linestyle="--", alpha=0.5, label="Hôm nay"
            )

        # Định dạng trục x để hiển thị ngày
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d/%m"))
        plt.xticks(rotation=45)

        # Thêm nhãn và tiêu đề
        ax.set_xlabel("Ngày")
        ax.set_ylabel("Số lượng task còn lại")
        ax.set_title("Sprint Burndown Chart (Số lượng Task)")
        ax.legend()

        # Đảm bảo y không âm
        ax.set_ylim(bottom=0)

        plt.tight_layout()
        st.pyplot(fig)

        # Hiển thị thông tin chi tiết
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tổng số task và subtask", f"{total_issues}")
            st.metric(
                "Task", f"{total_tasks}", help="Số lượng task (không bao gồm Epic)"
            )
            st.metric("Subtask", f"{total_subtasks}")
        with col2:
            st.metric("Đã hoàn thành", f"{total_done}")
            st.metric("Task đã hoàn thành", f"{tasks_done}")
            st.metric("Subtask đã hoàn thành", f"{subtasks_done}")
        with col3:
            st.metric("Còn lại", f"{remaining_issues}")
            st.metric("Task còn lại", f"{total_tasks - tasks_done}")
            st.metric("Subtask còn lại", f"{total_subtasks - subtasks_done}")

        # Tính tỷ lệ hoàn thành
        completion_rate = (total_done / total_issues * 100) if total_issues > 0 else 0
        task_completion_rate = (
            (tasks_done / total_tasks * 100) if total_tasks > 0 else 0
        )
        subtask_completion_rate = (
            (subtasks_done / total_subtasks * 100) if total_subtasks > 0 else 0
        )

        # Hiển thị tỷ lệ hoàn thành
        st.write("#### Tỷ lệ hoàn thành")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tổng thể", f"{completion_rate:.1f}%")
        with col2:
            st.metric("Task", f"{task_completion_rate:.1f}%")
        with col3:
            st.metric("Subtask", f"{subtask_completion_rate:.1f}%")

        # Thêm giải thích
        st.info(
            """
        **Giải thích Burndown Chart (Số lượng Task):**
        - **Đường màu xanh (Lý tưởng)**: Thể hiện tốc độ lý tưởng mà team nên hoàn thành các task và subtask.
        - **Đường màu đỏ (Thực tế)**: Thể hiện số lượng task và subtask còn lại thực tế.
        - Nếu đường thực tế nằm **trên** đường lý tưởng: Team đang hoàn thành task **chậm hơn** kế hoạch.
        - Nếu đường thực tế nằm **dưới** đường lý tưởng: Team đang hoàn thành task **nhanh hơn** kế hoạch.
        """
        )

    except Exception as e:
        st.error(f"Không thể tạo burndown chart theo số lượng task: {str(e)}")
        import traceback

        st.error(traceback.format_exc())


# Tìm index của "CLD Sprint 10" nếu có trong danh sách
default_index = 0
sprint_options = [
    "CLD Sprint 10",
    "CLD Sprint 11",
    "CLD Sprint 12",
]  # Thay thế bằng danh sách tên sprint của bạn
if "CLD Sprint 10" in sprint_options:
    default_index = sprint_options.index("CLD Sprint 10")
