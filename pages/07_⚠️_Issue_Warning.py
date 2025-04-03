import streamlit as st
from datetime import datetime, timedelta
from src.services.jira.jira_client_facade import JiraClientFacade
from src.config import DEFAULT_PROJECT

# Thiết lập cấu hình trang
st.set_page_config(
    page_title="Cảnh Báo Issue | Jira Analytics",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="auto",
)

# Khởi tạo client
jira_client = JiraClientFacade()

# CSS cho bảng
TAILWIND_TABLE_CSS = """
<style>
    /* Container chính */
    .main .block-container {
        max-width: 100%;
        padding: 1rem;
    }
    
    /* Bảng */
    .stDataFrame {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        width: 100%;
    }
    
    /* Bảng bên trong */
    .stDataFrame table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    
    /* Header của bảng */
    .stDataFrame th {
        background-color: #f3f4f6;
        padding: 0.75rem;
        text-align: left;
        font-weight: 600;
        color: #374151;
        border-bottom: 2px solid #e5e7eb;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* Cell của bảng */
    .stDataFrame td {
        padding: 0.75rem;
        border-bottom: 1px solid #e5e7eb;
        color: #4b5563;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* Hover effect */
    .stDataFrame tr:hover {
        background-color: #f9fafb;
    }
    
    /* Điều chỉnh chiều rộng các cột */
    .stDataFrame th:nth-child(1) { width: 10%; }  /* Key */
    .stDataFrame th:nth-child(2) { width: 25%; }  /* Summary */
    .stDataFrame th:nth-child(3) { width: 10%; }  /* Due Date */
    .stDataFrame th:nth-child(4) { width: 15%; }  /* Status */
    .stDataFrame th:nth-child(5) { width: 15%; }  /* Assignee */
    .stDataFrame th:nth-child(6) { width: 10%; }  /* Priority */
    .stDataFrame th:nth-child(7) { width: 10%; }  /* Created */
    .stDataFrame th:nth-child(8) { width: 10%; }  /* Updated */
</style>
"""


def get_all_sprints(project_key):
    """Lấy danh sách tất cả sprint của dự án"""
    return jira_client.get_all_sprints(project_key)


def get_active_sprint(project_key):
    """Lấy sprint đang active của dự án"""
    return jira_client.get_active_sprint(project_key)


def get_sprint_issues(sprint_id, project_key):
    """Lấy danh sách issues của sprint với các trường cần thiết"""
    fields = [
        "summary",
        "issuetype",
        "priority",
        "assignee",
        "status",
        "duedate",
        "created",
        "updated",
        "subtasks",
        "timeestimate",
        "timeoriginalestimate",
        "worklog",
    ]
    return jira_client.get_sprint_issues(
        sprint_id, fields=fields, project_key=project_key
    )


def filter_issues(issues):
    """Lọc các issue theo điều kiện"""
    filtered_issues = []
    for issue in issues:
        fields = issue.get("fields", {})

        # Kiểm tra loại issue
        issue_type = fields.get("issuetype", {}).get("name", "")
        if issue_type.lower() == "epic":
            continue

        # Kiểm tra có subtasks không
        subtasks = fields.get("subtasks", [])
        if subtasks and len(subtasks) > 0:
            continue

        # Kiểm tra có due date không
        due_date = fields.get("duedate")
        if not due_date:
            continue

        filtered_issues.append(issue)

    return filtered_issues


def calculate_issue_status(issue):
    """Tính toán trạng thái của issue dựa trên due date"""
    fields = issue.get("fields", {})
    due_date = datetime.strptime(fields.get("duedate"), "%Y-%m-%d")
    status = fields.get("status", {}).get("name", "").lower()

    # Các trạng thái hoàn thành
    completed_statuses = ["done", "dev done", "test done", "deployed"]

    # Tính số ngày còn lại
    days_remaining = (due_date - datetime.now()).days

    # Xác định trạng thái
    if status in completed_statuses:
        return "✅ Hoàn thành"
    elif days_remaining < 0:
        return f"❌ Quá hạn ({abs(days_remaining)} ngày)"
    elif days_remaining <= 3:
        return f"⚠️ Sắp quá hạn ({days_remaining} ngày)"
    else:
        return f"🔄 Đang thực hiện ({days_remaining} ngày)"


def format_date(date_str):
    """Format ngày tháng"""
    if not date_str:
        return "N/A"
    try:
        date = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
        return date.strftime("%d/%m/%Y")
    except:
        return date_str


def get_status_summary(issues):
    """Tính toán thống kê trạng thái của các issue"""
    summary = {
        "total": len(issues),
        "completed": 0,
        "overdue": 0,
        "warning": 0,
        "in_progress": 0,
    }

    for issue in issues:
        status = calculate_issue_status(issue)
        if "✅" in status:
            summary["completed"] += 1
        elif "❌" in status:
            summary["overdue"] += 1
        elif "⚠️" in status:
            summary["warning"] += 1
        else:
            summary["in_progress"] += 1

    return summary


