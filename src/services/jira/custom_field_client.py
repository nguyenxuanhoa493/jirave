import streamlit as st
from src.services.jira.base_client import BaseJiraClient


class CustomFieldClient(BaseJiraClient):
    """Client for handling Jira custom fields"""

    def get_custom_fields(self):
        """Get all custom fields

        Returns:
            list: List of custom fields
        """
        response = self.get("field")
        if response and response.status_code == 200:
            # Hiển thị thông tin gỡ lỗi
            all_fields = response.json()
            st.info(f"Tổng số trường: {len(all_fields)}")

            # Lọc chỉ lấy các custom field
            custom_fields = [
                field for field in all_fields if field.get("custom", False)
            ]
            st.info(f"Số trường tùy chỉnh: {len(custom_fields)}")

            # Hiển thị một số trường đầu tiên để kiểm tra
            if all_fields and len(all_fields) > 0:
                st.subheader("Mẫu dữ liệu trường:")
                st.json(all_fields[0])

            return custom_fields
        else:
            if response:
                st.error(f"Lỗi khi gọi API: {response.status_code} - {response.text}")
            else:
                st.error("Không nhận được phản hồi từ API")
            return []

    def get_field_details(self, field_id):
        """Get details for a specific field

        Args:
            field_id (str): The field ID

        Returns:
            dict: Field details
        """
        response = self.get(f"field/{field_id}")
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_custom_field_id(self, field_name):
        """Get the ID of a custom field by name

        Args:
            field_name (str): The custom field name

        Returns:
            str: The custom field ID or None if not found
        """
        response = self.get("field")
        if response and response.status_code == 200:
            for field in response.json():
                if field.get("name") == field_name:
                    return field.get("id")
        return None

    def update_custom_fields(self, issues, data_set):
        """Update custom fields for a set of issues

        Args:
            issues (list): List of issue keys
            data_set (dict): Custom field data to update

        Returns:
            list: List of successful updates
        """
        successful_updates = []
        for issue_key in issues:
            fields_data = {}
            for field_id, value in data_set.items():
                # Chuẩn bị dữ liệu theo định dạng của Jira
                if isinstance(value, str):
                    fields_data[field_id] = value
                elif isinstance(value, dict) and "value" in value:
                    fields_data[field_id] = {"value": value["value"]}
                elif isinstance(value, list):
                    fields_data[field_id] = [{"value": v} for v in value]
                else:
                    fields_data[field_id] = value

            # Gửi yêu cầu cập nhật
            payload = {"fields": fields_data}
            response = self.put(f"issue/{issue_key}", payload)

            if response and response.status_code == 204:
                successful_updates.append(issue_key)

        return successful_updates
