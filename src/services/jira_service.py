def get_sprint_board_info(self, sprint_id):
    """Lấy thông tin dashboard của sprint

    Args:
        sprint_id (str): ID của sprint

    Returns:
        dict: Thông tin sprint từ dashboard
    """
    # Lấy board_id từ config
    board_id = self.config.get("board_id")
    if not board_id:
        return None

    # Lấy danh sách sprint của board
    sprints_response = self.sprint_client.get(
        f"board/{board_id}/sprint/{sprint_id}", use_agile_api=True
    )
    if sprints_response.status_code != 200:
        print(f"Lỗi khi lấy thông tin sprint {sprint_id}: {sprints_response.text}")
        return None

    return sprints_response.json()

def get_sprint_document(self, sprint_id):
    """Lấy thông tin document của sprint từ MongoDB

    Args:
        sprint_id (str): ID của sprint

    Returns:
        dict: Document sprint từ MongoDB hoặc None nếu không tìm thấy
    """
    if not self.mongo_client.is_connected():
        return None
        
    try:
        collection = self.mongo_client.db["data"]
        sprint_document = collection.find_one({"_id": f"sprint_{sprint_id}"})
        return sprint_document
    except Exception as e:
        print(f"Lỗi khi lấy document sprint từ MongoDB: {str(e)}")
        return None

def get_status_transitions(self, issue_id):
    """Lấy các bước chuyển trạng thái có thể của một issue 