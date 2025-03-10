import os
import subprocess
import sys


def run_streamlit():
    """Run the Streamlit application"""
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Change to the script directory
        os.chdir(script_dir)

        # Run the Streamlit app
        cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8503"]
        subprocess.run(cmd)
    except Exception as e:
        print(f"Error running Streamlit app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_streamlit()
