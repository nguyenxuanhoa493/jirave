import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import from src modules
from src.config.config import (
    APP_TITLE,
    APP_LAYOUT,
    SIDEBAR_STATE,
    DEFAULT_PROJECT,
)
from src.services.data_sync.sync_service import DataSyncService
from src.services.mongodb_client import is_running_in_streamlit
from src.services.utils.issue_utils import safe_get_status
from src.ui.components.sprint_selector import select_sprint
import json


def display_sync_tab(sync_service):
    """Hiển thị tab đồng bộ dữ liệu

    Args:
        sync_service (DataSyncService): Dịch vụ đồng bộ dữ liệu
    """
    st.subheader("Đồng bộ dữ liệu Sprint từ Jira")

    # Hiển thị dự án được sử dụng
    st.info(f"Đang sử dụng dự án: {DEFAULT_PROJECT}")

    # Kiểm tra nếu MongoDB có sẵn
    mongo_available = sync_service.mongo_client.is_connected()

    # Hiển thị trạng thái MongoDB
    if mongo_available:
        st.toast("Dữ liệu sẽ được lưu vào MongoDB", icon="✅")
    else:
        st.toast(
            "Dữ liệu sẽ được lưu vào local do không kết nối được MongoDB", icon="⚠️"
        )

    # Hiển thị thông báo về trạng thái trong Sprint và trạng thái hiện tại
    st.info(
        """
    **Lưu ý về trạng thái issue:**
    - **Trạng thái Sprint**: Trạng thái cuối cùng của issue trong khoảng thời gian của sprint (lấy từ changelog)
    - **Trạng thái hiện tại**: Trạng thái mới nhất của issue được lấy trực tiếp từ Jira API
    """
    )

    # Kiểm tra nếu có sprints
    local_sprints = sync_service.get_local_sprints(DEFAULT_PROJECT)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Đồng bộ tất cả Sprints của dự án", use_container_width=True):
            # Đồng bộ tất cả sprints
            sprints = sync_service.sync_all_sprints(DEFAULT_PROJECT)
            if sprints:
                st.success(
                    f"Đã đồng bộ {len(sprints)} sprints của dự án {DEFAULT_PROJECT}"
                )
                # Cập nhật local_sprints
                local_sprints = sprints

    with col2:
        if st.button("Cập nhật lại danh sách Sprints", use_container_width=True):
            # Đồng bộ lại danh sách sprints
            local_sprints = sync_service.get_local_sprints(DEFAULT_PROJECT)
            if not local_sprints:
                local_sprints = sync_service.sync_all_sprints(DEFAULT_PROJECT)

    # Hiển thị các sprints để lựa chọn
    if local_sprints:
        st.subheader("Chọn Sprint để đồng bộ Issues")

        # Hiển thị component chọn sprint
        selected_sprint = select_sprint(local_sprints)
        sprint_id = selected_sprint["id"]

        # Nút đồng bộ issues full width
        if st.button(
            f"Đồng bộ Issues của Sprint {selected_sprint.get('name', '')}",
            use_container_width=True,
        ):
            with st.status("Đang đồng bộ...", expanded=True) as status:
                # Đồng bộ issues của sprint
                issues = sync_service.sync_sprint_issues(sprint_id)
                if issues:
                    status.update(
                        label=f"Đã đồng bộ {len(issues)} issues",
                        state="complete",
                        expanded=False,
                    )
                    st.toast(
                        f"Đã đồng bộ {len(issues)} issues của sprint {selected_sprint.get('name', '')}",
                        icon="✅",
                    )
    else:
        st.warning("Chưa có dữ liệu sprints nào. Vui lòng đồng bộ sprints trước.")


