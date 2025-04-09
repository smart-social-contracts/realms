import ast
import time
from datetime import datetime

DAY = 1000 * 3600 * 24  # number of milliseconds in 1 day

time_offset = 0

def get_real_time():
    return int(time.time() * 1000) 


def set_system_time(timestamp):
    global time_offset
    time_offset = timestamp - get_real_time()

def get_system_time():
    return get_real_time() + time_offset

def timestamp_to_datetime(timestamp):
    dt_object = datetime.fromtimestamp(timestamp / 1000)
    return dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def timestamp_to_date(timestamp):
    dt_object = datetime.fromtimestamp(timestamp / 1000)
    return dt_object.strftime("%Y-%m-%d")

def datetime_to_timestamp(date_time):
    dt_object = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S.%f")
    return int(dt_object.timestamp() * 1000)

