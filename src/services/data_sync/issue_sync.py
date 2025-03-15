import streamlit as st
import re
import json
from src.services.mongodb_client import is_running_in_streamlit
from src.config import DEBUG
from datetime import datetime


def get_default_issue_fields():
    """Trả về danh sách mặc định các trường cần lấy từ Jira API

    Returns:
        list: Danh sách các trường cần lấy
    """
    return [
        "summary",
        "status",
        "assignee",
        "issuetype",
        "priority",
        "created",
        "updated",
        "customfield_10160",  # Show in Dashboard
        "customfield_10130",  # Popup
        "customfield_10159",  # Steve Estimate
        "subtasks",  # Thông tin về sub-tasks
        "parent",  # Thông tin về parent nếu là sub-task
        "duedate",  # Ngày đến hạn
        "resolutiondate",  # Ngày hoàn thành
        "timeoriginalestimate",  # Thời gian ước tính ban đầu
        "timeestimate",  # Thời gian ước tính còn lại
        "timespent",  # Thời gian đã dùng
        "worklog",  # Nhật ký công việc
        "customfield_10092",  # Customer
        "customfield_10132",  # Feature
        "customfield_10031",  # Tester
        "comment",  # Lấy comments để tìm thông tin commit
        "development",  # Thông tin phát triển có thể chứa commit
        "changelog",  # Lấy changelog để tìm thời gian chuyển trạng thái
    ]


def sync_sprint_issues(
    jira_client,
    mongo_client,
    sprint_id,
    sprint_info=None,
    fields=None,
    with_progress=True,
):
    """Đồng bộ issues của một sprint

    Args:
        jira_client: Client kết nối đến Jira
        mongo_client: Client kết nối đến MongoDB
        sprint_id (int): ID của sprint
        sprint_info (dict, optional): Thông tin sprint. Nếu không cung cấp sẽ tự động lấy từ API
        fields (list, optional): Danh sách các trường cần lấy
        with_progress (bool): Hiển thị tiến trình hay không

    Returns:
        list: Danh sách issues đã đồng bộ
    """
    # Sử dụng danh sách trường mặc định nếu không được cung cấp
    if fields is None:
        fields = get_default_issue_fields()

    # Lấy thông tin sprint nếu chưa có
    if sprint_info is None:
        try:
            sprint_info = jira_client.sprint_client.get(
                f"sprint/{sprint_id}", use_agile_api=True
            ).json()
        except Exception as e:
            if is_running_in_streamlit():
                st.error(f"Lỗi khi lấy thông tin sprint {sprint_id}: {str(e)}")
            return []

    sprint_name = sprint_info.get("name", f"Sprint {sprint_id}")

    # Lấy danh sách issues
    try:
        progress_text = f"Đang đồng bộ issues của sprint {sprint_name}..."
        progress_bar = None

        if with_progress and is_running_in_streamlit():
            st.toast(progress_text, icon="ℹ️")
            progress_bar = st.progress(0)

        # Không giới hạn số lượng issues (max_issues=-1 sẽ lấy tất cả)
        issues = jira_client.get_sprint_issues(sprint_id, fields=fields, max_issues=-1)

        if not issues:
            if is_running_in_streamlit():
                st.warning(f"Không có issues nào trong sprint {sprint_name}")
            return []

        # Lọc bỏ các issue không có quyền truy cập
        valid_issues = []
        no_access_count = 0

        for issue in issues:
            # Kiểm tra xem issue có thông báo lỗi quyền truy cập không
            if issue.get("key") and issue.get("fields") is not None:
                # Thêm issue hợp lệ vào danh sách
                valid_issues.append(issue)
            else:
                # Đếm số issue không có quyền truy cập
                no_access_count += 1
                if is_running_in_streamlit():
                    st.toast(
                        f"Không có quyền truy cập issue {issue.get('key', 'Unknown')}",
                        icon="⚠️",
                    )

        if no_access_count > 0 and is_running_in_streamlit():
            st.warning(f"Đã bỏ qua {no_access_count} issues do không có quyền truy cập")

        # Cập nhật danh sách issues
        issues = valid_issues
        total_issues = len(issues)

        # Xử lý chi tiết từng issue
        for i, issue in enumerate(issues):
            issue_key = issue.get("key")

            if with_progress and progress_bar is not None and is_running_in_streamlit():
                # Cập nhật tiến trình
                progress = min((i + 1) / total_issues, 1.0)
                progress_bar.progress(
                    progress, text=f"Đồng bộ {i+1}/{total_issues} issues: {issue_key}"
                )

            # Xử lý thêm thông tin cho issue
            process_issue_details(jira_client, issue, sprint_info)

        # Lưu vào MongoDB
        if mongo_client.is_connected():
            if is_running_in_streamlit():
                st.toast("Đang xử lý và lưu dữ liệu vào MongoDB...", icon="ℹ️")
            # Truyền cả thông tin sprint để có thể xử lý worklogs một cách chính xác
            save_result = mongo_client.save_issues(
                issues, sprint_id, sprint_name, sprint_info
            )
            if save_result and is_running_in_streamlit():
                st.toast("Dữ liệu đã được xử lý và lưu vào MongoDB!", icon="✅")
        else:
            if is_running_in_streamlit():
                st.error("Không thể kết nối đến MongoDB. Dữ liệu không được lưu.")

        if with_progress and progress_bar is not None and is_running_in_streamlit():
            progress_bar.empty()

        if is_running_in_streamlit():
            st.toast(
                f"Đã đồng bộ {len(issues)} issues của sprint {sprint_name}", icon="✅"
            )

        return issues
    except Exception as e:
        if is_running_in_streamlit():
            st.error(f"Lỗi khi đồng bộ issues của sprint {sprint_id}: {str(e)}")
        return []


