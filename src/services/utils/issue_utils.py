def safe_get_status(issue, field_name="status"):
    """Lấy trạng thái từ issue một cách an toàn

    Args:
        issue (dict): Dữ liệu issue
        field_name (str): Tên trường cần lấy (status hoặc current_status)

    Returns:
        str: Giá trị trạng thái hợp lệ
    """
    value = issue.get(field_name)

    # Kiểm tra kiểu dữ liệu và trả về chuỗi phù hợp
    if value is None:
        return ""
    elif isinstance(value, dict) and "name" in value:
        return value.get("name", "")
    elif isinstance(value, (int, float)):
        return str(value)
    elif value == "None" or value == "null":
        return ""
    else:
        return str(value)
