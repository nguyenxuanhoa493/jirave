import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
import plotly.graph_objects as go
import numpy as np

# Set page configuration first
st.set_page_config(
    page_title="Steve Estimate | Jira Analytics",
    page_icon="⏱️",
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


class SteveEstimateService:
    """Service cho phân tích Steve Estimate"""

    def __init__(self):
        """Khởi tạo service"""
        self.jira = JiraClient()

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

    def search_issues_with_steve_estimate(self, sprint_id=None):
        """Tìm kiếm issues với Steve Estimate và có thể lọc theo sprint_id

        Args:
            sprint_id (int, optional): ID của sprint cần lọc. Defaults to None.

        Returns:
            list: Danh sách issues thỏa mãn điều kiện
        """
        # Xây dựng JQL query
        jql = 'project = "CLD" AND "steve estimate[number]" IS NOT EMPTY'

        # Thêm điều kiện sprint nếu có
        if sprint_id:
            jql += f" AND sprint = {sprint_id}"

        # Các fields cần lấy, bao gồm customfield_10159 (steve estimate)
        fields = [
            "key",
            "summary",
            "issuetype",
            "timeoriginalestimate",
            "timeestimate",
            "timespent",
            "customfield_10159",
            "subtasks",
            "status",
            "assignee",
        ]

        # Tìm kiếm issues
        try:
            issues = self.jira.search_issues(jql, fields)
            if issues:
                st.toast(
                    f"Đã tìm thấy {len(issues)} issues có Steve Estimate!", icon="✅"
                )
                return issues
            else:
                st.info("Không tìm thấy issue nào thỏa mãn điều kiện.")
                return []
        except Exception as e:
            st.error(f"Lỗi khi tìm kiếm issues: {str(e)}")
            return []

    def get_issue_details(self, issue_key):
        """Lấy chi tiết issue bao gồm thông tin subtasks

        Args:
            issue_key (str): Key của issue

        Returns:
            dict: Thông tin chi tiết của issue
        """
        try:
            # Lấy thông tin issue
            issue = self.jira.get_issue(issue_key, ["customfield_10159"])
            if issue is None:
                st.warning(f"Không thể tìm thấy thông tin cho issue {issue_key}")
                return None
            return issue
        except Exception as e:
            st.error(f"Lỗi khi lấy chi tiết issue {issue_key}: {str(e)}")
            return None

    def get_subtasks_estimate(self, subtask_keys):
        """Lấy tổng thời gian dự kiến của các subtask

        Args:
            subtask_keys (list): Danh sách keys của các subtask

        Returns:
            int: Tổng thời gian dự kiến (seconds)
        """
        total_estimate = 0
        if not subtask_keys:
            return total_estimate

        for key in subtask_keys:
            if not key:  # Kiểm tra key rỗng
                continue

            try:
                subtask = self.jira.get_issue(key)
                if subtask and "fields" in subtask:
                    # Lấy thời gian dự kiến (timeoriginalestimate hoặc timeestimate)
                    estimate = (
                        subtask["fields"].get("timeoriginalestimate")
                        or subtask["fields"].get("timeestimate")
                        or 0
                    )
                    total_estimate += estimate
            except Exception as e:
                st.warning(f"Không thể lấy thông tin của subtask {key}: {str(e)}")

        return total_estimate


def format_time_seconds(seconds):
    """Chuyển đổi thời gian từ giây sang định dạng giờ

    Args:
        seconds (int): Thời gian tính bằng giây

    Returns:
        str: Thời gian định dạng giờ (Xh)
    """
    if not seconds:
        return "0h"
    hours = seconds / 3600
    return f"{hours:.1f}h"


def process_issues_data(issues_data, steve_est_service, status_filter="dev_done"):
    """Xử lý dữ liệu issues để hiển thị

    Args:
        issues_data (list): Danh sách issues
        steve_est_service (SteveEstimateService): Service để lấy thông tin bổ sung
        status_filter (str): Lọc theo trạng thái ("all" hoặc "dev_done")

    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu đã xử lý
    """
    results = []

    # Danh sách các trạng thái Dev Done
    dev_done_statuses = ["Dev Done", "Test Done", "Deployed", "Done"]

    for issue in issues_data:
        try:
            # Xử lý đặc biệt cho issue CLD-501 (thêm thông tin debug)
            is_special_issue = issue.get("key") == "CLD-501"
            if is_special_issue:
                pass
                if issue.get("fields") is None:
                    st.warning("Issue CLD-501 có trường fields là None")
                    continue

            fields = issue.get("fields", {})

            # Lọc theo trạng thái nếu cần
            if status_filter == "dev_done":
                status_name = (
                    fields.get("status", {}).get("name", "")
                    if fields.get("status") is not None
                    else ""
                )
                if status_name not in dev_done_statuses:
                    continue

            # Lấy thông tin cơ bản
            key = issue.get("key", "N/A")
            summary = fields.get("summary", "N/A")

            # Lấy Steve Estimate
            steve_estimate = fields.get("customfield_10159")
            if steve_estimate is None:
                steve_estimate = 0
            elif isinstance(steve_estimate, dict):
                steve_estimate = float(steve_estimate.get("value", 0))
            else:
                try:
                    steve_estimate = float(steve_estimate)
                except (ValueError, TypeError):
                    steve_estimate = 0

            # Lấy thời gian dự kiến và đã log
            original_estimate = fields.get("timeoriginalestimate", 0) or 0
            time_spent = fields.get("timespent", 0) or 0

            # Kiểm tra xem issue có subtasks không
            subtasks = fields.get("subtasks", [])
            subtask_estimate = 0
            subtask_spent = 0

            if subtasks:
                # Lấy danh sách key của các subtask
                subtask_keys = [
                    subtask.get("key")
                    for subtask in subtasks
                    if subtask.get("key") is not None
                ]

                # Lấy tổng thời gian dự kiến của các subtask
                if subtask_keys:
                    subtask_estimate = steve_est_service.get_subtasks_estimate(
                        subtask_keys
                    )

                    # Lấy thêm thời gian đã log của subtasks
                    for key in subtask_keys:
                        try:
                            subtask = steve_est_service.jira.get_issue(key)
                            if subtask and "fields" in subtask:
                                spent = subtask["fields"].get("timespent", 0) or 0
                                subtask_spent += spent
                        except Exception:
                            pass

            # Sử dụng thời gian của subtasks nếu có, nếu không thì dùng thời gian của issue gốc
            total_estimate = (
                subtask_estimate if subtask_estimate > 0 else original_estimate
            )
            total_spent = subtask_spent if subtask_spent > 0 else time_spent

            # Tính chênh lệch (giờ)
            steve_estimate_seconds = steve_estimate * 3600  # Chuyển giờ sang giây
            diff_seconds = steve_estimate_seconds - total_estimate

            # Tính % hoàn thành theo thời gian
            completion_rate_original = 0
            if total_estimate > 0:
                completion_rate_original = min(
                    100, (total_spent / total_estimate) * 100
                )

            completion_rate_steve = 0
            if steve_estimate_seconds > 0:
                completion_rate_steve = min(
                    100, (total_spent / steve_estimate_seconds) * 100
                )

            # Thêm vào kết quả
            results.append(
                {
                    "Key": key,
                    "Summary": summary,
                    "Steve Estimate (h)": steve_estimate,
                    "Thời gian dự kiến (h)": format_time_seconds(total_estimate),
                    "Thời gian dự kiến (s)": total_estimate,
                    "Thời gian đã log (h)": format_time_seconds(total_spent),
                    "Thời gian đã log (s)": total_spent,
                    "Chênh lệch (h)": format_time_seconds(diff_seconds),
                    "Chênh lệch (s)": diff_seconds,
                    "Chênh lệch (%)": (
                        0
                        if total_estimate == 0
                        else diff_seconds / total_estimate * 100
                    ),
                    "% hoàn thành (theo dự kiến)": round(completion_rate_original, 2),
                    "% hoàn thành (theo Steve)": round(completion_rate_steve, 2),
                    "Loại Issue": (
                        fields.get("issuetype", {}).get("name", "N/A")
                        if fields.get("issuetype") is not None
                        else "N/A"
                    ),
                    "Trạng thái": (
                        fields.get("status", {}).get("name", "N/A")
                        if fields.get("status") is not None
                        else "N/A"
                    ),
                    "Assignee": (
                        fields.get("assignee", {}).get("displayName", "Không có")
                        if fields.get("assignee") is not None
                        else "Không có"
                    ),
                }
            )

        except Exception as e:
            st.error(f"Lỗi khi xử lý issue {issue.get('key', 'unknown')}: {str(e)}")

    # Tạo DataFrame
    if results:
        df = pd.DataFrame(results)
        return df
    else:
        return pd.DataFrame()


def display_summary_metrics(df):
    """Hiển thị các số liệu tổng hợp

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu issues
    """
    # Tạo layout 4 cột cho dòng đầu - Cặp chỉ số thời gian
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_issues = len(df)
        st.metric("Tổng số Issues", total_issues)

    with col2:
        total_steve_estimate = df["Steve Estimate (h)"].sum()
        st.metric("Tổng Steve Estimate", f"{total_steve_estimate:.1f}h")

    with col3:
        total_estimate_seconds = df["Thời gian dự kiến (s)"].sum()
        total_estimate_hours = total_estimate_seconds / 3600
        st.metric("Tổng thời gian dự kiến", f"{total_estimate_hours:.1f}h")

    with col4:
        total_spent_seconds = df["Thời gian đã log (s)"].sum()
        total_spent_hours = total_spent_seconds / 3600
        st.metric("Tổng thời gian đã log", f"{total_spent_hours:.1f}h")

    # Dòng thứ hai - Cặp chỉ số chênh lệch thời gian
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_diff_seconds = df["Chênh lệch (s)"].sum()
        total_diff_hours = total_diff_seconds / 3600
        diff_color = "normal"
        if total_diff_hours > 0:
            diff_color = "inverse"  # Steve ước tính cao hơn
        elif total_diff_hours < 0:
            diff_color = "off"  # Steve ước tính thấp hơn
        # Tỉ lệ chênh lệch tổng thể
        total_diff_percent = 0
        if total_estimate_seconds > 0:
            total_diff_percent = (total_diff_seconds / total_estimate_seconds) * 100

        diff_color = "normal"
        if total_diff_percent > 0:
            diff_color = "inverse"  # Steve ước tính cao hơn
        elif total_diff_percent < 0:
            diff_color = "off"  # Steve ước tính thấp hơn

        st.metric(
            "Tổng chênh lệch",
            f"{total_diff_hours:+.1f}h ({total_diff_percent:+.1f}%)",
            delta_color=diff_color,
        )

    with col2:
        avg_completion_steve = df["% hoàn thành (theo Steve)"].mean()
        st.metric("% hoàn thành TB (theo Steve)", f"{avg_completion_steve:.1f}%")

    with col3:
        avg_completion_original = df["% hoàn thành (theo dự kiến)"].mean()
        st.metric("% hoàn thành TB (theo dự kiến)", f"{avg_completion_original:.1f}%")

    with col4:
        completion_diff = avg_completion_original - avg_completion_steve
        diff_color = "normal"
        if completion_diff > 0:
            diff_color = "inverse"  # Hoàn thành theo dự kiến cao hơn
        elif completion_diff < 0:
            diff_color = "off"  # Hoàn thành theo Steve cao hơn

        st.metric(
            "Chênh lệch % hoàn thành",
            f"{completion_diff:+.1f}%",
            delta_color=diff_color,
            help="Chênh lệch giữa % hoàn thành theo dự kiến và theo Steve. Giá trị dương có nghĩa là % hoàn thành theo dự kiến cao hơn.",
        )


def display_chart(df, diff_type="hours"):
    """Hiển thị biểu đồ phân tích

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu issues
        diff_type (str): Loại chênh lệch hiển thị ('hours' hoặc 'percent')
    """
    st.subheader("Phân tích Steve Estimate vs Thời gian dự kiến")

    # Tạo layout 2 cột
    col1, col2 = st.columns(2)

    with col1:
        # Bảng danh sách các issue có chênh lệch giờ lớn nhất
        st.subheader("Issues có chênh lệch lớn nhất")

        # Chuẩn bị dữ liệu cho hiển thị
        # Sắp xếp theo chênh lệch giờ (tuyệt đối) từ lớn đến nhỏ
        sorted_df = df.copy()
        sorted_df["Chênh lệch tuyệt đối (s)"] = sorted_df["Chênh lệch (s)"].abs()
        sorted_df = sorted_df.sort_values(
            by="Chênh lệch tuyệt đối (s)", ascending=False
        )

        # Chọn các cột cần hiển thị
        display_cols = [
            "Key",
            "Summary",
            "Steve Estimate (h)",
            "Thời gian dự kiến (h)",
            "Chênh lệch (h)",
            "Chênh lệch (%)",
        ]

        # Định dạng cột Chênh lệch (%) để hiển thị dấu + hoặc - và 1 số thập phân
        sorted_df["Chênh lệch (%)"] = sorted_df["Chênh lệch (%)"].apply(
            lambda x: f"{x:+.1f}%" if pd.notnull(x) else "N/A"
        )

        # Lấy top 10 issues có chênh lệch lớn nhất
        top_issues = sorted_df[display_cols].head(10)

        # Tạo màu cho các giá trị chênh lệch
        def color_diff(val):
            if isinstance(val, str) and ("+" in val or "-" in val):
                if "+" in val:
                    return "color: green"
                elif "-" in val:
                    return "color: red"
            return ""

        # Hiển thị DataFrame
        st.dataframe(
            top_issues,
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        # Biểu đồ Population Pyramid cho chênh lệch
        # Chia dữ liệu thành hai nhóm: chênh lệch dương và chênh lệch âm
        diff_values = df["Chênh lệch (s)"] / 3600  # Chuyển từ giây sang giờ
        title = "Phân bố chênh lệch giữa Steve Estimate và Thời gian dự kiến (giờ)"
        x_title = "Chênh lệch (giờ)"

        # Phân nhóm các giá trị chênh lệch
        # Định nghĩa các khoảng (bins) cho chênh lệch giờ
        # Khoảng giá trị sẽ được hiển thị trên trục x
        bins = [0, 1, 2, 3, 4, 6, 8, float("inf")]
        bin_labels = ["0", "1", "2", "3", "4", "6", "8"]

        # Tạo DataFrame cho biểu đồ
        positive_values = diff_values[diff_values >= 0]
        negative_values = diff_values[diff_values < 0]

        # Đếm số lượng giá trị trong mỗi bin
        pos_counts = []
        neg_counts = []

        # Xử lý giá trị dương (Trước hạn)
        for i in range(len(bins) - 1):
            if i < len(bins) - 1:
                count = len(
                    positive_values[
                        (positive_values >= bins[i]) & (positive_values < bins[i + 1])
                    ]
                )
                pos_counts.append(count)

        # Xử lý giá trị âm (Quá hạn) - lấy giá trị tuyệt đối để phân nhóm
        for i in range(len(bins) - 1):
            if i < len(bins) - 1:
                count = len(
                    negative_values[
                        (negative_values.abs() >= bins[i])
                        & (negative_values.abs() < bins[i + 1])
                    ]
                )
                neg_counts.append(count)

        # Tạo biểu đồ - đã xoay trục x, y
        fig = go.Figure()

        # Thêm dữ liệu "Trước hạn" (giá trị dương)
        fig.add_trace(
            go.Bar(
                x=pos_counts,
                y=bin_labels,
                name="Trước hạn",
                orientation="h",
                marker=dict(color="#2ca02c"),  # Màu xanh lá
                text=pos_counts,
                textposition="auto",
                hoverinfo="text",
                hovertext=[f"Trước hạn: {count} issues" for count in pos_counts],
            )
        )

        # Thêm dữ liệu "Quá hạn" (giá trị âm)
        fig.add_trace(
            go.Bar(
                x=[
                    -count for count in neg_counts
                ],  # Chuyển thành giá trị âm để hiển thị ở bên trái
                y=bin_labels,
                name="Quá hạn",
                orientation="h",
                marker=dict(color="#d62728"),  # Màu đỏ
                text=neg_counts,
                textposition="auto",
                hoverinfo="text",
                hovertext=[f"Quá hạn: {count} issues" for count in neg_counts],
            )
        )

        # Cấu hình layout
        fig.update_layout(
            title=title,
            xaxis=dict(
                title="Số lượng issue",
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor="black",
                showgrid=True,
            ),
            yaxis=dict(
                title=x_title,  # Lưu ý: x_title là "Chênh lệch (giờ)"
                showgrid=True,
            ),
            barmode="relative",
            height=400,
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=50, r=50, t=80, b=50),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Thêm thống kê chênh lệch bên dưới biểu đồ
        st.subheader("Thống kê chênh lệch")

        # Tạo 3 cột cho các chỉ số thống kê
        stat_col1, stat_col2, stat_col3 = st.columns(3)

        with stat_col1:
            max_diff = diff_values.max()
            min_diff = diff_values.min()
            avg_diff = diff_values.mean()
            median_diff = diff_values.median()

            st.metric("Chênh lệch lớn nhất", f"{max_diff:.1f}h")
            st.metric("Chênh lệch nhỏ nhất", f"{min_diff:.1f}h")

        with stat_col2:
            st.metric("Chênh lệch trung bình", f"{avg_diff:.1f}h")
            st.metric("Chênh lệch trung vị", f"{median_diff:.1f}h")

        with stat_col3:
            # Đếm số lượng issue có chênh lệch dương và âm
            positive_count = len(positive_values)
            negative_count = len(negative_values)
            total_count = len(diff_values)

            st.metric(
                "Số issues trước hạn",
                f"{positive_count} ({positive_count/total_count*100:.1f}%)",
            )
            st.metric(
                "Số issues quá hạn",
                f"{negative_count} ({negative_count/total_count*100:.1f}%)",
            )

    # Bảng và biểu đồ tổng hợp theo Assignee
    st.subheader("Tổng hợp theo Assignee")

    # Tạo DataFrame tổng hợp
    if not df.empty and "Assignee" in df.columns:
        # Nhóm dữ liệu theo Assignee
        assignee_stats = []

        for assignee, group in df.groupby("Assignee"):
            stats = {
                "Assignee": assignee,
                "Số issues": len(group),
                "Steve Estimate (h)": group["Steve Estimate (h)"].sum(),
                "Thời gian dự kiến (h)": group["Thời gian dự kiến (s)"].sum() / 3600,
                "Thời gian đã log (h)": group["Thời gian đã log (s)"].sum() / 3600,
                "Chênh lệch (h)": group["Chênh lệch (s)"].sum() / 3600,
                "% hoàn thành (theo dự kiến)": group[
                    "% hoàn thành (theo dự kiến)"
                ].mean(),
                "% hoàn thành (theo Steve)": group["% hoàn thành (theo Steve)"].mean(),
            }

            # Tính chênh lệch % giữa thời gian dự kiến và Steve Estimate
            if stats["Thời gian dự kiến (h)"] > 0:
                stats["Chênh lệch (%)"] = (
                    stats["Chênh lệch (h)"] / stats["Thời gian dự kiến (h)"]
                ) * 100
            else:
                stats["Chênh lệch (%)"] = 0

            # Tính chênh lệch giữa 2 tỷ lệ hoàn thành
            stats["Chênh lệch % hoàn thành"] = (
                stats["% hoàn thành (theo dự kiến)"]
                - stats["% hoàn thành (theo Steve)"]
            )

            assignee_stats.append(stats)

        if assignee_stats:
            # Tạo DataFrame
            assignee_df = pd.DataFrame(assignee_stats)

            # Làm tròn các số
            numeric_cols = assignee_df.select_dtypes(include=[np.number]).columns
            assignee_df[numeric_cols] = assignee_df[numeric_cols].round(1)

            # Hiển thị bảng
            st.dataframe(
                assignee_df,
                use_container_width=True,
                hide_index=True,
            )

            # Tạo biểu đồ so sánh
            col1, col2 = st.columns(2)

            with col1:
                # Biểu đồ so sánh thời gian
                fig = go.Figure()

                # Sắp xếp theo Steve Estimate
                plot_df = assignee_df.sort_values(
                    by="Steve Estimate (h)", ascending=False
                )

                # Thêm Steve Estimate
                fig.add_trace(
                    go.Bar(
                        name="Steve Estimate (h)",
                        x=plot_df["Assignee"],
                        y=plot_df["Steve Estimate (h)"],
                        marker_color="#1f77b4",
                    )
                )

                # Thêm Thời gian dự kiến
                fig.add_trace(
                    go.Bar(
                        name="Thời gian dự kiến (h)",
                        x=plot_df["Assignee"],
                        y=plot_df["Thời gian dự kiến (h)"],
                        marker_color="#ff7f0e",
                    )
                )

                # Thêm Thời gian đã log
                fig.add_trace(
                    go.Bar(
                        name="Thời gian đã log (h)",
                        x=plot_df["Assignee"],
                        y=plot_df["Thời gian đã log (h)"],
                        marker_color="#2ca02c",
                    )
                )

                # Cấu hình layout
                fig.update_layout(
                    title="So sánh thời gian theo Assignee",
                    xaxis_title="Assignee",
                    yaxis_title="Thời gian (giờ)",
                    barmode="group",
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Biểu đồ chênh lệch giờ theo Assignee
                fig = go.Figure()

                # Sắp xếp theo chênh lệch tuyệt đối
                plot_df = assignee_df.copy()
                plot_df["Chênh lệch tuyệt đối (h)"] = plot_df["Chênh lệch (h)"].abs()
                plot_df = plot_df.sort_values(
                    by="Chênh lệch tuyệt đối (h)", ascending=False
                )

                # Tạo màu cho các cột
                colors = []
                for val in plot_df["Chênh lệch (h)"]:
                    if val > 0:
                        colors.append("#2ca02c")  # Xanh lá cho chênh lệch dương
                    else:
                        colors.append("#d62728")  # Đỏ cho chênh lệch âm

                # Thêm chênh lệch giờ
                fig.add_trace(
                    go.Bar(
                        name="Chênh lệch (h)",
                        x=plot_df["Assignee"],
                        y=plot_df["Chênh lệch (h)"],
                        marker_color=colors,
                        text=plot_df["Chênh lệch (h)"].round(1).astype(str) + "h",
                        textposition="auto",
                    )
                )

                # Cấu hình layout
                fig.update_layout(
                    title="Chênh lệch giờ theo Assignee",
                    xaxis_title="Assignee",
                    yaxis_title="Chênh lệch (giờ)",
                    height=400,
                )

                # Thêm đường zero line
                fig.update_layout(
                    yaxis=dict(
                        zeroline=True,
                        zerolinewidth=2,
                        zerolinecolor="black",
                    )
                )

                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu để phân tích theo Assignee")
    else:
        st.info("Không đủ dữ liệu để phân tích theo Assignee")


def main():
    """Hàm chính của ứng dụng"""
    st.title("Steve Estimate")

    # Khởi tạo service
    steve_est_service = SteveEstimateService()

    # Hiển thị dự án đang sử dụng
    st.toast(f"Đang sử dụng dự án: {DEFAULT_PROJECT}", icon="🔍")

    # Kiểm tra kết nối
    jira_connected = True  # Giả sử kết nối thành công

    if not jira_connected:
        st.error("Không thể kết nối đến Jira API. Vui lòng kiểm tra cấu hình kết nối!")
        st.stop()

    # Tải danh sách sprint từ API
    with st.spinner("Đang tải danh sách sprint từ Jira API..."):
        # Kiểm tra xem sprints đã có trong session_state chưa
        if "sprints" not in st.session_state:
            st.session_state.sprints = steve_est_service.get_all_sprints(
                DEFAULT_PROJECT
            )
        sprints = st.session_state.sprints

    if not sprints:
        st.error(f"Không tìm thấy sprint nào cho dự án {DEFAULT_PROJECT}")
        st.stop()

    # Format sprint options cho dropdown selection
    sprint_options = []

    # Thêm option "Tất cả" cho sprint
    sprint_options.append(
        {"display": "Tất cả", "id": None, "data": {"name": "Tất cả", "state": "ALL"}}
    )

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

    # Sắp xếp sprints: Active first, then by name
    sprint_options[1:] = sorted(
        sprint_options[1:],
        key=lambda x: (
            (
                0
                if x["data"].get("state") == "active"
                else (1 if x["data"].get("state") == "future" else 2)
            ),
            x["data"].get("name", ""),
        ),
    )

    # Bố trí các bộ lọc song song
    col1, col2 = st.columns(2)

    # Selection với "Tất cả" được chọn mặc định (index=0)
    with col1:
        selected_sprint_idx = st.selectbox(
            "Chọn Sprint",
            options=range(len(sprint_options)),
            format_func=lambda i: sprint_options[i]["display"],
            index=0,  # Mặc định chọn "Tất cả"
            key="selected_sprint_idx",
        )

    # Bộ lọc trạng thái
    with col2:
        status_options = {
            "dev_done": "Dev Done (bao gồm Dev Done, Test Done, Deployed, Done)",
            "all": "Tất cả",
        }
        selected_status = st.selectbox(
            "Chọn trạng thái",
            options=list(status_options.keys()),
            format_func=lambda x: status_options[x],
            index=0,  # Mặc định chọn "Dev Done"
            key="selected_status",
        )

    selected_sprint = sprint_options[selected_sprint_idx]
    sprint_id = selected_sprint["id"]  # Có thể là None nếu chọn "Tất cả"

    # Tìm kiếm issues
    with st.spinner(f"Đang tìm kiếm issues có Steve Estimate..."):
        # Kiểm tra xem sprint_id và issues đã có trong session_state chưa
        should_reload_data = (
            "current_steve_sprint_id" not in st.session_state
            or st.session_state.current_steve_sprint_id != sprint_id
            or "steve_issues" not in st.session_state
        )

        if should_reload_data:
            issues = steve_est_service.search_issues_with_steve_estimate(sprint_id)
            st.session_state.steve_issues = issues
            st.session_state.current_steve_sprint_id = sprint_id
        else:
            issues = st.session_state.steve_issues

    if not issues:
        st.warning(
            "Không tìm thấy issues nào có Steve Estimate trong điều kiện tìm kiếm."
        )
        st.stop()

    # Xử lý dữ liệu issues
    with st.spinner("Đang xử lý dữ liệu..."):
        df = process_issues_data(issues, steve_est_service, selected_status)

    if df.empty:
        st.warning("Không có dữ liệu để hiển thị sau khi xử lý.")
        st.stop()

    # Hiển thị các số liệu tổng hợp
    display_summary_metrics(df)

    # Hiển thị biểu đồ
    display_chart(df)

    # Hiển thị bảng dữ liệu
    st.subheader("Bảng dữ liệu chi tiết")

    # Bỏ các cột không cần hiển thị
    display_df = df.drop(
        columns=["Thời gian dự kiến (s)", "Chênh lệch (s)", "Thời gian đã log (s)"]
    )

    # Hiển thị DataFrame
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
