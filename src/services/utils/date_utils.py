from datetime import datetime


def format_date(date_str):
    """Định dạng chuỗi ngày ISO thành định dạng dễ đọc hơn

    Args:
        date_str (str): Chuỗi ngày dạng ISO

    Returns:
        str: Chuỗi ngày đã định dạng
    """
    if not date_str:
        return ""

    try:
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return date_obj.strftime("%d/%m/%Y %H:%M")
    except:
        return date_str