def get_last_status_in_sprint(changelog_data, sprint_start=None, sprint_end=None):
    """Lấy trạng thái cuối cùng của issue trong sprint dựa trên changelog

    Args:
        changelog_data (dict): Dữ liệu changelog của issue
        sprint_start (datetime, optional): Thời gian bắt đầu sprint
        sprint_end (datetime, optional): Thời gian kết thúc sprint

    Returns:
        tuple: (last_status, current_status) - Trạng thái cuối cùng trong sprint và trạng thái hiện tại
    """
    status_changes_in_sprint = []
    current_status = None

    if changelog_data and "histories" in changelog_data:
        # Duyệt qua tất cả lịch sử thay đổi
        for history in changelog_data.get("histories", []):
            history_created = history.get("created", "")
            if history_created:
                try:
                    history_date = datetime.fromisoformat(
                        history_created.replace("Z", "+00:00")
                    )

                    # Kiểm tra xem thời gian có nằm trong sprint không
                    if sprint_start and sprint_end:
                        if not (sprint_start <= history_date <= sprint_end):
                            continue

                    # Kiểm tra các thay đổi trạng thái
                    items = history.get("items", [])
                    status_changes = [
                        item for item in items if item.get("field") == "status"
                    ]

                    if status_changes:
                        for change in status_changes:
                            status_changes_in_sprint.append(
                                {
                                    "date": history_date,
                                    "status": change.get("toString", ""),
                                    "history": history,
                                }
                            )
                except Exception as e:
                    print(f"Lỗi khi xử lý thời gian changelog: {str(e)}")
                    continue

    # Sắp xếp các thay đổi trạng thái theo thời gian giảm dần (mới nhất lên đầu)
    if status_changes_in_sprint:
        status_changes_in_sprint.sort(key=lambda x: x["date"], reverse=True)
        # Lấy trạng thái mới nhất trong sprint
        last_status = status_changes_in_sprint[0]["status"]
        return last_status, last_status

    return None, None


