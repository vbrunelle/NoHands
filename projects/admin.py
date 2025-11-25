from django.contrib import admin
from .models import GitRepository, Branch, Commit, AppConfiguration


@admin.register(AppConfiguration)
class AppConfigurationAdmin(admin.ModelAdmin):
    list_display = ['app_url', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        # Only allow one instance
        if AppConfiguration.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False


@admin.register(GitRepository)
class GitRepositoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'default_branch', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'url', 'description']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'repository', 'commit_sha', 'last_updated']
    list_filter = ['repository', 'last_updated']
    search_fields = ['name', 'commit_sha']


@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ['sha', 'repository', 'branch', 'author', 'committed_at']
    list_filter = ['repository', 'committed_at']
    search_fields = ['sha', 'message', 'author']
