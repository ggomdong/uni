from django import template

register = template.Library()


@register.filter
def sub(value, arg):
    return value - arg


@register.filter
def get_index(object_list, index):
    return object_list[index]


@register.filter
def to_int(value):
    return int(value)


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)
