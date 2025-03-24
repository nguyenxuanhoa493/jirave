def get_current_sprint(self):
    """Lấy thông tin sprint hiện tại đang hoạt động

    Returns:
        dict: Thông tin sprint hiện tại
    """
    sprints = self.get_sprints()
    active_sprints = [s for s in sprints if s.get("state") == "active"]
    return active_sprints[0] if active_sprints else None


def get_sprint_document(self, sprint_id):
    """Lấy thông tin document của sprint từ MongoDB

    Args:
        sprint_id (str): ID của sprint

    Returns:
        dict: Document sprint từ MongoDB hoặc None nếu không tìm thấy
    """
    if not self.jira.mongo_client.is_connected():
        return None

    try:
        collection = self.jira.mongo_client.db["data"]
        sprint_document = collection.find_one({"_id": f"sprint_{sprint_id}"})
        return sprint_document
    except Exception as e:
        print(f"Lỗi khi lấy document sprint từ MongoDB: {str(e)}")
        return None


def calculate_sprint_target_work_days(self, sprint_name):
    """Tính toán số ngày làm việc mục tiêu dựa trên tên sprint

    Args:
        sprint_name (str): Tên của sprint

    Returns:
        int: Số ngày làm việc mục tiêu của sprint
    """
    # Implementation of the method
    pass
