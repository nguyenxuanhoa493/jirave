import pandas as pd
from datetime import datetime, timedelta
import streamlit as st


class DataProcessor:
    """Class xử lý và chuẩn bị dữ liệu cho hiển thị"""

    @staticmethod
    def filter_by_date_range(worklogs, start_date, end_date, timezone):
        """Lọc worklogs theo khoảng thời gian

        Args:
            worklogs (list): Danh sách các worklog
            start_date (date): Ngày bắt đầu
            end_date (date): Ngày kết thúc
            timezone (str): Múi giờ

        Returns:
            list: Danh sách worklog đã lọc
        """
        filtered_logs = []

        # Đảm bảo end_date bao gồm cả ngày cuối
        end_date_inclusive = end_date + timedelta(days=1)

        for log in worklogs:
            # Chuyển đổi thời gian từ chuỗi sang datetime
            started = datetime.fromisoformat(log["started"].replace("Z", "+00:00"))

            # Kiểm tra nếu worklog nằm trong khoảng thời gian
            if start_date <= started.date() < end_date_inclusive:
                filtered_logs.append(log)

        return filtered_logs

    @staticmethod
    def filter_by_team(worklogs, team_name, all_users):
        """Lọc worklogs theo team

        Args:
            worklogs (list): Danh sách các worklog
            team_name (str): Tên team để lọc
            all_users (dict): Danh sách tất cả người dùng và teams của họ

        Returns:
            list: Danh sách worklog đã lọc
        """
        if team_name == "All Teams":
            return worklogs

        filtered_logs = []

        # Lọc theo team
        for log in worklogs:
            author = log.get("author", {}).get("displayName", "")
            if author in all_users and team_name in all_users[author]:
                filtered_logs.append(log)

        return filtered_logs

    @staticmethod
    def process_report_data(worklogs):
        """Xử lý dữ liệu báo cáo từ worklogs

        Args:
            worklogs (list): Danh sách các worklog

        Returns:
            dict: Dữ liệu báo cáo đã xử lý
        """
        # Khởi tạo cấu trúc dữ liệu
        report_data = {
            "total_hours": 0,
            "user_summary": {},
            "daily_summary": {},
            "issue_summary": {},
        }

        for log in worklogs:
            author = log.get("author", {}).get("displayName", "Unknown")
            time_spent_seconds = log.get("timeSpentSeconds", 0)
            time_spent_hours = time_spent_seconds / 3600
            issue_key = log.get("issueKey", "Unknown")

            # Chuyển đổi thời gian bắt đầu
            started = datetime.fromisoformat(log["started"].replace("Z", "+00:00"))
            date_str = started.date().isoformat()

            # Tính tổng số giờ
            report_data["total_hours"] += time_spent_hours

            # Thêm vào tổng hợp theo người dùng
            if author not in report_data["user_summary"]:
                report_data["user_summary"][author] = 0
            report_data["user_summary"][author] += time_spent_hours

            # Thêm vào tổng hợp theo ngày
            if date_str not in report_data["daily_summary"]:
                report_data["daily_summary"][date_str] = {}
            if author not in report_data["daily_summary"][date_str]:
                report_data["daily_summary"][date_str][author] = 0
            report_data["daily_summary"][date_str][author] += time_spent_hours

            # Thêm vào tổng hợp theo issue
            if issue_key not in report_data["issue_summary"]:
                report_data["issue_summary"][issue_key] = 0
            report_data["issue_summary"][issue_key] += time_spent_hours

        return report_data

    @staticmethod
    def filter_inactive_users(report_data, hide_inactive=True):
        """Lọc các người dùng không có hoạt động

        Args:
            report_data (dict): Dữ liệu báo cáo
            hide_inactive (bool): Có ẩn người dùng không hoạt động hay không

        Returns:
            dict: Dữ liệu báo cáo đã lọc
        """
        if not hide_inactive:
            return report_data

        # Lọc người dùng từ user_summary
        active_users = {
            user: hours
            for user, hours in report_data["user_summary"].items()
            if hours > 0
        }

        # Cập nhật daily_summary
        for date, users in report_data["daily_summary"].items():
            report_data["daily_summary"][date] = {
                user: hours for user, hours in users.items() if user in active_users
            }

        # Cập nhật user_summary
        report_data["user_summary"] = active_users

        return report_data
