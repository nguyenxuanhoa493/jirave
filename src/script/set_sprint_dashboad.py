from collections import Counter
from src.services.jira_client import JiraClient
import sys


def get_target_sprint(jira_client, sprint_name):
    """Lấy thông tin sprint theo tên"""
    all_sprints = jira_client.get_all_sprints("CLD")
    for sprint in all_sprints:
        if sprint["name"] == sprint_name:
            return sprint
    return None


def print_status_statistics(status_counts, target_statuses, total_issues):
    """In thống kê số lượng issue theo trạng thái"""
    print("\nThống kê issue theo trạng thái trong CLD Sprint 11:")
    print("-" * 50)
    for status in target_statuses:
        count = status_counts.get(status, 0)
        print(f"{status}: {count} issues")
    print(f"\nTổng số issue: {total_issues}")


def print_update_results(results):
    """In kết quả cập nhật custom fields"""
    print("\nKết quả cập nhật custom fields:")
    print("-" * 50)
    for field_name, result in results.items():
        print(f"\n{field_name}:")
        print(f"Trạng thái: {'Thành công' if result['success'] else 'Thất bại'}")
        print(f"Thông báo: {result['message']}")
        if result["success"]:
            print(f"Số issue đã cập nhật: {result['updated_issues']}")


def inspect_custom_fields(jira_client, field_names=None):
    """Kiểm tra và hiển thị thông tin chi tiết về custom fields"""
    custom_fields = jira_client.get_custom_fields()

    if field_names:
        print(f"\nTìm kiếm thông tin về {len(field_names)} custom field:")
        for name in field_names:
            found = False
            for field in custom_fields:
                if field.get("name") == name:
                    found = True
                    print(f"\nTên: {field.get('name')}")
                    print(f"ID: {field.get('id')}")
                    print(f"Kiểu: {field.get('schema', {}).get('type')}")
                    print(f"Custom: {field.get('custom')}")
                    print(f"Thông tin schema: {field.get('schema')}")
                    break
            if not found:
                print(f"\nKhông tìm thấy field '{name}'")
    else:
        print(f"\nDanh sách {len(custom_fields)} custom field:")
        for field in custom_fields:
            print(f"{field.get('name')} (ID: {field.get('id')})")

    return custom_fields


def update_issue_key(jira_client, issue_key, sprint_name):
    """Cập nhật các custom field cho một issue cụ thể

    Args:
        jira_client (JiraClient): Client Jira API
        issue_key (str): Key của issue cần cập nhật
        sprint_name (str): Tên của sprint

    Returns:
        dict: Kết quả cập nhật với trạng thái thành công/thất bại
    """
    print(f"\nCập nhật custom fields cho issue {issue_key}...")

    # Các field cần cập nhật với định dạng đã biết từ JSON
    fields_data = {
        # Show in Dashboard - sử dụng định dạng option
        "customfield_10160": {"value": "YES"},
        # Sprint Dashboard - sử dụng định dạng option
        "customfield_10161": {"value": sprint_name},
    }

    # Cập nhật issue
    success = jira_client.update_issue(issue_key, fields_data)

    result = {
        "success": success,
        "message": "Cập nhật thành công" if success else "Cập nhật thất bại",
    }

    print(f"Kết quả: {result['message']}")
    return result


def main():
    """Hàm chính của script"""
    # Kiểm tra tham số dòng lệnh
    if len(sys.argv) > 1:
        # Nếu có tham số, coi đó là issue key cần cập nhật
        issue_key = sys.argv[1]
        jira_client = JiraClient()
        update_issue_key(jira_client, issue_key, "CLD Sprint 11")
        return

    # Khởi tạo Jira client
    jira_client = JiraClient()

    # Các thông số cấu hình
    SPRINT_NAME = "CLD Sprint 11"
    TARGET_STATUSES = ["In Progress", "To Do", "Reopen"]

    # Kiểm tra thông tin về custom fields
    print("\n=== KIỂM TRA CUSTOM FIELDS ===")
    inspect_custom_fields(jira_client, ["Show in Dashboard", "Sprint Dashboard"])

    # Lấy thông tin sprint
    target_sprint = get_target_sprint(jira_client, SPRINT_NAME)
    if not target_sprint:
        print(f"Không tìm thấy sprint '{SPRINT_NAME}'")
        return

    # Lấy danh sách issues
    sprint_issues = jira_client.get_sprint_issues(
        sprint_id=target_sprint["id"], status_names=TARGET_STATUSES
    )

    # In thống kê
    status_counts = Counter(
        issue["fields"]["status"]["name"] for issue in sprint_issues
    )
    print_status_statistics(status_counts, TARGET_STATUSES, len(sprint_issues))

    if not sprint_issues:
        print("Không có issue nào để cập nhật!")
        return

    # Cập nhật từng issue với định dạng biết trước
    success_count = 0
    for issue in sprint_issues:
        issue_key = issue["key"]
        result = update_issue_key(jira_client, issue_key, SPRINT_NAME)
        if result["success"]:
            success_count += 1

    print(f"\nĐã cập nhật thành công {success_count}/{len(sprint_issues)} issues")


if __name__ == "__main__":
    main()
