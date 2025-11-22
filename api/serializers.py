from rest_framework import serializers
from projects.models import GitRepository, Branch, Commit
from builds.models import Build


class GitRepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GitRepository
        fields = ['id', 'name', 'url', 'description', 'default_branch', 'is_active', 'created_at']


class BranchSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    
    class Meta:
        model = Branch
        fields = ['id', 'repository_name', 'name', 'commit_sha', 'last_updated']


class CommitSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Commit
        fields = ['id', 'repository_name', 'branch_name', 'sha', 'message', 'author', 'author_email', 'committed_at']


class BuildSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    commit_sha = serializers.CharField(source='commit.sha', read_only=True)
    
    class Meta:
        model = Build
        fields = [
            'id', 'repository_name', 'commit_sha', 'branch_name', 'status',
            'image_tag', 'logs', 'error_message', 'created_at', 'started_at',
            'completed_at', 'push_to_registry', 'duration'
        ]
        read_only_fields = ['status', 'logs', 'error_message', 'image_tag', 'started_at', 'completed_at']


class BuildCreateSerializer(serializers.Serializer):
    repository_id = serializers.IntegerField()
    commit_id = serializers.IntegerField()
    push_to_registry = serializers.BooleanField(default=False)
    deploy_after_build = serializers.BooleanField(default=False)
