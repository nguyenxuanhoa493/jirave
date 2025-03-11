import os
import sys
import streamlit as st

# Chạy ứng dụng qua app.py để có sidebar và các tab
if __name__ == "__main__":
    # Xác định đường dẫn đến file app.py
    file_path = os.path.join(os.path.dirname(__file__), "app.py")

    # Chạy Streamlit với app.py để có sidebar với các tab
    os.system(f"streamlit run {file_path}")
