import os
import sys
import streamlit as st
from streamlit import runtime


# Hàm chính để khởi chạy ứng dụng
def main():
    """
    Hàm chính để khởi chạy ứng dụng Streamlit và chuyển hướng đến trang chính (Home.py)
    """
    # Xác định đường dẫn đến file Home.py
    file_path = os.path.join(os.path.dirname(__file__), "Home.py")

    # Kiểm tra xem có đang chạy trong môi trường Streamlit không
    if runtime.exists():
        # Nếu đang chạy trong Streamlit, chuyển hướng đến trang Home.py
        st.switch_page(file_path)
    else:
        # Nếu chạy từ command line, sử dụng sys.argv để chạy Home.py
        os.system(f"streamlit run {file_path}")


# Chạy hàm main khi script được thực thi trực tiếp
if __name__ == "__main__":
    main()