def get_special_issues(issues):
    """Lấy danh sách các issue đặc biệt cần cảnh báo"""
    unassigned_issues = []
    unestimated_issues = []
    completed_without_worklog = []

    for issue in issues:
        fields = issue.get("fields", {})
        status = fields.get("status", {}).get("name", "").lower()

        # Kiểm tra issue chưa gán người
        assignee = fields.get("assignee", {})
        if not assignee or not assignee.get("displayName"):
            unassigned_issues.append(issue)
            continue

        # Kiểm tra issue chưa estimate
        time_estimate = fields.get("timeestimate", 0)
        time_original = fields.get("timeoriginalestimate", 0)
        if not time_estimate and not time_original:
            unestimated_issues.append(issue)
            continue

        # Kiểm tra issue hoàn thành nhưng không có worklog
        if status in ["done", "dev done", "test done", "deployed"]:
            worklog = fields.get("worklog", {})
            worklog_entries = worklog.get("worklogs", [])
            if not worklog_entries:
                completed_without_worklog.append(issue)

    return {
        "unassigned": unassigned_issues,
        "unestimated": unestimated_issues,
        "completed_without_worklog": completed_without_worklog,
    }


def display_special_issues(issues):
    """Hiển thị các danh sách issue đặc biệt"""
    special_issues = get_special_issues(issues)

    # Chuẩn bị dữ liệu cho bảng chính
    main_table_data = []
    for issue in issues:
        fields = issue.get("fields", {})
        status = calculate_issue_status(issue)
        assignee = fields.get("assignee", {})
        due_date = fields.get("duedate", "")

        main_table_data.append(
            {
                "Key": issue.get("key", ""),
                "Summary": fields.get("summary", ""),
                "Due Date": format_date(due_date),
                "Due Date Raw": due_date,  # Thêm trường raw để sort
                "Status": status,
                "Assignee": assignee.get("displayName", "Chưa gán"),
                "Priority": fields.get("priority", {}).get("name", "N/A"),
                "Created": format_date(fields.get("created", "")),
                "Updated": format_date(fields.get("updated", "")),
            }
        )

    # Sắp xếp theo due date
    main_table_data.sort(key=lambda x: x["Due Date Raw"])

    # Tạo tabs cho từng loại issue
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            f"📋 Danh Sách Issue Theo Due Date ({len(issues)})",
            f"👤 Chưa gán người ({len(special_issues['unassigned'])})",
            f"⏰ Chưa estimate ({len(special_issues['unestimated'])})",
            f"🔍 Hoàn thành không có worklog ({len(special_issues['completed_without_worklog'])})",
        ]
    )

    # Tab 1: Danh sách issue theo due date
    with tab1:
        # Xóa trường Due Date Raw trước khi hiển thị
        display_data = [
            {k: v for k, v in item.items() if k != "Due Date Raw"}
            for item in main_table_data
        ]
        st.dataframe(
            display_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Key": st.column_config.TextColumn("Key", width="small"),
                "Summary": st.column_config.TextColumn("Summary", width="large"),
                "Due Date": st.column_config.TextColumn("Due Date", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
                "Priority": st.column_config.TextColumn("Priority", width="small"),
                "Created": st.column_config.TextColumn("Created", width="small"),
                "Updated": st.column_config.TextColumn("Updated", width="small"),
            },
        )

    # Tab 2: Issues chưa gán người
    with tab2:
        if special_issues["unassigned"]:
            table_data = []
            for issue in special_issues["unassigned"]:
                fields = issue.get("fields", {})
                table_data.append(
                    {
                        "Key": issue.get("key", ""),
                        "Summary": fields.get("summary", ""),
                        "Due Date": format_date(fields.get("duedate", "")),
                        "Status": fields.get("status", {}).get("name", ""),
                        "Priority": fields.get("priority", {}).get("name", "N/A"),
                        "Created": format_date(fields.get("created", "")),
                        "Updated": format_date(fields.get("updated", "")),
                    }
                )
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Key": st.column_config.TextColumn("Key", width="small"),
                    "Summary": st.column_config.TextColumn("Summary", width="large"),
                    "Due Date": st.column_config.TextColumn("Due Date", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                    "Priority": st.column_config.TextColumn("Priority", width="small"),
                    "Created": st.column_config.TextColumn("Created", width="small"),
                    "Updated": st.column_config.TextColumn("Updated", width="small"),
                },
            )
        else:
            st.success("Không có issue nào chưa gán người!")

    # Tab 3: Issues chưa estimate
    with tab3:
        if special_issues["unestimated"]:
            table_data = []
            for issue in special_issues["unestimated"]:
                fields = issue.get("fields", {})
                assignee = fields.get("assignee", {})
                table_data.append(
                    {
                        "Key": issue.get("key", ""),
                        "Summary": fields.get("summary", ""),
                        "Due Date": format_date(fields.get("duedate", "")),
                        "Status": fields.get("status", {}).get("name", ""),
                        "Assignee": assignee.get("displayName", "Chưa gán"),
                        "Priority": fields.get("priority", {}).get("name", "N/A"),
                        "Created": format_date(fields.get("created", "")),
                        "Updated": format_date(fields.get("updated", "")),
                    }
                )
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Key": st.column_config.TextColumn("Key", width="small"),
                    "Summary": st.column_config.TextColumn("Summary", width="large"),
                    "Due Date": st.column_config.TextColumn("Due Date", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                    "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
                    "Priority": st.column_config.TextColumn("Priority", width="small"),
                    "Created": st.column_config.TextColumn("Created", width="small"),
                    "Updated": st.column_config.TextColumn("Updated", width="small"),
                },
            )
        else:
            st.success("Không có issue nào chưa estimate!")

    # Tab 4: Issues hoàn thành không có worklog
    with tab4:
        if special_issues["completed_without_worklog"]:
            table_data = []
            for issue in special_issues["completed_without_worklog"]:
                fields = issue.get("fields", {})
                assignee = fields.get("assignee", {})
                table_data.append(
                    {
                        "Key": issue.get("key", ""),
                        "Summary": fields.get("summary", ""),
                        "Due Date": format_date(fields.get("duedate", "")),
                        "Status": fields.get("status", {}).get("name", ""),
                        "Assignee": assignee.get("displayName", "Chưa gán"),
                        "Priority": fields.get("priority", {}).get("name", "N/A"),
                        "Created": format_date(fields.get("created", "")),
                        "Updated": format_date(fields.get("updated", "")),
                    }
                )
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Key": st.column_config.TextColumn("Key", width="small"),
                    "Summary": st.column_config.TextColumn("Summary", width="large"),
                    "Due Date": st.column_config.TextColumn("Due Date", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                    "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
                    "Priority": st.column_config.TextColumn("Priority", width="small"),
                    "Created": st.column_config.TextColumn("Created", width="small"),
                    "Updated": st.column_config.TextColumn("Updated", width="small"),
                },
            )
        else:
            st.success("Không có issue nào hoàn thành mà không có worklog!")


