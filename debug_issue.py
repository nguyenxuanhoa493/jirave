#!/usr/bin/env python3
import os
import sys
import json
from pprint import pprint

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import các module cần thiết
from src.services.jira_client import JiraClient
from src.config.config import DEFAULT_PROJECT


def debug_issue(issue_key="CLD-501"):
    """Debug thông tin chi tiết của một issue cụ thể

    Args:
        issue_key (str): Key của issue cần debug
    """
    print(f"===== BẮT ĐẦU DEBUG ISSUE: {issue_key} =====")

    # Khởi tạo Jira client
    jira = JiraClient()

    # Lấy thông tin chi tiết của issue
    fields = [
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

    try:
        # Lấy thông tin issue
        issue = jira.get_issue(issue_key, fields)

        if not issue:
            print(f"KHÔNG TÌM THẤY ISSUE: {issue_key}")
            return

        # In thông tin cơ bản
        print("\n=== THÔNG TIN CƠ BẢN ===")
        print(f"Key: {issue_key}")
        print(f"Các trường có sẵn: {list(issue.get('fields', {}).keys())}")

        # In chi tiết từng trường
        fields_data = issue.get("fields", {})

        print("\n=== CHI TIẾT TỪNG TRƯỜNG ===")

        # 1. Tiêu đề
        summary = fields_data.get("summary", "N/A")
        print(f"Tiêu đề: {summary}")

        # 2. Loại issue
        issuetype = fields_data.get("issuetype", {})
        issuetype_name = issuetype.get("name", "N/A") if issuetype else "N/A"
        print(f"Loại issue: {issuetype_name}")
        print(f"Chi tiết issuetype: {issuetype}")

        # 3. Steve Estimate
        steve_estimate = fields_data.get("customfield_10159")
        print(f"Steve Estimate (raw): {steve_estimate}")
        print(f"Kiểu dữ liệu: {type(steve_estimate)}")

        if steve_estimate is None:
            steve_estimate_value = 0
        elif isinstance(steve_estimate, dict):
            steve_estimate_value = float(steve_estimate.get("value", 0))
        else:
            try:
                steve_estimate_value = float(steve_estimate)
            except (ValueError, TypeError):
                steve_estimate_value = 0

        print(f"Steve Estimate (sau xử lý): {steve_estimate_value}")

        # 4. Thời gian dự kiến
        timeoriginalestimate = fields_data.get("timeoriginalestimate")
        timeestimate = fields_data.get("timeestimate")
        print(f"Thời gian dự kiến ban đầu (giây): {timeoriginalestimate}")
        print(f"Thời gian dự kiến hiện tại (giây): {timeestimate}")

        # 5. Thời gian đã log
        timespent = fields_data.get("timespent")
        print(f"Thời gian đã log (giây): {timespent}")

        # 6. Trạng thái
        status = fields_data.get("status", {})
        status_name = status.get("name", "N/A") if status else "N/A"
        print(f"Trạng thái: {status_name}")
        print(f"Chi tiết status: {status}")

        # 7. Người được gán
        assignee = fields_data.get("assignee", {})
        assignee_name = (
            assignee.get("displayName", "Không có") if assignee else "Không có"
        )
        print(f"Người được gán: {assignee_name}")
        print(f"Chi tiết assignee: {assignee}")

        # 8. Subtasks
        subtasks = fields_data.get("subtasks", [])
        print(f"\n=== SUBTASKS ({len(subtasks)}) ===")

        if subtasks:
            for i, subtask in enumerate(subtasks):
                print(f"\nSubtask #{i+1}:")
                print(f"  Key: {subtask.get('key', 'N/A')}")
                subtask_fields = subtask.get("fields", {})
                if subtask_fields:
                    print(f"  Tiêu đề: {subtask_fields.get('summary', 'N/A')}")
                    subtask_status = subtask_fields.get("status", {})
                    if subtask_status:
                        print(f"  Trạng thái: {subtask_status.get('name', 'N/A')}")
                else:
                    print("  Không có dữ liệu fields")

                # Lấy chi tiết subtask
                try:
                    subtask_key = subtask.get("key")
                    if subtask_key:
                        subtask_detail = jira.get_issue(subtask_key)
                        if subtask_detail and "fields" in subtask_detail:
                            subtask_timeoriginalestimate = subtask_detail["fields"].get(
                                "timeoriginalestimate"
                            )
                            subtask_timeestimate = subtask_detail["fields"].get(
                                "timeestimate"
                            )
                            subtask_timespent = subtask_detail["fields"].get(
                                "timespent"
                            )

                            print(
                                f"  Thời gian dự kiến ban đầu (giây): {subtask_timeoriginalestimate}"
                            )
                            print(
                                f"  Thời gian dự kiến hiện tại (giây): {subtask_timeestimate}"
                            )
                            print(f"  Thời gian đã log (giây): {subtask_timespent}")
                except Exception as e:
                    print(f"  Lỗi khi lấy chi tiết subtask: {str(e)}")
        else:
            print("Không có subtask nào")

    except Exception as e:
        print(f"LỖI KHI DEBUG: {str(e)}")
        import traceback

        traceback.print_exc()

    print("\n===== KẾT THÚC DEBUG =====")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        issue_key = sys.argv[1]
        debug_issue(issue_key)
    else:
        debug_issue()  # Mặc định debug CLD-501
