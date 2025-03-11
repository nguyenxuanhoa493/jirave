from src.services.jira_client import JiraClient
import sys
import json


def update_field(jira_client, issue_key, field_id, field_value):

    # Thử với 3 định dạng khác nhau
    field_formats = [
        field_value,  # Giá trị trực tiếp
        {"value": field_value},  # Định dạng option
        [{"value": field_value}],  # Định dạng array
    ]

    for format_value in field_formats:
        fields_data = {field_id: format_value}
        print(f"Thử với định dạng: {format_value}")

        if jira_client.update_issue(issue_key, fields_data):
            print(f"Cập nhật thành công với định dạng: {format_value}")
            return True

    print(f"Không thể cập nhật field '{field_id}' cho issue {issue_key}")
    return False


def main():
    """Hàm chính của script"""
    # Kiểm tra tham số dòng lệnh
    if len(sys.argv) < 4:
        print(
            "Sử dụng: python src/script/update_issue_field.py <issue_key> <field_name> <field_value>"
        )
        return

    issue_key = "CLD-388"
    field_name = "Sprint Dashboad"
    field_value = "YES"

    # Khởi tạo Jira client
    jira_client = JiraClient()

    # Cập nhật field
    success = update_field(jira_client, issue_key, field_name, field_value)

    if success:
        print(f"\nĐã cập nhật thành công field '{field_name}' cho issue {issue_key}")
    else:
        print(f"\nKhông thể cập nhật field '{field_name}' cho issue {issue_key}")


if __name__ == "__main__":
    main()
