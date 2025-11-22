"""
Management command to set up GitHub OAuth configuration.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Configure GitHub OAuth application from environment variables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=str,
            help='GitHub OAuth App Client ID (defaults to GITHUB_CLIENT_ID env var)',
        )
        parser.add_argument(
            '--client-secret',
            type=str,
            help='GitHub OAuth App Client Secret (defaults to GITHUB_CLIENT_SECRET env var)',
        )
        parser.add_argument(
            '--site-domain',
            type=str,
            default='localhost:8000',
            help='Site domain (default: localhost:8000)',
        )

    def handle(self, *args, **options):
        # Get credentials from args or environment
        client_id = options.get('client_id') or os.environ.get('GITHUB_CLIENT_ID', '')
        client_secret = options.get('client_secret') or os.environ.get('GITHUB_CLIENT_SECRET', '')
        site_domain = options.get('site_domain')

        if not client_id or not client_secret:
            self.stdout.write(
                self.style.ERROR(
                    'GitHub OAuth credentials not provided. Please set GITHUB_CLIENT_ID '
                    'and GITHUB_CLIENT_SECRET environment variables or use --client-id '
                    'and --client-secret options.'
                )
            )
            self.stdout.write('')
            self.stdout.write('To create a GitHub OAuth App:')
            self.stdout.write('1. Go to https://github.com/settings/developers')
            self.stdout.write('2. Click "New OAuth App"')
            self.stdout.write('3. Set Homepage URL to: http://localhost:8000/')
            self.stdout.write('4. Set Authorization callback URL to: http://localhost:8000/accounts/github/login/callback/')
            self.stdout.write('5. Copy the Client ID and generate a Client Secret')
            self.stdout.write('')
            self.stdout.write('Then run:')
            self.stdout.write('  export GITHUB_CLIENT_ID="your_client_id"')
            self.stdout.write('  export GITHUB_CLIENT_SECRET="your_client_secret"')
            self.stdout.write('  python manage.py setup_github_oauth')
            return

        # Update or create site
        site, created = Site.objects.get_or_create(pk=1)
        site.domain = site_domain
        site.name = 'NoHands'
        site.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created site: {site.domain}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated site: {site.domain}'))

        # Create or update GitHub social app
        social_app, created = SocialApp.objects.get_or_create(
            provider='github',
            defaults={
                'name': 'GitHub',
                'client_id': client_id,
                'secret': client_secret,
            }
        )

        if not created:
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()

        # Associate with site
        if site not in social_app.sites.all():
            social_app.sites.add(site)

        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ GitHub OAuth app created successfully!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ GitHub OAuth app updated successfully!')
            )

        self.stdout.write('')
        self.stdout.write('Configuration:')
        self.stdout.write(f'  Site: {site.domain}')
        self.stdout.write(f'  Provider: GitHub')
        self.stdout.write(f'  Client ID: {client_id[:8]}...')
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                'GitHub OAuth is now configured! Users can connect via /accounts/github/login/'
            )
        )
