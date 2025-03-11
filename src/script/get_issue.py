from src.services.jira_client import JiraClient
import json
import sys


def print_issue_details(issue_data):
    """In thông tin chi tiết của issue"""
    print("\n=== THÔNG TIN ISSUE ===")
    print(f"Key: {issue_data.get('key')}")
    print(f"Summary: {issue_data.get('fields', {}).get('summary')}")
    print(f"Status: {issue_data.get('fields', {}).get('status', {}).get('name')}")
    print(
        f"Issue Type: {issue_data.get('fields', {}).get('issuetype', {}).get('name')}"
    )
    print(
        f"Assignee: {issue_data.get('fields', {}).get('assignee', {}).get('displayName', 'Unassigned')}"
    )

    print("\n=== CUSTOM FIELDS ===")
    for field_key, field_value in issue_data.get("fields", {}).items():
        if field_key.startswith("customfield_") and field_value is not None:
            print(f"{field_key}: {field_value}")


def save_issue_json(issue_data, issue_key):
    """Lưu thông tin issue ra file JSON"""
    filename = f"{issue_key}_info.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(issue_data, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu thông tin chi tiết vào file: {filename}")


def main():
    """Hàm chính của script"""
    # Kiểm tra tham số dòng lệnh
    if len(sys.argv) < 2:
        print("Sử dụng: python src/script/get_issue.py <issue_key>")
        return

    issue_key = sys.argv[1]

    # Khởi tạo Jira client
    jira_client = JiraClient()

    # Lấy thông tin issue
    issue_data = jira_client.get_issue(
        issue_key, custom_field_ids=["customfield_10160", "customfield_10161"]
    )

    if not issue_data:
        print(f"Không tìm thấy issue với key: {issue_key}")
        return

    # In thông tin
    # print_issue_details(issue_data)

    # Lưu thông tin ra file
    save_issue_json(issue_data, issue_key)


if __name__ == "__main__":
    main()
