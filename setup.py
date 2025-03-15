import subprocess
import os
import sys
from pathlib import Path


def install_requirements():
    """Cài đặt các gói thư viện cần thiết"""
    print("Đang cài đặt các gói thư viện cần thiết...")

    requirements = [
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "plotly>=5.13.0",
        "python-dotenv>=1.0.0",
        "requests>=2.28.0",
        "openpyxl>=3.0.10",
        "xlsxwriter>=3.0.3",
        "pymongo>=4.6.0",
        "dnspython>=2.4.0",
    ]

    for req in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
            print(f"Đã cài đặt {req}")
        except subprocess.CalledProcessError:
            print(f"Lỗi khi cài đặt {req}")


def create_env_file():
    """Tạo file .env nếu chưa tồn tại"""
    env_path = Path(".env")

    if not env_path.exists():
        print("Tạo file .env...")
        with open(env_path, "w") as f:
            f.write(
                """# Database settings
DB_HOST=<hostname>
DB_PASSWORD=<db_password>

# Jira settings
JIRA_URL=https://vieted.atlassian.net
JIRA_API_TOKEN=<your_jira_api_token>
JIRA_USER=<your_jira_username>

# Default project 
DEFAULT_PROJECT=CLD
"""
            )
        print("Đã tạo file .env. Vui lòng cập nhật thông tin kết nối MongoDB và Jira.")
    else:
        print("File .env đã tồn tại.")


def create_data_dirs():
    """Tạo các thư mục dữ liệu nếu chưa tồn tại"""
    print("Kiểm tra và tạo thư mục dữ liệu...")

    data_dirs = [
        "data",
        "data/sprints",
        "data/issues",
        "data/worklogs",
        "data/changelog",
    ]

    for dir_path in data_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Đã tạo thư mục {dir_path}")
        else:
            print(f"Thư mục {dir_path} đã tồn tại.")


def check_mongodb_connection():
    """Kiểm tra kết nối MongoDB"""
    print("Kiểm tra kết nối MongoDB...")

    try:
        import pymongo
        from dotenv import load_dotenv

        load_dotenv()

        db_host = os.environ.get("DB_HOST")
        db_password = os.environ.get("DB_PASSWORD")

        if (
            not db_host
            or not db_password
            or db_host == "<hostname>"
            or db_password == "<db_password>"
        ):
            print("Chưa cấu hình thông tin kết nối MongoDB trong file .env")
            return False

        mongo_uri = f"mongodb://nguyenxuanhoa493:{db_password}@{db_host}/?ssl=true&replicaSet=atlas-ahcjce-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

        # Kiểm tra kết nối
        client.admin.command("ping")
        print("Kết nối MongoDB thành công!")
        return True
    except ImportError:
        print("Thiếu thư viện pymongo hoặc python-dotenv.")
        return False
    except Exception as e:
        print(f"Lỗi kết nối MongoDB: {str(e)}")
        return False


def main():
    """Hàm chính"""
    print("=== THIẾT LẬP MÔI TRƯỜNG ===")

    # Cài đặt các gói thư viện
    install_requirements()

    # Tạo file .env
    create_env_file()

    # Tạo thư mục dữ liệu
    create_data_dirs()

    # Kiểm tra kết nối MongoDB
    check_mongodb_connection()

    print("\n=== THIẾT LẬP HOÀN TẤT ===")
    print("Chạy ứng dụng bằng lệnh: streamlit run Home.py")


if __name__ == "__main__":
    main()
