from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta

week_list = ["월", "화", "수", "목", "금", "토", "일"]
day_of_the_week = {'mon': '월', 'tue': '화', 'wed': '수', 'thu': '목', 'fri': '금', 'sat': '토', 'sun': '일', }
categories = ['정규근무', '휴일근무', '유급휴무', '무급휴무', 'OFF']
times = ['-', '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00',
         '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
         '17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00',
         '21:30', '22:00', '22:30', '23:00', '23:30', ]
module_colors = {
        1: '#f0f0ec',
        2: '#f7e2e8',
        3: '#f5bfcc',
        4: '#aed6df',
        5: '#fea188',
        6: '#e2d9ca',
        7: '#bfcfdd',
        8: '#f5e97a',
        9: '#aed4d2',
        10: '#d8bfd8',
        11: '#ffffff',  # 휴일근무, 유급휴무, 무급휴무, OFF 색상
    }

STATUS_LABELS = {
    "WORKDAY": "정규근무",
    "HOLIDAY": "휴근",
    "NORMAL": "정상",
    "LATE": "지각",
    "EARLY": "조퇴",
    "OVERTIME": "연장",
    "ERROR": "오류",
    "PAY": "유급휴무",
    "NOPAY": "무급휴무",
    "OFF": "OFF",
    "NOSCHEDULE": "스케쥴없음",
}


def get_day_of_the_week(self):
    return {'day_of_the_week': day_of_the_week}


def get_categories(self):
    return {'categories': categories}


def get_times(self):
    return {'times': times}


def get_module_colors(self):
    return {'module_colors': module_colors}


def get_day_list(stand_ym, last_day=None):
    #day_of_the_week = list(day_of_the_week.values())  # ['월', '화', '수', '목', '금', '토', '일']
    #now = datetime.today()  # 오늘 : 2024-01-24 23:08:13.697803
    year = int(stand_ym[0:4])  # 연도 : 2024
    month = int(stand_ym[4:6])  # 월 : 1

    if last_day is None:
        last_day = calendar.monthrange(year, month)[1]  # stand_ym 말일 : 31

    first_weekday = datetime(year, month, 1).weekday()  # stand_ym 1일 요일값 : 0
    day_list = {}
    for i in range(last_day):
        # 날짜, 요일 쌍을 dictionary에 저장
        day_list[str(i + 1)] = list(day_of_the_week.values())[first_weekday]
        # 6(일)이면 0(월) 으로 변경, 아니면 1을 더함
        if first_weekday == 6:
            first_weekday = 0
        else:
            first_weekday += 1

    return day_list


def get_days(day):
    return datetime(int(day[0:4]), int(day[4:6]), int(day[6:8])).weekday()


def get_days_korean(day):
    return week_list[datetime(int(day[0:4]), int(day[4:6]), int(day[6:8])).weekday()]


def get_month(obj, delta):
    try:
        return (datetime.strptime(obj, '%Y%m') + relativedelta(months=delta)).strftime('%Y%m')
    except:
        return None


def get_last_day(stand_ym):
    year = int(stand_ym[0:4])  # 연도 : 2024
    month = int(stand_ym[4:6])  # 월 : 1
    return calendar.monthrange(year, month)[1]  # stand_ym 말일 : 31
