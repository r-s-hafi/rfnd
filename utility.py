import matplotlib.colors as mcolors 
import random
import uuid

def handle_cookie(session_token: str = None, user_sessions: dict = None) -> str:

    #checks if there is no session token or if the session token has not been assigned to a user yet
    if not session_token or session_token not in user_sessions:
        session_token = str(uuid.uuid4())
    
    return session_token


def detect_time_frame(time_frame: str) -> float:

    #parse time frame string for processing
    time_frame_chars = time_frame.split()
    print(time_frame_chars)

    #check that there are only two character sets, the first is numeric, and the second is a time-based string
    if len(time_frame_chars) != 2 or time_frame_chars[0].isalpha() or not time_frame_chars[1].isalpha():
        print("please enter a valid time frame")
        return None, None

    else:
        num = float(time_frame_chars[0])
        time = time_frame_chars[1]
        print(num, time)

    #check for the time fram string and return the total time in minutes
    #check for years
    possible_years = ["year", "years", "yr", "y", "yrs"]
    if time in possible_years:
        total_time = num * 365 * 24 * 60
        return total_time
    
    #check for months
    possible_months = ["month", "months", "mo", "m", "mos"]
    if time in possible_months:
        total_time = num * 30 * 24 * 60
        return total_time
    
    #check for weeks
    possible_weeks = ["week", "weeks", "wk", "w", "wks"]
    if time in possible_weeks:
        total_time = num * 7 * 24 * 60
        return total_time
    
    #check for days
    possible_days = ["day", "days", "d", "day"]
    if time in possible_days:
        total_time = num * 24 * 60
        return total_time
    
    #check for hours
    possible_hours = ["hour", "hours", "hr", "h", "hrs"]
    if time in possible_hours:
        total_time = num * 60
        return total_time
    
    #check for minutes
    possible_minutes = ["minute", "minutes", "min", "m", "mins"]
    if time in possible_minutes:
        total_time = num
        return total_time
    
    #if the program makes it to this point without returning a tuple, the time frame is invalid
    print("please enter a valid time frame")
    return None, None



    
    
        