def display_debug_tab(sync_service):
    """Hiển thị tab debug issue

    Args:
        sync_service (DataSyncService): Dịch vụ đồng bộ dữ liệu
    """
    st.subheader("Debug Issue từ Jira")

    # Hiển thị dự án được sử dụng
    st.info(f"Đang sử dụng dự án: {DEFAULT_PROJECT}")

    # Hiển thị chế độ DEBUG
    st.warning("⚠️ Công cụ debug issue")

    # Lấy danh sách sprint để người dùng có thể chọn
    local_sprints = sync_service.get_local_sprints(DEFAULT_PROJECT)

    if not local_sprints:
        st.warning("Chưa có dữ liệu sprints. Sẽ tiến hành đồng bộ sprints...")
        local_sprints = sync_service.sync_all_sprints(DEFAULT_PROJECT)

    if local_sprints:
        # Hiển thị danh sách sprints để chọn
        sprint_options = [
            {
                "label": f"{sprint.get('name', 'Sprint ' + str(sprint['id']))} (ID: {sprint['id']})",
                "value": sprint["id"],
            }
            for sprint in local_sprints
        ]

        # Khởi tạo session state nếu chưa có
        if "selected_sprint_id" not in st.session_state:
            st.session_state.selected_sprint_id = sprint_options[0]["value"]
        if "debug_issue_key" not in st.session_state:
            st.session_state.debug_issue_key = ""

        # Chọn sprint
        selected_sprint_id = st.selectbox(
            "Chọn Sprint để lấy thông tin thời gian:",
            options=[option["value"] for option in sprint_options],
            format_func=lambda x: next(
                (option["label"] for option in sprint_options if option["value"] == x),
                str(x),
            ),
            key="debug_sprint_selector_1",
            index=[
                i
                for i, opt in enumerate(sprint_options)
                if opt["value"] == st.session_state.selected_sprint_id
            ][0],
        )
        st.session_state.selected_sprint_id = selected_sprint_id

    # Form nhập issue key để debug
    with st.form("debug_single_issue"):
        issue_key = st.text_input(
            "Nhập ISSUE KEY để đồng bộ và debug chỉ 1 issue",
            value=st.session_state.debug_issue_key,
        )
        submitted = st.form_submit_button("Debug Issue")

    if submitted and issue_key:
        st.session_state.debug_issue_key = issue_key
        st.info(f"Đang debug issue: {issue_key}")

        # Khai báo biến để lưu dữ liệu trước
        raw_issue = None
        processed_issue = None
        processed_issues_mongo = None
        sprint_info = None

        # Lấy thông tin sprint được chọn từ lựa chọn ban đầu
        if selected_sprint_id:
            sprint_info_resp = sync_service.jira.sprint_client.get(
                f"sprint/{selected_sprint_id}", use_agile_api=True
            )
            if sprint_info_resp.status_code == 200:
                sprint_info = sprint_info_resp.json()

        with st.status("Đang lấy thông tin issue...", expanded=True) as status:
            # Lấy issue từ API
            try:
                # Lấy tất cả các trường cần thiết
                fields = "summary,status,assignee,issuetype,priority,created,updated,customfield_10160,customfield_10130,customfield_10159,subtasks,parent,duedate,resolutiondate,timeoriginalestimate,timeestimate,timespent,worklog,customfield_10092,customfield_10132,customfield_10031,comment,development,changelog"

                params = {"fields": fields}

                response = sync_service.jira.get(f"issue/{issue_key}", params=params)
                if not response or response.status_code != 200:
                    st.error(f"Không tìm thấy issue với key: {issue_key}")
                    return

                raw_issue = response.json()

                # Xử lý issue
                from src.services.data_sync.issue_sync import process_issue_details

                # Xử lý issue với thông tin sprint đã chọn
                processed_issue = process_issue_details(
                    sync_service.jira, raw_issue, sprint_info
                )

                # Cập nhật trạng thái sprint dựa trên changelog
                if raw_issue.get("changelog", {}).get("histories", []):
                    status_changes_in_sprint = []
                    for history in raw_issue["changelog"]["histories"]:
                        history_created = history.get("created", "")
                        if history_created:
                            history_date = datetime.fromisoformat(
                                history_created.replace("Z", "+00:00")
                            )
                            if sprint_info.get("startDate") and sprint_info.get(
                                "endDate"
                            ):
                                sprint_start_date = datetime.fromisoformat(
                                    sprint_info.get("startDate").replace("Z", "+00:00")
                                )
                                sprint_end_date = datetime.fromisoformat(
                                    sprint_info.get("endDate").replace("Z", "+00:00")
                                )
                                if sprint_start_date <= history_date <= sprint_end_date:
                                    items = history.get("items", [])
                                    status_changes = [
                                        item
                                        for item in items
                                        if item.get("field") == "status"
                                    ]
                                    if status_changes:
                                        for change in status_changes:
                                            status_changes_in_sprint.append(
                                                {
                                                    "date": history_date,
                                                    "status": change.get(
                                                        "toString", ""
                                                    ),
                                                    "history": history,
                                                }
                                            )

                    # Sắp xếp và hiển thị trạng thái cuối cùng trong sprint
                    if status_changes_in_sprint:
                        # Sắp xếp theo thời gian tăng dần
                        status_changes_in_sprint.sort(key=lambda x: x["date"])
                        # Lấy trạng thái cuối cùng
                        last_status = status_changes_in_sprint[-1]["status"]
                        st.success(f"Trạng thái cuối cùng trong sprint: {last_status}")

                        # Cập nhật trạng thái sprint trong processed_issue
                        processed_issue["sprint_status"] = last_status
                    else:
                        current_status = (
                            raw_issue.get("fields", {})
                            .get("status", {})
                            .get("name", "N/A")
                        )
                        st.success(
                            f"Trạng thái cuối cùng trong sprint: {current_status} (không có thay đổi trong sprint)"
                        )
                        processed_issue["sprint_status"] = current_status

                # Xử lý lần cuối qua MongoDB process
                processed_issues_mongo = sync_service.mongo_client.process_issues_data(
                    [processed_issue], sprint_info
                )

                # Tự động lưu lên MongoDB
                if (
                    processed_issue
                    and sprint_info
                    and sync_service.mongo_client.is_connected()
                ):
                    try:
                        # Lấy sprint ID và name
                        sprint_id = sprint_info.get("id")
                        sprint_name = sprint_info.get("name", f"Sprint {sprint_id}")

                        # Lưu issue lên MongoDB
                        save_result = sync_service.mongo_client.save_issues(
                            [processed_issue], sprint_id, sprint_name, sprint_info
                        )

                        if save_result:
                            st.toast(
                                f"Đã tự động đồng bộ issue {issue_key} lên MongoDB!",
                                icon="✅",
                            )
                        else:
                            st.toast("Không thể đồng bộ issue lên MongoDB.", icon="⚠️")
                    except Exception as e:
                        st.toast(f"Lỗi khi đồng bộ lên MongoDB: {str(e)}", icon="❌")

                status.update(
                    label=f"Đã xử lý issue {issue_key}",
                    state="complete",
                    expanded=False,
                )
            except Exception as e:
                st.error(f"Lỗi khi debug issue: {str(e)}")
                import traceback

                st.code(traceback.format_exc())
                return

        # Hiển thị thông tin sau khi status hoàn thành
        if raw_issue and processed_issue:
            # Lấy thông tin thời gian của sprint nếu có
            sprint_start_date = None
            sprint_end_date = None
            if sprint_info:
                if sprint_info.get("startDate"):
                    sprint_start_date = datetime.fromisoformat(
                        sprint_info.get("startDate").replace("Z", "+00:00")
                    )
                if sprint_info.get("endDate"):
                    sprint_end_date = datetime.fromisoformat(
                        sprint_info.get("endDate").replace("Z", "+00:00")
                    )

            # Hiển thị JSON
            st.subheader("1. Dữ liệu raw từ API")
            with st.expander("Xem JSON raw", expanded=True):
                st.json(raw_issue)

            # Hiển thị changelog trạng thái
            st.subheader("1.1. Chi tiết changelog trạng thái trong sprint")
            with st.expander("Xem changelog trạng thái", expanded=True):
                changelog_histories = raw_issue.get("changelog", {}).get(
                    "histories", []
                )
                if changelog_histories:
                    filtered_histories = []
                    status_changes_in_sprint = []
                    for history in changelog_histories:
                        history_created = history.get("created", "")
                        if history_created:
                            history_date = datetime.fromisoformat(
                                history_created.replace("Z", "+00:00")
                            )
                            if sprint_start_date and sprint_end_date:
                                if sprint_start_date <= history_date <= sprint_end_date:
                                    filtered_histories.append(history)
                                    # Kiểm tra nếu có thay đổi trạng thái
                                    items = history.get("items", [])
                                    status_changes = [
                                        item
                                        for item in items
                                        if item.get("field") == "status"
                                    ]
                                    if status_changes:
                                        for change in status_changes:
                                            status_changes_in_sprint.append(
                                                {
                                                    "date": history_date,
                                                    "status": change.get(
                                                        "toString", ""
                                                    ),
                                                    "history": history,
                                                }
                                            )

                    if filtered_histories:
                        st.info(
                            f"Số lượng thay đổi trạng thái trong sprint: {len(filtered_histories)}"
                        )
                        # Sắp xếp và hiển thị trạng thái cuối cùng trong sprint
                        if status_changes_in_sprint:
                            status_changes_in_sprint.sort(key=lambda x: x["date"])
                            last_status = status_changes_in_sprint[-1]["status"]
                            st.success(
                                f"Trạng thái cuối cùng trong sprint: {last_status}"
                            )
                        else:
                            current_status = (
                                raw_issue.get("fields", {})
                                .get("status", {})
                                .get("name", "N/A")
                            )
                            st.success(
                                f"Trạng thái cuối cùng trong sprint: {current_status} (không có thay đổi trong sprint)"
                            )
                            processed_issue["sprint_status"] = current_status

                        # Hiển thị lịch sử thay đổi theo thứ tự thời gian
                        for history in filtered_histories:
                            history_created = history.get("created", "")
                            history_author = history.get("author", {}).get(
                                "displayName", ""
                            )

                            items = history.get("items", [])
                            status_changes = [
                                item for item in items if item.get("field") == "status"
                            ]

                            if status_changes:
                                for change in status_changes:
                                    from_status = change.get("fromString", "")
                                    to_status = change.get("toString", "")

                                    st.markdown(f"**Thời gian**: {history_created}")
                                    st.markdown(f"**Người thay đổi**: {history_author}")
                                    st.markdown(f"**Trạng thái cũ**: {from_status}")
                                    st.markdown(f"**Trạng thái mới**: {to_status}")
                                    st.markdown("---")
                    else:
                        st.info(
                            "Không có thay đổi trạng thái nào trong thời gian của sprint"
                        )
                else:
                    st.info("Không có changelog nào")

            # Tính toán thời gian dev done và test done trong sprint
            st.subheader("1.2. Thời gian hoàn thành trong sprint")
            with st.expander("Xem thời gian hoàn thành", expanded=True):
                dev_done_time = None
                test_done_time = None

                if changelog_histories:
                    for history in changelog_histories:
                        history_created = history.get("created", "")
                        if history_created:
                            history_date = datetime.fromisoformat(
                                history_created.replace("Z", "+00:00")
                            )
                            if sprint_start_date and sprint_end_date:
                                if sprint_start_date <= history_date <= sprint_end_date:
                                    items = history.get("items", [])
                                    status_changes = [
                                        item
                                        for item in items
                                        if item.get("field") == "status"
                                    ]

                                    if status_changes:
                                        for change in status_changes:
                                            to_status = change.get("toString", "")
                                            if to_status.lower() in [
                                                "dev done",
                                                "resolved",
                                            ]:
                                                dev_done_time = history_date
                                            elif to_status.lower() in [
                                                "test done",
                                                "closed",
                                            ]:
                                                test_done_time = history_date

                if dev_done_time:
                    st.info(
                        f"**Dev Done Time**: {dev_done_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                else:
                    st.warning("Chưa hoàn thành Dev trong sprint này")

                if test_done_time:
                    st.info(
                        f"**Test Done Time**: {test_done_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                else:
                    st.warning("Chưa hoàn thành Test trong sprint này")

                if dev_done_time and test_done_time:
                    test_duration = test_done_time - dev_done_time
                    st.success(f"**Thời gian test**: {test_duration}")

            # Hiển thị worklog của issue
            st.subheader("1.3. Chi tiết worklog của issue")
            with st.expander("Xem chi tiết worklog", expanded=True):
                worklogs = (
                    raw_issue.get("fields", {}).get("worklog", {}).get("worklogs", [])
                )

                if worklogs:
                    # Tính tổng thời gian đã dành
                    total_time_spent_seconds = sum(
                        worklog.get("timeSpentSeconds", 0) for worklog in worklogs
                    )
                    total_hours = round(total_time_spent_seconds / 3600, 2)

                    # Hiển thị tổng thời gian
                    st.info(
                        f"**Tổng thời gian**: {total_hours} giờ ({total_time_spent_seconds} giây)"
                    )

                    # Nếu có thông tin về sprint, lọc và hiển thị các worklog trong khoảng thời gian của sprint
                    if sprint_info:
                        sprint_start_date = None
                        sprint_end_date = None

                        if sprint_info.get("startDate"):
                            sprint_start_date = datetime.fromisoformat(
                                sprint_info.get("startDate").replace("Z", "+00:00")
                            )
                        if sprint_info.get("endDate"):
                            sprint_end_date = datetime.fromisoformat(
                                sprint_info.get("endDate").replace("Z", "+00:00")
                            )

                        if sprint_start_date and sprint_end_date:
                            st.markdown("### Worklog trong khoảng thời gian sprint")
                            st.markdown(f"**Sprint**: {sprint_info.get('name', 'N/A')}")
                            st.markdown(
                                f"**Thời gian sprint**: {sprint_start_date.strftime('%d/%m/%Y')} → {sprint_end_date.strftime('%d/%m/%Y')}"
                            )

                            # Lọc worklog trong khoảng thời gian của sprint
                            sprint_worklogs = []
                            for worklog in worklogs:
                                worklog_date_str = worklog.get("started", "")
                                if worklog_date_str:
                                    try:
                                        worklog_date = datetime.fromisoformat(
                                            worklog_date_str.replace("Z", "+00:00")
                                        )
                                        if (
                                            sprint_start_date
                                            <= worklog_date
                                            <= sprint_end_date
                                        ):
                                            sprint_worklogs.append(worklog)
                                    except Exception as e:
                                        st.warning(
                                            f"Lỗi khi chuyển đổi thời gian worklog: {str(e)}"
                                        )

                            # Tính tổng thời gian trong sprint
                            sprint_time_spent_seconds = sum(
                                worklog.get("timeSpentSeconds", 0)
                                for worklog in sprint_worklogs
                            )
                            sprint_hours = round(sprint_time_spent_seconds / 3600, 2)

                            st.info(
                                f"**Tổng thời gian trong sprint**: {sprint_hours} giờ ({sprint_time_spent_seconds} giây)"
                            )

                            if sprint_worklogs:
                                # Hiển thị chi tiết worklog trong sprint
                                for i, worklog in enumerate(sprint_worklogs, 1):
                                    author = worklog.get("author", {}).get(
                                        "displayName", "Không có"
                                    )
                                    started = worklog.get("started", "")
                                    time_spent = worklog.get("timeSpent", "")
                                    time_spent_seconds = worklog.get(
                                        "timeSpentSeconds", 0
                                    )
                                    hours = round(time_spent_seconds / 3600, 2)

                                    comment = "Không có mô tả"
                                    if worklog.get("comment"):
                                        if isinstance(worklog["comment"], str):
                                            comment = worklog["comment"]
                                        elif isinstance(worklog["comment"], dict):
                                            comment_content = worklog["comment"].get(
                                                "content", []
                                            )
                                            if comment_content:
                                                for content in comment_content:
                                                    if content.get(
                                                        "type"
                                                    ) == "paragraph" and content.get(
                                                        "content"
                                                    ):
                                                        for text_content in content.get(
                                                            "content", []
                                                        ):
                                                            if (
                                                                text_content.get("type")
                                                                == "text"
                                                            ):
                                                                comment = (
                                                                    text_content.get(
                                                                        "text", ""
                                                                    )
                                                                )

                                    st.markdown(f"**#{i} - {author}** - {started}")
                                    st.markdown(
                                        f"**Thời gian**: {time_spent} ({hours} giờ)"
                                    )
                                    st.markdown(f"**Mô tả**: {comment}")
                                    st.markdown("---")

                                # Phân tích theo người dùng trong sprint
                                st.subheader("Phân tích theo người dùng trong sprint")
                                user_time_sprint = {}
                                for worklog in sprint_worklogs:
                                    author = worklog.get("author", {}).get(
                                        "displayName", "Không có"
                                    )
                                    time_spent_seconds = worklog.get(
                                        "timeSpentSeconds", 0
                                    )

                                    if author not in user_time_sprint:
                                        user_time_sprint[author] = 0
                                    user_time_sprint[author] += time_spent_seconds

                                for user, seconds in user_time_sprint.items():
                                    hours = round(seconds / 3600, 2)
                                    st.info(
                                        f"**{user}**: {hours} giờ ({round(hours/sprint_hours*100 if sprint_hours else 0, 1)}%)"
                                    )
                            else:
                                st.warning(
                                    "Không có worklog nào trong khoảng thời gian của sprint"
                                )

                    st.markdown("### Tất cả worklog")
                    # Tạo danh sách worklog với thông tin chi tiết
                    for i, worklog in enumerate(worklogs, 1):
                        author = worklog.get("author", {}).get(
                            "displayName", "Không có"
                        )
                        started = worklog.get("started", "")
                        time_spent = worklog.get("timeSpent", "")
                        time_spent_seconds = worklog.get("timeSpentSeconds", 0)
                        hours = round(time_spent_seconds / 3600, 2)

                        # Lấy comment nếu có
                        comment = "Không có mô tả"
                        if worklog.get("comment"):
                            if isinstance(worklog["comment"], str):
                                comment = worklog["comment"]
                            elif isinstance(worklog["comment"], dict):
                                comment_content = worklog["comment"].get("content", [])
                                if comment_content:
                                    for content in comment_content:
                                        if content.get(
                                            "type"
                                        ) == "paragraph" and content.get("content"):
                                            for text_content in content.get(
                                                "content", []
                                            ):
                                                if text_content.get("type") == "text":
                                                    comment = text_content.get(
                                                        "text", ""
                                                    )

                        st.markdown(f"**#{i} - {author}** - {started}")
                        st.markdown(f"**Thời gian**: {time_spent} ({hours} giờ)")
                        st.markdown(f"**Mô tả**: {comment}")
                        st.markdown("---")

                    # Hiển thị phân tích worklog theo người dùng
                    st.subheader("Phân tích theo người dùng (tất cả)")
                    user_time = {}
                    for worklog in worklogs:
                        author = worklog.get("author", {}).get(
                            "displayName", "Không có"
                        )
                        time_spent_seconds = worklog.get("timeSpentSeconds", 0)

                        if author not in user_time:
                            user_time[author] = 0
                        user_time[author] += time_spent_seconds

                    for user, seconds in user_time.items():
                        hours = round(seconds / 3600, 2)
                        st.info(
                            f"**{user}**: {hours} giờ ({round(hours/total_hours*100 if total_hours else 0, 1)}%)"
                        )
                else:
                    st.info("Không có worklog nào")

            st.subheader("2. Dữ liệu sau khi xử lý bởi issue_sync.py")
            with st.expander("Xem JSON sau xử lý cấp 1", expanded=True):
                st.json(processed_issue)

            st.subheader("3. Dữ liệu sau khi xử lý bởi MongoDB client")
            with st.expander("Xem JSON sau xử lý cấp 2", expanded=True):
                if processed_issues_mongo and len(processed_issues_mongo) > 0:
                    st.json(processed_issues_mongo[0])
                else:
                    st.error("Không có dữ liệu sau xử lý MongoDB")

            # So sánh các trường quan trọng
            st.subheader("4. So sánh các trường quan trọng")

            # Hiển thị thông tin về thời gian của sprint nếu có
            if sprint_info:
                sprint_start = sprint_info.get("startDate", "N/A")
                sprint_end = sprint_info.get("endDate", "N/A")
                sprint_name = sprint_info.get("name", "N/A")
                sprint_id = sprint_info.get("id", "N/A")

                st.info(f"Sprint: {sprint_name}")
                st.info(f"Sprint ID: {sprint_id}")
                st.info(f"Thời gian sprint: {sprint_start} → {sprint_end}")
            else:
                st.warning("Không có thông tin về sprint để kiểm tra thời gian")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**API raw**")
                current_status = (
                    raw_issue.get("fields", {}).get("status", {}).get("name", "N/A")
                )
                st.info(f"Current status: {current_status}")

                # Hiển thị thông tin về Sprint mà issue đang thuộc về
                st.markdown("**Sprints của issue:**")
                sprint_field = raw_issue.get("fields", {}).get("customfield_10020", [])

                # Xử lý và hiển thị danh sách sprint
                if sprint_field:
                    sprints_data = []

                    # Xử lý nhiều định dạng khác nhau của sprint field
                    if isinstance(sprint_field, list):
                        for sprint_item in sprint_field:
                            if isinstance(sprint_item, str):
                                # Trích xuất thông tin sprint từ chuỗi
                                import re

                                match = re.search(
                                    r"name=([^,]+),.*id=(\d+)", sprint_item
                                )
                                if match:
                                    sprint_name = match.group(1)
                                    sprint_id = match.group(2)
                                    sprints_data.append(
                                        {"name": sprint_name, "id": sprint_id}
                                    )
                            elif isinstance(sprint_item, dict):
                                # Trường hợp sprint là object
                                sprint_name = sprint_item.get("name", "Unknown")
                                sprint_id = sprint_item.get("id", "Unknown")
                                sprints_data.append(
                                    {"name": sprint_name, "id": sprint_id}
                                )

                    if sprints_data:
                        for i, sprint_data in enumerate(sprints_data, 1):
                            st.info(
                                f"{i}. {sprint_data['name']} (ID: {sprint_data['id']})"
                            )
                    else:
                        st.warning("Không thể phân tích dữ liệu sprint")
                else:
                    st.warning("Issue này không thuộc về sprint nào")

                tester_raw = raw_issue.get("fields", {}).get("customfield_10031")
                if isinstance(tester_raw, dict):
                    tester_display = tester_raw.get("displayName", str(tester_raw))
                elif isinstance(tester_raw, list) and len(tester_raw) > 0:
                    if isinstance(tester_raw[0], dict):
                        tester_display = tester_raw[0].get(
                            "displayName", str(tester_raw[0])
                        )
                    else:
                        tester_display = str(tester_raw[0])
                else:
                    tester_display = str(tester_raw)

                st.info(f"Tester raw: {tester_display}")

                # Hiển thị thông tin về commit từ dev field nếu có
                dev_info = raw_issue.get("fields", {}).get("development", {})
                if dev_info:
                    st.markdown("**Thông tin commit từ API:**")
                    st.json(dev_info)
                else:
                    st.info("Không có thông tin commit từ API")

            with col2:
                st.markdown("**issue_sync.py**")
                st.info(f"Sprint status: {processed_issue.get('sprint_status', 'N/A')}")
                st.info(f"Tester: {processed_issue.get('tester', 'N/A')}")

                # Hiển thị commit sau khi xử lý
                commits = processed_issue.get("commits", [])
                st.info(f"Số commit: {len(commits)}")
                if commits:
                    st.markdown("**Danh sách commit:**")
                    for i, commit in enumerate(commits, 1):
                        st.markdown(f"- **Commit {i}:** {commit}")

                # Hiển thị thông tin tổng hợp về worklog
                if processed_issue.get("sprint_time_spent"):
                    sprint_time_spent = processed_issue.get("sprint_time_spent", 0)
                    sprint_hours = round(sprint_time_spent / 3600, 2)
                    st.info(f"**Thời gian trong sprint**: {sprint_hours} giờ")
                elif raw_issue.get("fields", {}).get("worklog", {}).get("worklogs", []):
                    worklogs = (
                        raw_issue.get("fields", {})
                        .get("worklog", {})
                        .get("worklogs", [])
                    )
                    total_time_spent_seconds = sum(
                        worklog.get("timeSpentSeconds", 0) for worklog in worklogs
                    )
                    total_hours = round(total_time_spent_seconds / 3600, 2)
                    st.info(f"**Tổng thời gian worklog**: {total_hours} giờ")

            with col3:
                st.markdown("**MongoDB process**")
                if processed_issues_mongo and len(processed_issues_mongo) > 0:
                    st.info(f"Status: {processed_issues_mongo[0].get('status', 'N/A')}")
                    st.info(f"Tester: {processed_issues_mongo[0].get('tester', 'N/A')}")

                    # Hiển thị commit sau khi xử lý bởi MongoDB
                    mongo_commits = processed_issues_mongo[0].get("commits", [])
                    st.info(f"Số commit: {len(mongo_commits)}")
                    if mongo_commits:
                        st.markdown("**Danh sách commit:**")
                        for i, commit in enumerate(mongo_commits, 1):
                            st.markdown(f"- **Commit {i}:** {commit}")

                    # Hiển thị thông tin tổng hợp về worklog từ MongoDB
                    if processed_issues_mongo[0].get("sprint_time_spent"):
                        sprint_time_spent = processed_issues_mongo[0].get(
                            "sprint_time_spent", 0
                        )
                        sprint_hours = round(sprint_time_spent / 3600, 2)
                        st.info(
                            f"**Thời gian trong sprint (MongoDB)**: {sprint_hours} giờ"
                        )
                else:
                    st.error("Không có dữ liệu")

            # Thêm nút để lưu dữ liệu đã debug lên MongoDB
            st.subheader("5. Lưu dữ liệu lên MongoDB")

            if st.button("Lưu issue này lên MongoDB", use_container_width=True):
                if processed_issue and sprint_info:
                    try:
                        # Lấy sprint ID và name
                        sprint_id = sprint_info.get("id")
                        sprint_name = sprint_info.get("name", f"Sprint {sprint_id}")

                        # Lưu issue lên MongoDB
                        save_result = sync_service.mongo_client.save_issues(
                            [processed_issue], sprint_id, sprint_name, sprint_info
                        )

                        if save_result:
                            st.success(
                                f"Đã lưu issue {issue_key} lên MongoDB thành công!"
                            )
                        else:
                            st.error("Không thể lưu issue lên MongoDB.")
                    except Exception as e:
                        st.error(f"Lỗi khi lưu issue lên MongoDB: {str(e)}")
                        import traceback

                        st.code(traceback.format_exc())
                else:
                    st.error(
                        "Không có dữ liệu issue đã xử lý hoặc thông tin sprint để lưu lên MongoDB."
                    )
    else:
        st.warning("Vui lòng nhập mã issue và nhấn nút 'Debug Issue'")


def display_view_tab(sync_service):
    """Hiển thị tab xem dữ liệu

    Args:
        sync_service (DataSyncService): Dịch vụ đồng bộ dữ liệu
    """
    st.subheader("Xem dữ liệu đã đồng bộ")

    # Kiểm tra nếu có sprints
    local_sprints = sync_service.get_local_sprints(DEFAULT_PROJECT)

    if not local_sprints:
        st.warning("Chưa có dữ liệu sprints nào. Vui lòng đồng bộ sprints trước.")
        return

    # Hiển thị component chọn sprint
    selected_sprint = select_sprint(local_sprints, key="view_sprint_selector")

    if selected_sprint is None:
        return

    sprint_id = selected_sprint["id"]

    # Lấy issues của sprint từ MongoDB
    issues = sync_service.get_local_sprint_issues(sprint_id)

    if not issues:
        st.warning(
            f"Sprint {selected_sprint['data'].get('name', '')} chưa có dữ liệu issues."
        )
        return

    df = pd.DataFrame(issues)
    st.dataframe(df, use_container_width=True)


def display_data_sync():
    """Hiển thị giao diện đồng bộ dữ liệu"""
    st.title("Đồng bộ dữ liệu từ Jira")

    # Khởi tạo dịch vụ đồng bộ
    sync_service = DataSyncService()

    # Thêm tab cho các chức năng đồng bộ khác nhau
    tab1, tab2, tab3 = st.tabs(
        ["Đồng bộ Sprint", "Xem dữ liệu đã đồng bộ", "Debug Issue"]
    )

    with tab1:
        display_sync_tab(sync_service)

    with tab2:
        display_view_tab(sync_service)

    with tab3:
        display_debug_tab(sync_service)


def setup_page():
    """Thiết lập trang khi chạy trực tiếp"""
    # Set page configuration
    st.set_page_config(
        page_title="Đồng bộ dữ liệu",
        layout=APP_LAYOUT,
        initial_sidebar_state=SIDEBAR_STATE,
    )


def main():
    """Hàm chính để chạy ứng dụng"""
    # Thiết lập trang
    setup_page()

    # Hiển thị giao diện đồng bộ dữ liệu
    display_data_sync()


if __name__ == "__main__":
    main()
