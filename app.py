import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from datetime import timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from src modules
from src.config.config import (
    APP_TITLE,
    APP_LAYOUT,
    SIDEBAR_STATE,
    DEFAULT_TIMEZONE,
    HEATMAP_COLORSCALE,
)
from src.utils.date_utils import (
    get_current_time,
    format_date,
    get_week_start_end,
    get_last_week_start_end,
)
from src.services.worklog_service import WorklogReport

# Set page configuration
st.set_page_config(
    page_title=APP_TITLE, layout=APP_LAYOUT, initial_sidebar_state=SIDEBAR_STATE
)


def main():
    st.title(APP_TITLE)

    # Set default time to morning in GMT+7
    today = get_current_time(DEFAULT_TIMEZONE).replace(
        hour=9, minute=0, second=0, microsecond=0
    )

    # Date selection in 3 columns
    col1, col2, col3 = st.columns(3)
    with col1:
        report_type = st.selectbox(
            "Select Report Period",
            ["Today", "Yesterday", "This Week", "Last Week", "Custom Range"],
        )

    # Handle different date selections
    if report_type == "Custom Range":
        with col2:
            start_date = st.date_input("Start Date")
        with col3:
            end_date = st.date_input("End Date")
    else:
        if report_type == "Today":
            start_date = end_date = today.date()
        elif report_type == "Yesterday":
            start_date = end_date = (today - timedelta(days=1)).date()
        elif report_type == "This Week":
            start_date, end_date = get_week_start_end(today)
        else:  # Last Week
            start_date, end_date = get_last_week_start_end()

    if st.button("Generate Report"):
        report = WorklogReport()
        data = report.get_project_worklogs(
            start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        )

        if data:
            # Add KPI metrics at the top
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Hours", f"{data['total_hours']:.2f}")
            with col2:
                avg_daily_hours = data["total_hours"] / len(data["daily_summary"])
                st.metric("Average Daily Hours", f"{avg_daily_hours:.2f}")
            with col3:
                total_tasks = len(data["by_issue"])
                st.metric("Total Tasks", total_tasks)
            with col4:
                total_users = len(data["by_user"])
                st.metric("Team Members", total_users)

            # Add charts
            col_left, col_right = st.columns(2)

            with col_left:
                # Daily Hours Trend
                dates = sorted(data["daily_summary"].keys())
                daily_totals = []
                for date in dates:
                    daily_total = sum(data["daily_summary"][date].values())
                    daily_totals.append(daily_total)

                fig_trend = go.Figure()
                fig_trend.add_trace(
                    go.Scatter(
                        x=dates,
                        y=daily_totals,
                        mode="lines+markers",
                        name="Daily Hours",
                    )
                )
                fig_trend.update_layout(
                    title="Daily Hours Trend",
                    xaxis_title="Date",
                    yaxis_title="Hours",
                    height=300,
                )
                st.plotly_chart(fig_trend, use_container_width=True)

            with col_right:
                # Task Distribution Chart (top 5)
                task_data = []
                for key, issue_info in data["by_issue"].items():
                    total_hours = sum(w["hours"] for w in issue_info["worklogs"])
                    task_data.append(
                        {
                            "Task": f"{key}: {issue_info['summary'][:30]}...",
                            "Hours": total_hours,
                        }
                    )

                df_tasks = pd.DataFrame(task_data)
                df_tasks = df_tasks.nlargest(5, "Hours")

                fig_tasks = px.bar(
                    df_tasks,
                    x="Hours",
                    y="Task",
                    orientation="h",
                    title="Top 5 Tasks by Hours",
                )
                fig_tasks.update_layout(height=300)
                st.plotly_chart(fig_tasks, use_container_width=True)

            # Daily Summary with heatmap
            st.subheader("📅 Daily Summary")
            dates = sorted(data["daily_summary"].keys())
            users = sorted(data["by_user"].keys())

            # Create daily_data for the table view
            daily_data = []
            for date in dates:
                row = {"Date": date}
                daily_total = 0
                for user in users:
                    hours = data["daily_summary"][date].get(user, 0)
                    row[user] = f"{hours:.2f}"
                    daily_total += hours
                row["Total"] = f"{daily_total:.2f}"
                daily_data.append(row)

            # Add total row if more than one day
            if len(dates) > 1:
                total_row = {"Date": "Total"}
                for user in users:
                    user_total = sum(float(day[user]) for day in daily_data)
                    total_row[user] = f"{user_total:.2f}"
                total_row["Total"] = f"{data['total_hours']:.2f}"
                daily_data.append(total_row)

            # Prepare data for heatmap
            heatmap_data = []
            text_data = []
            for date in dates:
                hours_row = []
                text_row = []
                for user in users:
                    hours = data["daily_summary"][date].get(user, 0)
                    hours_row.append(hours)
                    text_row.append(f"{hours:.2f}")
                heatmap_data.append(hours_row)
                text_data.append(text_row)

            # Create and display heatmap
            fig_heatmap = go.Figure(
                data=go.Heatmap(
                    z=heatmap_data,
                    x=users,
                    y=dates,
                    text=text_data,
                    texttemplate="%{text}",
                    textfont={"size": 14, "color": "black", "weight": "bold"},
                    showscale=True,
                    colorscale=HEATMAP_COLORSCALE,
                    hoverongaps=False,
                )
            )

            fig_heatmap.update_layout(
                title="Daily Hours by Team Member",
                xaxis_title="Team Member",
                yaxis_title="Date",
                height=max(300, len(dates) * 30),
                font=dict(size=14),
                title_font_size=16,
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

            # Display the detailed table
            st.dataframe(daily_data)

            # Create DataFrame and sort by "Time Log"
            data_total = {}
            for data_daily in daily_data:
                if "Total" in data_daily and "Date" in data_daily:
                    data_daily_copy = data_daily.copy()
                    del data_daily_copy["Total"]
                    del data_daily_copy["Date"]
                    for key, value in data_daily_copy.items():
                        data_total[key] = data_total.get(key, 0) + float(value)

            df = pd.DataFrame(
                {"DEV": data_total.keys(), "Time Log": data_total.values()}
            )
            # /2 time log if more than one day
            df["Time Log"] = (
                df["Time Log"] / 2 if len(daily_data) > 1 else df["Time Log"]
            )
            df = df.sort_values(by="Time Log", ascending=False)

            # Display the sorted bar chart
            st.bar_chart(
                df.set_index("DEV").sort_values(by="Time Log", ascending=False)
            )

            # Issue Summary with enhanced grouping and reordered columns
            st.subheader("📋 Hours by Issue")

            # Reorganize issue data by user and task
            user_task_data = {}
            for key, issue_info in data["by_issue"].items():
                for worklog in issue_info["worklogs"]:
                    user = worklog["author"]
                    hours = worklog["hours"]
                    if user not in user_task_data:
                        user_task_data[user] = []
                    user_task_data[user].append(
                        {
                            "Issue": key,
                            "Summary": issue_info["summary"],
                            "Hours": hours,
                            "Date": worklog["date"],
                        }
                    )

            # Create formatted table with headers
            issue_data = [["Date", "Issue Key", "Summary", "Hours"]]  # Headers

            for user, tasks in user_task_data.items():
                user_total = sum(task["Hours"] for task in tasks)
                # Add user group header
                issue_data.append(["-", f"👤 {user}", "", f"{user_total:.2f}"])
                # Add tasks for this user
                for task in sorted(tasks, key=lambda x: x["Date"]):
                    issue_data.append(
                        [
                            task["Date"],
                            task["Issue"],
                            task["Summary"],
                            f"{task['Hours']:.2f}",
                        ]
                    )

            st.table(issue_data)
        else:
            st.info("No data found for the selected period.")


if __name__ == "__main__":
    main()
