import os
import sys
import streamlit as st
from streamlit import runtime


# Hàm chính để khởi chạy ứng dụng
def main():
    """
    Hàm chính để khởi chạy ứng dụng Streamlit và chuyển hướng đến trang Worklog Report
    """
    # Xác định đường dẫn đến file Home.py để Streamlit khởi tạo cấu trúc đa trang
    home_path = os.path.join(os.path.dirname(__file__), "Home.py")

    # Xác định đường dẫn đến trang Worklog Report
    worklog_path = os.path.join(
        os.path.dirname(__file__), "pages", "01_Worklog_Report.py"
    )

    # Nếu đang chạy trong môi trường Streamlit, chạy Home trước để khởi tạo cấu trúc đa trang
    # sau đó mới chuyển hướng đến trang Worklog Report
    if runtime.exists():
        st.switch_page(worklog_path)
    else:
        # Nếu chạy từ command line, chạy Home.py để có cấu trúc đa trang
        os.system(f"streamlit run {home_path}")


# Chạy hàm main khi script được thực thi trực tiếp
if __name__ == "__main__":
    main()
