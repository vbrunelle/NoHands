from django.contrib import admin
from .models import Build


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = ['id', 'repository', 'branch_name', 'status', 'created_at', 'duration']
    list_filter = ['status', 'repository', 'created_at']
    search_fields = ['commit__sha', 'branch_name', 'image_tag']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'duration']

