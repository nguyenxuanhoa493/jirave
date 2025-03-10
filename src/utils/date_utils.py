from datetime import datetime, timedelta
import pytz
from src.config.config import DEFAULT_TIMEZONE, DATE_FORMAT, DATETIME_FORMAT

def get_current_time(timezone=DEFAULT_TIMEZONE):
    """Get current time in the specified timezone"""
    tz = pytz.timezone(timezone)
    return datetime.now(tz)

def format_date(date_obj, format_str=DATE_FORMAT):
    """Format date object to string"""
    return date_obj.strftime(format_str)

def parse_date(date_str, format_str=DATE_FORMAT):
    """Parse date string to date object"""
    return datetime.strptime(date_str, format_str)

def get_week_start_end(date=None, timezone=DEFAULT_TIMEZONE):
    """Get start and end dates of the week containing the given date"""
    if date is None:
        date = get_current_time(timezone).date()
    elif isinstance(date, datetime):
        date = date.date()
    
    start_date = date - timedelta(days=date.weekday())  # Monday
    end_date = start_date + timedelta(days=6)  # Sunday
    return start_date, end_date

def get_last_week_start_end(timezone=DEFAULT_TIMEZONE):
    """Get start and end dates of last week"""
    current_date = get_current_time(timezone).date()
    start_date = current_date - timedelta(days=current_date.weekday() + 7)
    end_date = start_date + timedelta(days=6)
    return start_date, end_date

def get_month_start_end(date=None, timezone=DEFAULT_TIMEZONE):
    """Get start and end dates of the month containing the given date"""
    if date is None:
        date = get_current_time(timezone).date()
    elif isinstance(date, datetime):
        date = date.date()
    
    start_date = date.replace(day=1)
    
    # Find the last day of the month
    if date.month == 12:
        end_date = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
    
    return start_date, end_date

def get_date_range(start_date, end_date):
    """Generate a list of dates between start_date and end_date (inclusive)"""
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
        
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
        
    date_list = []
    current_date = start_date
    
    while current_date <= end_date:
        date_list.append(format_date(current_date))
        current_date += timedelta(days=1)
        
    return date_list 