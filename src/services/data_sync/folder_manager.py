import os
import shutil

# Định nghĩa đường dẫn lưu trữ dữ liệu
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data"
)
SPRINTS_DIR = os.path.join(DATA_DIR, "sprints")
ISSUES_DIR = os.path.join(DATA_DIR, "issues")
WORKLOGS_DIR = os.path.join(DATA_DIR, "worklogs")
CHANGELOG_DIR = os.path.join(DATA_DIR, "changelog")


def ensure_data_dirs():
    """Đảm bảo các thư mục dữ liệu đã tồn tại"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SPRINTS_DIR, exist_ok=True)
    os.makedirs(ISSUES_DIR, exist_ok=True)
    os.makedirs(WORKLOGS_DIR, exist_ok=True)
    os.makedirs(CHANGELOG_DIR, exist_ok=True)


def clear_local_data(confirm_callback=None):
    """Xóa tất cả dữ liệu local

    Args:
        confirm_callback (callable, optional): Hàm callback để xác nhận việc xóa dữ liệu

    Returns:
        bool: True nếu xóa thành công, False nếu không
    """
    try:
        # Nếu có callback xác nhận và không xác nhận được, return False
        if confirm_callback and not confirm_callback():
            return False

        # Xóa thư mục dữ liệu nếu tồn tại
        if os.path.exists(SPRINTS_DIR):
            shutil.rmtree(SPRINTS_DIR)
        if os.path.exists(ISSUES_DIR):
            shutil.rmtree(ISSUES_DIR)
        if os.path.exists(WORKLOGS_DIR):
            shutil.rmtree(WORKLOGS_DIR)
        if os.path.exists(CHANGELOG_DIR):
            shutil.rmtree(CHANGELOG_DIR)

        # Tạo lại các thư mục
        ensure_data_dirs()
        return True
    except Exception as e:
        print(f"Lỗi khi xóa dữ liệu local: {str(e)}")
        return False
