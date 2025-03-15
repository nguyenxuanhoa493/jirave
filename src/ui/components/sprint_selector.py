import streamlit as st


def format_sprint_option(sprint):
    """Format hiển thị cho mỗi sprint

    Args:
        sprint (dict): Thông tin sprint

    Returns:
        str: Chuỗi hiển thị tên sprint
    """
    state = sprint.get("state", "unknown").upper()
    name = sprint.get("name", "Unnamed Sprint")
    return f"{name} ({state})"


def prepare_sprint_options(sprints):
    """Chuẩn bị danh sách sprint để hiển thị

    Args:
        sprints (list): Danh sách sprint từ API

    Returns:
        list: Danh sách options để chọn
    """
    sprint_options = []
    for sprint in sprints:
        sprint_options.append(
            {
                "display": format_sprint_option(sprint),
                "id": sprint.get("id"),
                "board_id": sprint.get("originBoardId"),
                "data": sprint,
            }
        )

    # Sắp xếp sprint: Active trước, sau đó đến Future, rồi đến các sprint còn lại
    sprint_options.sort(
        key=lambda x: (
            (
                0
                if x["data"].get("state") == "active"
                else (1 if x["data"].get("state") == "future" else 2)
            ),
            x["data"].get("name", ""),
        )
    )

    return sprint_options


def select_sprint(sprints, key="sprint_selector"):
    """Hiển thị component chọn sprint

    Args:
        sprints (list): Danh sách sprint từ API
        key (str): Key cho component

    Returns:
        dict: Sprint được chọn
    """
    # Chuẩn bị options
    sprint_options = prepare_sprint_options(sprints)

    if not sprint_options:
        st.warning("Không có sprint nào. Vui lòng đồng bộ dữ liệu trước.")
        return None

    # Hiển thị selectbox
    selected_sprint_idx = st.selectbox(
        "Chọn Sprint",
        options=range(len(sprint_options)),
        format_func=lambda i: sprint_options[i]["display"],
        key=key,
    )

    selected_sprint = sprint_options[selected_sprint_idx]

    # Hiển thị thông tin cơ bản của sprint
    st.write(f"**Sprint ID:** {selected_sprint['id']}")
    st.write(f"**Tên:** {selected_sprint['data'].get('name', '')}")
    st.write(f"**Trạng thái:** {selected_sprint['data'].get('state', '').upper()}")

    return selected_sprint
