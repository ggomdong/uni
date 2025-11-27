from django.contrib import admin
from .models import User, Branch

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "emp_name", "branch")
    list_filter = ("branch",)
    search_fields = ("username", "emp_name", "email", "dept", "position")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "sort_order", "is_active", "reg_date", "mod_date")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "code")
    readonly_fields = ("reg_date", "mod_date")