from django import template
from dateutil.relativedelta import relativedelta
from datetime import datetime

register = template.Library()


@register.filter
def sub(value, arg):
    return value - arg


@register.filter
def get_index(object_list, index):
    return object_list[index]


@register.filter
def get_day_index(object_list, index):
    return object_list["d"+index]


@register.filter
def get_next_index(object_list, index):
    return object_list["n"+index]


@register.filter
def concat_date(value1, value2):
    return str(value1) + str(value2).zfill(2)


@register.filter
def to_int(value):
    return int(value)


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)


@register.filter
def get_month(obj, delta):
    return (datetime.strptime(obj, '%Y%m') + relativedelta(months=delta)).strftime('%Y%m')
