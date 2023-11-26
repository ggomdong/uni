from django.contrib import admin
from .models import Work

class WorkAdmin(admin.ModelAdmin):
    search_fields = ['id', 'username']

admin.site.register(Work, WorkAdmin)
