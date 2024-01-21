def get_day_of_the_week(self):
    day_of_the_week = {
        'mon': '월',
        'tue': '화',
        'wed': '수',
        'thu': '목',
        'fri': '금',
        'sat': '토',
        'sun': '일',
    }

    return {'day_of_the_week': day_of_the_week}


def get_categories(self):
    categories = ['정규근무', '휴일근무', '유급휴무', 'OFF']

    return {'categories': categories}


def get_times(self):
    times = ['-', '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00',
             '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
             '17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00',
             '21:30', '22:00', '22:30', '23:00', '23:30',]

    return {'times': times}


def get_module_colors(self):
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
        11: '#ffffff', # 휴일근무, 유급휴무, OFF 색상
    }

    return {'module_colors': module_colors}