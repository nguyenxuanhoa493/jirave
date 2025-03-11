import os
import sys
import streamlit as st

# Chạy trang gốc Home.py
if __name__ == "__main__":
    # Xác định đường dẫn đến file Home.py
    file_path = os.path.join(os.path.dirname(__file__), "Home.py")

    # Chạy Streamlit với Home.py
    os.system(f"streamlit run {file_path}")
