from django import template
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