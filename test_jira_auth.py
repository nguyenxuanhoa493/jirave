import os
import json
from dotenv import load_dotenv
from src.services.jira.base_client import BaseJiraClient

# Load environment variables
load_dotenv()


# Hiển thị thông tin kết nối (che một phần token/password)
def mask_string(s, show_first=4, show_last=4):
    if not s:
        return "Không được cấu hình"
    if len(s) <= (show_first + show_last):
        return s
    return s[:show_first] + "*" * (len(s) - show_first - show_last) + s[-show_last:]


# Lấy thông tin từ biến môi trường
jira_url = os.getenv("JIRA_URL")
email = os.getenv("EMAIL")
api_token = os.getenv("API_TOKEN")

# Hiển thị thông tin (đã che)
print(f"JIRA_URL: {jira_url}")
print(f"EMAIL: {email}")
print(f"API_TOKEN: {mask_string(api_token) if api_token else 'Không được cấu hình'}")

# Thử kết nối đến Jira API
client = BaseJiraClient()
response = client.get("field")

# Hiển thị kết quả
if response and response.status_code == 200:
    print("\n✅ Kết nối thành công đến Jira API!")
    fields = response.json()
    print(f"Tổng số trường: {len(fields)}")

    # Lọc chỉ lấy các custom field
    custom_fields = [field for field in fields if field.get("custom", False)]
    print(f"Số trường tùy chỉnh: {len(custom_fields)}")

    # Hiển thị mẫu dữ liệu
    if fields:
        print("\nMẫu dữ liệu trường đầu tiên:")
        print(json.dumps(fields[0], indent=2))

    # Hiển thị danh sách các custom field
    if custom_fields:
        print("\nDanh sách trường tùy chỉnh:")
        for i, field in enumerate(
            custom_fields[:5], 1
        ):  # Chỉ hiển thị 5 trường đầu tiên
            print(f"{i}. {field.get('name')} (ID: {field.get('id')})")
        if len(custom_fields) > 5:
            print(f"... và {len(custom_fields) - 5} trường khác")
    else:
        print("\nKhông tìm thấy trường tùy chỉnh nào.")
else:
    if response:
        print(f"\n❌ Lỗi kết nối: {response.status_code} - {response.text}")
    else:
        print("\n❌ Không nhận được phản hồi từ API")
