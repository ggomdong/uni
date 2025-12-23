import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from dateutil.relativedelta import relativedelta
from datetime import datetime

register = template.Library()


@register.filter
def sub(value, arg):
    try:
        return value - arg
    except:
        return None


@register.filter
def get_index(object_list, index):
    try:
        return object_list[index]
    except:
        return None


@register.filter
def get_day_index(object_list, index):
    try:
        return object_list["d"+index]
    except:
        return None


@register.filter
def get_next_index(object_list, index):
    try:
        return object_list["n"+index]
    except:
        return None


@register.filter
def split(value, key):
    try:
        return value.split(key)
    except:
        return None


@register.filter
def concat_date(value1, value2):
    try:
        return str(value1) + str(value2).zfill(2)
    except:
        return None


@register.filter
def to_int(value):
    try:
        return int(value)
    except:
        return None


@register.filter
def get_attr(obj, attr):
    try:
        return getattr(obj, attr)
    except:
        return None


@register.filter
def get_month(obj, delta):
    try:
        return (datetime.strptime(obj, '%Y%m') + relativedelta(months=delta)).strftime('%Y%m')
    except:
        return None


@register.filter
def get_day(obj, delta):
    try:
        return (datetime.strptime(obj, '%Y%m%d') + relativedelta(days=delta)).strftime('%Y%m%d')
    except:
        return None


@register.filter
def get_range(max_value, current):
    return range(max_value - current + 1)


@register.filter
def ss_to_hhmmss(value):
    try:
        s = int(value)
    except (TypeError, ValueError):
        return ""
    if s <= 0:
        return ""
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


@register.filter
def pretty_module_name(name: str):
    if not name:
        return ""

    s = escape(name)

    # 1) "(...)" 는 무조건 다음 줄로: "대진(전일)" -> "대진<br>(전일)"
    s = re.sub(r"\s*\(", "<br>(", s)

    # 2) 공백이 있으면 공백 기준으로 줄바꿈: "평일 의사" -> "평일<br>의사"
    s = s.replace(" ", "<br>")

    # 3) 예외/표준화가 필요한 용어는 매핑으로 강제 줄바꿈
    s = s.replace("경조휴가", "경조<br>휴가")
    s = s.replace("무급휴가", "무급<br>휴가")

    return mark_safe(s)