def process_issue_details(jira_client, issue, sprint_info=None):
    """Xử lý chi tiết của issue

    Args:
        jira_client: Client kết nối đến Jira
        issue (dict): Dữ liệu issue
        sprint_info (dict, optional): Thông tin sprint

    Returns:
        dict: Issue đã được xử lý
    """
    try:
        issue_key = issue.get("key")

        # Lấy changelog từ API Jira với tham số expand=changelog
        response = jira_client.get(f"issue/{issue_key}?expand=changelog")
        changelog_data = response.json().get("changelog", {})

        # Xác định khoảng thời gian của sprint nếu có
        sprint_start = None
        sprint_end = None
        if sprint_info:
            if sprint_info.get("startDate"):
                sprint_start = datetime.fromisoformat(
                    sprint_info.get("startDate").replace("Z", "+00:00")
                )
            if sprint_info.get("endDate"):
                sprint_end = datetime.fromisoformat(
                    sprint_info.get("endDate").replace("Z", "+00:00")
                )

        # Lấy trạng thái cuối cùng trong sprint
        last_status_in_sprint, _ = get_last_status_in_sprint(
            changelog_data, sprint_start, sprint_end
        )

        # Nếu không có thay đổi trạng thái trong sprint, sử dụng trạng thái hiện tại
        if not last_status_in_sprint:
            current_status = (
                issue.get("fields", {}).get("status", {}).get("name", "N/A")
            )
            issue["sprint_status"] = current_status
        else:
            issue["sprint_status"] = last_status_in_sprint

        # Lưu trạng thái hiện tại vào issue để so sánh
        issue["current_status"] = (
            issue.get("fields", {}).get("status", {}).get("name", "N/A")
        )

        # Tìm thời gian gần nhất khi issue chuyển sang trạng thái Dev Done và Test Done trong sprint
        dev_done_date = None
        test_done_date = None

        if changelog_data and "histories" in changelog_data:
            for history in changelog_data.get("histories", []):
                created_date = history.get("created")

                # Kiểm tra xem thời gian chuyển trạng thái có nằm trong khoảng thời gian của sprint không
                history_in_sprint = True
                history_date = None

                if created_date and sprint_start and sprint_end:
                    try:
                        history_date = datetime.fromisoformat(
                            created_date.replace("Z", "+00:00")
                        )
                        if history_date < sprint_start or history_date > sprint_end:
                            history_in_sprint = False
                    except Exception as e:
                        print(f"Lỗi khi chuyển đổi thời gian: {str(e)}")

                # Nếu không có thông tin sprint hoặc thời gian nằm trong sprint
                if history_in_sprint:
                    items = history.get("items", [])
                    for item in items:
                        if item.get("field") == "status":
                            if item.get("toString") == "Dev Done":
                                # Cập nhật dev_done_date nếu gần đây hơn
                                if dev_done_date is None or (
                                    history_date
                                    and history_date
                                    > datetime.fromisoformat(
                                        dev_done_date.replace("Z", "+00:00")
                                    )
                                ):
                                    dev_done_date = created_date

                            if item.get("toString") == "Test Done":
                                # Cập nhật test_done_date nếu gần đây hơn
                                if test_done_date is None or (
                                    history_date
                                    and history_date
                                    > datetime.fromisoformat(
                                        test_done_date.replace("Z", "+00:00")
                                    )
                                ):
                                    test_done_date = created_date

        # Định dạng thời gian Dev Done nếu có
        formatted_dev_done_date = ""
        if dev_done_date:
            try:
                # Kiểm tra kiểu dữ liệu trước khi xử lý
                if not isinstance(dev_done_date, str):
                    dev_done_date = str(dev_done_date)
                date_obj = datetime.fromisoformat(dev_done_date.replace("Z", "+00:00"))
                formatted_dev_done_date = date_obj.strftime("%d/%m/%Y %H:%M")
            except Exception as e:
                print(f"Lỗi khi định dạng thời gian Dev Done: {str(e)}")
                formatted_dev_done_date = str(dev_done_date)

        # Định dạng thời gian Test Done nếu có
        formatted_test_done_date = ""
        if test_done_date:
            try:
                # Kiểm tra kiểu dữ liệu trước khi xử lý
                if not isinstance(test_done_date, str):
                    test_done_date = str(test_done_date)
                date_obj = datetime.fromisoformat(test_done_date.replace("Z", "+00:00"))
                formatted_test_done_date = date_obj.strftime("%d/%m/%Y %H:%M")
            except Exception as e:
                print(f"Lỗi khi định dạng thời gian Test Done: {str(e)}")
                formatted_test_done_date = str(test_done_date)

        # Thêm changelog và thời gian Test Done và Dev Done vào issue
        issue["changelog"] = changelog_data
        issue["test_done_date"] = formatted_test_done_date
        issue["dev_done_date"] = formatted_dev_done_date

        # Tìm và lấy danh sách commit từ các comment
        commits = []
        comments = issue.get("fields", {}).get("comment", {}).get("comments", [])
        for comment in comments:
            comment_text = comment.get("body", "")
            # Tìm các commit ID trong comment (giả định commit ID có định dạng mã hash git)
            commit_pattern = r"commit[:\s]+([a-fA-F0-9]{7,40})"
            found_commits = re.findall(commit_pattern, comment_text)
            if found_commits:
                commits.extend(found_commits)

        # Lấy commit từ trường Development (Jira Dev Tools)
        development_info = issue.get("fields", {}).get("development", {})
        if development_info:
            # Hỗ trợ cả cấu trúc development hiện tại và cấu trúc mới
            if isinstance(development_info, dict):
                # Cấu trúc phiên bản mới
                commits_data = development_info.get("commits", [])

                # Lấy id của các commit
                for commit in commits_data:
                    commit_id = commit.get("id", "")
                    if commit_id and commit_id not in commits:
                        commits.append(commit_id)

            # Kiểm tra trường statuses nếu có (dùng trong một số cài đặt Jira)
            elif isinstance(development_info, list):
                for status in development_info:
                    if isinstance(status, dict) and "commits" in status:
                        # Lấy commit từ mỗi status
                        for commit in status.get("commits", []):
                            commit_id = commit.get("id", "")
                            if commit_id and commit_id not in commits:
                                commits.append(commit_id)

        # Thêm danh sách commit vào issue
        issue["commits"] = commits
        issue["commit_count"] = len(commits)

        # Lấy thông tin Tester từ customfield_10031
        tester = "Không có"
        cf_tester = issue.get("fields", {}).get("customfield_10031")

        # Xử lý trường tester theo định dạng có thể có - chỉ lấy người dùng đầu tiên nếu là multi-user
        if cf_tester:
            if isinstance(cf_tester, dict) and "displayName" in cf_tester:
                # Trường hợp tester là một user Jira
                tester = cf_tester.get("displayName", "Không có")
            elif isinstance(cf_tester, dict) and "value" in cf_tester:
                # Trường hợp tester là một trường tùy chỉnh với giá trị
                tester = cf_tester.get("value", "Không có")
            elif isinstance(cf_tester, list) and len(cf_tester) > 0:
                # Trường hợp tester là một danh sách (User Picker multiple users)
                # Chỉ lấy người dùng đầu tiên trong danh sách
                first_tester = cf_tester[0]
                if isinstance(first_tester, dict) and "displayName" in first_tester:
                    tester = first_tester.get("displayName", "Không có")
                elif isinstance(first_tester, dict) and "value" in first_tester:
                    tester = first_tester.get("value", "Không có")
                else:
                    tester = str(first_tester)
            else:
                # Trường hợp khác
                tester = str(cf_tester)

        issue["tester"] = tester

        # Lấy parent key nếu issue là subtask
        if issue.get("fields", {}).get("parent"):
            parent_data = issue.get("fields", {}).get("parent", {})
            parent_key = parent_data.get("key")
            issue["parent_key"] = parent_key

        return issue
    except Exception as e:
        if is_running_in_streamlit():
            st.error(
                f"Lỗi khi xử lý thêm dữ liệu cho issue {issue.get('key')}: {str(e)}"
            )
        return issue


def get_sprint_info_from_mongo(mongo_client, sprint_id):
    """Lấy thông tin sprint từ MongoDB

    Args:
        mongo_client: Client kết nối đến MongoDB
        sprint_id (int): ID của sprint

    Returns:
        dict: Thông tin sprint
    """
    if mongo_client.is_connected():
        return mongo_client.get_sprint_info(sprint_id)
    return None


def get_issues_from_mongo(mongo_client, sprint_id):
    """Lấy danh sách issues từ MongoDB

    Args:
        mongo_client: Client kết nối đến MongoDB
        sprint_id (int): ID của sprint

    Returns:
        list: Danh sách issues
    """
    if mongo_client.is_connected():
        return mongo_client.get_issues(sprint_id)
    return []
