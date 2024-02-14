from django import template

register = template.Library()


@register.filter
def sub(value, arg):
    return value - arg


@register.filter
def get_index(object_list, index):
    return object_list[index]


@register.filter
def concat_string(value1, value2):
    return str(value1) + str(value2)


@register.filter
def to_int(value):
    return int(value)


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)