def main():
    st.title("⚠️ Cảnh Báo Issue trong Sprint")

    # Thêm CSS cho bảng
    st.markdown(TAILWIND_TABLE_CSS, unsafe_allow_html=True)

    # Lấy danh sách sprint
    sprints = get_all_sprints(DEFAULT_PROJECT)
    if not sprints:
        st.error("Không tìm thấy sprint nào!")
        return

    # Sắp xếp sprints: Active first, then by name
    sprint_options = []
    for sprint in sprints:
        state = sprint.get("state", "").lower()
        name = sprint.get("name", "")
        display_name = f"{name} ({state})"
        sprint_options.append(
            {"id": sprint["id"], "name": name, "state": state, "display": display_name}
        )

    # Sắp xếp sprints
    sprint_options.sort(
        key=lambda x: (
            0 if x["state"] == "active" else (1 if x["state"] == "future" else 2),
            x["name"],
        )
    )

    # Tìm sprint active
    active_sprint = next((s for s in sprint_options if s["state"] == "active"), None)
    active_sprint_index = sprint_options.index(active_sprint) if active_sprint else 0

    # Selection với sprint active được chọn mặc định
    selected_sprint_idx = st.selectbox(
        "Chọn Sprint",
        options=range(len(sprint_options)),
        format_func=lambda i: sprint_options[i]["display"],
        index=active_sprint_index,
        key="selected_sprint_idx",
    )

    selected_sprint = sprint_options[selected_sprint_idx]

    # Lấy danh sách issues
    issues = get_sprint_issues(selected_sprint["id"], DEFAULT_PROJECT)
    if not issues:
        st.warning("Không có issue nào trong sprint!")
        return

    # Lọc issues theo điều kiện
    filtered_issues = filter_issues(issues)
    if not filtered_issues:
        st.warning("Không có issue nào thỏa mãn điều kiện!")
        return

    # Hiển thị thống kê tổng quan
    status_summary = get_status_summary(filtered_issues)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Tổng số issue", status_summary["total"])
    with col2:
        st.metric("Hoàn thành", status_summary["completed"])
    with col3:
        st.metric("Quá hạn", status_summary["overdue"])
    with col4:
        st.metric("Sắp quá hạn", status_summary["warning"])

    # Hiển thị các danh sách issue
    display_special_issues(filtered_issues)


if __name__ == "__main__":
    main()
