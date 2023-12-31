from django.contrib import admin
from .models import Work, Module

class WorkAdmin(admin.ModelAdmin):
    search_fields = ['id', 'username']

admin.site.register(Work, WorkAdmin)

class ModuleAdmin(admin.ModelAdmin):
    search_fields = ['cat', 'name']

admin.site.register(Module, ModuleAdmin)