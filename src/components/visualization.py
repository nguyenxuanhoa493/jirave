import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
from src.config.config import HEATMAP_COLORSCALE, TAILWIND_TABLE_CSS

# Thêm CSS cho group table với các nhóm hiển thị mặc định
GROUP_TABLE_CSS = """
<style>
.tailwind-table {
    margin-top: 10px;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    overflow: hidden;
}

.tailwind-table th {
    background-color: #f3f4f6;
    font-weight: 600;
    text-align: center;
    padding: 12px 16px;
    border-bottom: 2px solid #e5e7eb;
    color: #374151;
    text-transform: uppercase;
    font-size: 14px;
    letter-spacing: 0.05em;
}

.tailwind-table td {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e7eb;
    color: #1f2937;
    vertical-align: middle;
}

.group-header {
    background-color: #e5e7eb;
    font-weight: bold;
}

.group-header td {
    padding: 12px 16px !important; 
}

.group-header:hover {
    background-color: #d1d5db;
}

.group-row {
    background-color: #f9fafb;
}

.group-row:hover {
    background-color: #f3f4f6;
}

.inner-table {
    width: 100%;
    border-collapse: collapse;
}

.inner-table td {
    padding: 10px 16px;
    border-bottom: 1px solid #e5e7eb;
}

.tailwind-table a {
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
}

.tailwind-table a:hover {
    text-decoration: underline;
    color: #1d4ed8;
}
</style>
"""


class DataVisualizer:
    """Class chịu trách nhiệm tạo và hiển thị các biểu đồ"""

    @staticmethod
    def create_heatmap(dates, users, daily_summary):
        """Tạo biểu đồ heatmap hiển thị giờ làm việc theo ngày và người dùng

        Args:
            dates (list): Danh sách các ngày
            users (list): Danh sách người dùng
            daily_summary (dict): Dữ liệu tổng hợp theo ngày

        Returns:
            plotly.graph_objs.Figure: Đối tượng biểu đồ
        """
        # Chuẩn bị dữ liệu cho heatmap
        heatmap_data = []
        text_data = []
        for date in dates:
            hours_row = []
            text_row = []
            for user in users:
                hours = daily_summary[date].get(user, 0)
                hours_row.append(hours)
                text_row.append(f"{hours:.2f}")
            heatmap_data.append(hours_row)
            text_data.append(text_row)

        # Tạo biểu đồ heatmap
        fig_heatmap = go.Figure(
            data=go.Heatmap(
                z=heatmap_data,
                x=users,
                y=dates,
                text=text_data,
                texttemplate="%{text}",
                textfont={"size": 14, "color": "black"},
                showscale=True,
                colorscale=HEATMAP_COLORSCALE,
                hoverongaps=False,
            )
        )

        fig_heatmap.update_layout(
            title="Daily Hours by Team Member",
            xaxis_title="Team Member",
            yaxis_title="Date",
            height=max(300, len(dates) * 30),
            font=dict(size=14),
            title_font_size=16,
        )

        return fig_heatmap

    @staticmethod
    def create_pie_chart(user_summary):
        """Tạo biểu đồ tròn hiển thị phân bố giờ làm việc theo người dùng

        Args:
            user_summary (dict): Dữ liệu tổng số giờ làm việc theo người dùng

        Returns:
            plotly.graph_objs.Figure: Đối tượng biểu đồ
        """
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=list(user_summary.keys()),
                    values=list(user_summary.values()),
                    textinfo="label+percent",
                    insidetextorientation="radial",
                )
            ]
        )

        fig_pie.update_layout(
            title="Distribution of Hours by Team Member",
            height=500,
        )

        return fig_pie

    @staticmethod
    def create_task_chart(issue_summary):
        """Tạo biểu đồ cột hiển thị top 5 issue theo giờ làm việc

        Args:
            issue_summary (dict): Dữ liệu tổng số giờ làm việc theo issue

        Returns:
            plotly.graph_objs.Figure: Đối tượng biểu đồ
        """
        # Lấy top 5 issues
        sorted_issues = sorted(issue_summary.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        task_data = []
        for key, hours in sorted_issues:
            task_data.append({"Task": key, "Hours": hours})

        df_tasks = pd.DataFrame(task_data)

        fig_tasks = px.bar(
            df_tasks, x="Hours", y="Task", orientation="h", title="Top 5 Tasks by Hours"
        )

        fig_tasks.update_layout(height=300)
        return fig_tasks

    @staticmethod
    def display_visualizations(report_data):
        """Hiển thị tất cả các biểu đồ và bảng

        Args:
            report_data (dict): Dữ liệu báo cáo từ WorklogReport
        """
        # Kiểm tra dữ liệu có tồn tại không
        if not report_data or report_data["total_hours"] == 0:
            st.warning("No data available for the selected period.")
            return

        # Hiển thị metrics
        st.header("Team Summary")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Hours", f"{report_data['total_hours']:.2f}")
        with col2:
            avg_daily_hours = 0
            if len(report_data["daily_summary"]) > 0:
                avg_daily_hours = report_data["total_hours"] / len(
                    report_data["daily_summary"]
                )
            st.metric("Average Daily Hours", f"{avg_daily_hours:.2f}")
        with col3:
            total_tasks = len(report_data.get("by_issue", {}))
            st.metric("Total Tasks", total_tasks)
        with col4:
            total_users = len(report_data.get("by_user", {}))
            st.metric("Team Members", total_users)

        # Lấy danh sách ngày và user
        dates = sorted(report_data["daily_summary"].keys())
        users = sorted(report_data.get("by_user", {}).keys())

        if not dates or not users:
            st.warning("No data available for the selected period.")
            return

        # Hiển thị heatmap
        fig_heatmap = DataVisualizer.create_heatmap(
            dates, users, report_data["daily_summary"]
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Tạo dữ liệu cho bảng hàng ngày
        daily_data = DataVisualizer._prepare_daily_table(dates, users, report_data)

        # Hiển thị biểu đồ cột cho task
        if "by_issue" in report_data and report_data["by_issue"]:
            issue_summary = {}
            for key, issue_info in report_data["by_issue"].items():
                total_hours = sum(w["hours"] for w in issue_info["worklogs"])
                issue_summary[f"{key}: {issue_info['summary'][:30]}..."] = total_hours

            fig_tasks = DataVisualizer.create_task_chart(issue_summary)
            st.plotly_chart(fig_tasks, use_container_width=True)

        # Hiển thị bảng chi tiết log theo bộ lọc users
        st.header("Detailed Log Table")

        # Chuẩn bị tất cả dữ liệu log (không lọc)
        all_log_data = DataVisualizer._prepare_detailed_log_table(
            report_data, "All Users"
        )

        # Khởi tạo session_state cho user_filter nếu chưa có
        if "user_filter" not in st.session_state:
            st.session_state.user_filter = "All Users"

        # Hàm callback khi thay đổi bộ lọc user
        def on_user_filter_change():
            st.session_state.user_filter = st.session_state.user_filter_widget

        col1, col2 = st.columns(2, gap="large")
        with col1:
            # Sử dụng session_state để lưu giá trị selectbox
            st.selectbox(
                "Select User",
                users + ["All Users"],
                index=(
                    len(users)
                    if st.session_state.user_filter == "All Users"
                    else (
                        users.index(st.session_state.user_filter)
                        if st.session_state.user_filter in users
                        else len(users)
                    )
                ),
                key="user_filter_widget",
                on_change=on_user_filter_change,
            )

        # Lấy giá trị user_filter từ session_state
        user_filter = st.session_state.user_filter

        # Tính tổng số giờ hiển thị
        total_filtered_hours = sum(
            float(entry["Hours"])
            for entry in all_log_data
            if user_filter == "All Users" or entry["Author"] == user_filter
        )
        with col2:
            # Hiển thị tổng số giờ đã lọc
            st.metric("Total Hours in Table", f"{total_filtered_hours:.2f}")

        # Lọc dữ liệu theo user đã chọn (không cần call API lại)
        if user_filter != "All Users":
            filtered_log_data = [
                entry for entry in all_log_data if entry["Author"] == user_filter
            ]
        else:
            filtered_log_data = all_log_data

        # Chuyển đổi thành pandas DataFrame
        df = pd.DataFrame(filtered_log_data)

        # Tạo cột Issue_Link với HTML cho liên kết
        if not df.empty and "Issue" in df.columns and "URL" in df.columns:
            # Tạo cột liên kết Issue
            df["Issue_HTML"] = df.apply(
                lambda row: f'<a href="{row["URL"]}" target="_blank">{row["Issue"]}</a>',
                axis=1,
            )

            # Tạo cột Author_Display với HTML để hiển thị avatar và tên tác giả
            df["Author_HTML"] = df.apply(
                lambda row: f'<div style="display: flex; align-items: center; gap: 8px;"><img src="{row["Avatar"]}" style="width: 24px; height: 24px; border-radius: 50%;" onerror="this.onerror=null; this.src=\'https://upload.wikimedia.org/wikipedia/commons/8/89/Portrait_Placeholder.png\';"><span>{row["Author"]}</span></div>',
                axis=1,
            )

            # Chỉ giữ các cột cần thiết
            display_cols = [
                "Issue_HTML",
                "Summary",
                "Author_HTML",
                "Author",  # Giữ lại để nhóm
                "Date",
                "Hours",
                "Comment",
            ]

            df = df[display_cols]

            # Sắp xếp theo Author để nhóm
            df = df.sort_values(by=["Author"])

            # Tạo bảng HTML trực tiếp
            st.write("### Detailed Log Table (Grouped by User)")

            # Hiển thị CSS
            st.markdown(GROUP_TABLE_CSS, unsafe_allow_html=True)

            # Hiển thị dữ liệu tổng hợp theo user
            for user_name, user_group in df.groupby("Author"):
                # Tính tổng số giờ
                total_hours = sum(float(h) for h in user_group["Hours"])

                # Lấy HTML avatar + tên từ dòng đầu tiên
                author_html = user_group.iloc[0]["Author_HTML"]

                # Hiển thị header nhóm
                st.markdown(
                    f"""
                <div class="group-header" style="display: flex; justify-content: space-between; padding: 10px; background-color: #e5e7eb; margin-top: 20px; border-radius: 4px;">
                    <div>{author_html}</div>
                    <div>Total Hours: <b>{total_hours:.2f}</b> | {len(user_group)} entries</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Chuẩn bị dữ liệu cho bảng
                display_df = user_group[
                    ["Issue_HTML", "Summary", "Date", "Hours", "Comment"]
                ].copy()

                # Format lại cột Date thành DD/MM/YY
                display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime(
                    "%d/%m/%y"
                )

                display_df.columns = ["Issue", "Summary", "Date", "Hours", "Comment"]

                # Hiển thị bảng worklog của user
                st.markdown(
                    display_df.to_html(
                        escape=False, index=False, classes="tailwind-table"
                    ),
                    unsafe_allow_html=True,
                )
        else:
            # Hiển thị bình thường nếu không có dữ liệu hoặc cột

            # Chuyển đổi định dạng Date nếu cột tồn tại
            if not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d/%m/%y")

            st.dataframe(
                filtered_log_data if df.empty else df,
                use_container_width=True,
                column_config={
                    "Issue": st.column_config.TextColumn("Issue", width="small"),
                    "Summary": st.column_config.TextColumn("Summary", width="medium"),
                    "Author": st.column_config.TextColumn("Author", width="small"),
                    "Date": st.column_config.TextColumn("Date", width="small"),
                    "Hours": st.column_config.NumberColumn(
                        "Hours", width="small", format="%.2f"
                    ),
                    "Comment": st.column_config.TextColumn(
                        "Comment", width="large", help="Nội dung bình luận của worklog"
                    ),
                },
                hide_index=True,
            )

    @staticmethod
    def _prepare_daily_table(dates, users, data):
        """Chuẩn bị dữ liệu cho bảng hàng ngày

        Args:
            dates (list): Danh sách các ngày
            users (list): Danh sách người dùng
            data (dict): Dữ liệu báo cáo

        Returns:
            list: Danh sách các dòng dữ liệu cho bảng
        """
        daily_data = []

        # Đảm bảo daily_summary tồn tại trong data
        daily_summary = data.get("daily_summary", {})

        # Thêm dữ liệu cho từng ngày
        for date in dates:
            row = {"Date": date}
            daily_total = 0

            # Đảm bảo date tồn tại trong daily_summary
            date_data = daily_summary.get(date, {})

            for user in users:
                # Lấy số giờ cho user, mặc định là 0 nếu không tồn tại
                hours = date_data.get(user, 0)
                row[user] = f"{hours:.2f}"
                daily_total += hours

            row["Total"] = f"{daily_total:.2f}"
            daily_data.append(row)

        # Thêm dòng tổng nếu có nhiều hơn một ngày
        if len(dates) > 1:
            total_row = {"Date": "Total"}
            for user in users:
                # Cộng tổng số giờ cho mỗi user qua tất cả các ngày
                try:
                    user_total = sum(float(day.get(user, "0.00")) for day in daily_data)
                    total_row[user] = f"{user_total:.2f}"
                except (ValueError, TypeError):
                    # Xử lý trường hợp không thể chuyển đổi thành float
                    total_row[user] = "0.00"

            # Sử dụng tổng số giờ từ dữ liệu báo cáo nếu có
            total_row["Total"] = f"{data.get('total_hours', 0):.2f}"
            daily_data.append(total_row)

        return daily_data

    @staticmethod
    def _prepare_detailed_log_table(report_data, user_filter):
        """Chuẩn bị dữ liệu cho bảng log chi tiết

        Args:
            report_data (dict): Dữ liệu báo cáo
            user_filter (str): Người dùng được chọn để lọc, hoặc 'All Users'

        Returns:
            list: Danh sách các dòng dữ liệu cho bảng log chi tiết
        """
        log_data = []

        # Kiểm tra xem by_issue có tồn tại trong report_data không
        if "by_issue" not in report_data:
            return log_data

        # Duyệt qua tất cả các issue và worklogs của chúng
        for issue_key, issue_info in report_data["by_issue"].items():
            issue_summary = issue_info.get("summary", "No summary")

            # Kiểm tra xem worklogs có tồn tại trong issue_info không
            if "worklogs" not in issue_info:
                continue

            for worklog in issue_info["worklogs"]:
                author = worklog.get("author", "Unknown")
                hours = worklog.get("hours", 0)

                # Xử lý trường Comment để đảm bảo luôn là chuỗi string
                comment = worklog.get("comment", "")
                if comment is None:
                    comment = ""
                elif isinstance(comment, dict):
                    # Xử lý chi tiết nếu comment là dict
                    try:
                        # Trích xuất nội dung từ các trường phổ biến trong Jira comment
                        if "content" in comment:
                            # Xử lý cấu trúc Jira Atlassian Document Format
                            content_arr = []
                            for content_item in comment.get("content", []):
                                if (
                                    isinstance(content_item, dict)
                                    and "content" in content_item
                                ):
                                    for text_item in content_item.get("content", []):
                                        if (
                                            isinstance(text_item, dict)
                                            and "text" in text_item
                                        ):
                                            content_arr.append(
                                                text_item.get("text", "")
                                            )
                            comment = " ".join(content_arr)
                        elif "body" in comment:
                            # Một số comment có thể được định dạng với trường body
                            comment = comment.get("body", "")
                        elif "value" in comment:
                            # Một số comment có thể được định dạng với trường value
                            comment = comment.get("value", "")
                        else:
                            # Nếu không tìm thấy trường nào quen thuộc, chuyển đổi toàn bộ dict
                            comment = str(comment)
                    except:
                        comment = "Structured comment data"
                elif isinstance(comment, list):
                    # Xử lý nếu comment là danh sách
                    try:
                        comment_parts = []
                        for item in comment:
                            if isinstance(item, dict):
                                # Trích xuất text từ dict trong list
                                if "text" in item:
                                    comment_parts.append(str(item["text"]))
                                else:
                                    comment_parts.append(str(item))
                            else:
                                comment_parts.append(str(item))
                        comment = " ".join(comment_parts)
                    except:
                        comment = "List of comment items"
                else:
                    # Đảm bảo comment là string cho tất cả các trường hợp khác
                    try:
                        comment = str(comment)
                    except:
                        comment = "Unreadable comment"

                # Tạo URL trực tiếp đến Jira issue
                issue_url = f"https://vieted.atlassian.net/browse/{issue_key}"

                # Thu thập thông tin cho bản ghi log
                log_entry = {
                    "Issue": issue_key,  # Mã issue (ví dụ: CLD-123)
                    "URL": issue_url,  # URL đầy đủ để link sang Jira
                    "Summary": issue_summary,
                    "Author": author,
                    "Avatar": worklog.get("avatar_url", ""),  # URL avatar của tác giả
                    "Date": worklog.get("date", ""),
                    "Hours": f"{hours:.2f}",
                    "Comment": comment,
                }

                log_data.append(log_entry)

        # Sắp xếp theo ngày giảm dần (mới nhất lên đầu)
        log_data.sort(key=lambda x: x["Date"], reverse=True)

        return log_data
