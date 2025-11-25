"""
Test TDD pour reproduire le problème CSRF lié au proxy des conteneurs.

Hypothèse: Le problème vient de la confusion entre:
1. Les cookies de NoHands (domaine principal)
2. Les cookies des applications dans les conteneurs (via proxy /builds/X/fwd/)

Quand l'utilisateur remplit un formulaire via le proxy, le cookie CSRF
pourrait être envoyé avec le mauvais domain/path, causant une erreur 403.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from builds.models import Build
from projects.models import GitRepository, Commit, Branch
from datetime import datetime, timezone
from unittest.mock import patch, Mock
import re

User = get_user_model()


class CSRFProxyDomainConflictTest(TestCase):
    """Test le problème CSRF causé par le proxy vers les conteneurs."""
    
    def setUp(self):
        """Setup avec un build et un conteneur en cours."""
        # GitHub OAuth
        self.site = Site.objects.get_or_create(
            id=1,
            defaults={'domain': 'testserver', 'name': 'Test Site'}
        )[0]
        
        self.github_app = SocialApp.objects.create(
            provider='github',
            name='GitHub Test',
            client_id='test-client-id',
            secret='test-secret'
        )
        self.github_app.sites.add(self.site)
        
        # Utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Repository, branch, commit, build
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            user=self.user
        )
        
        self.branch = Branch.objects.create(
            repository=self.repo,
            name='main',
            commit_sha='abc123'
        )
        
        self.commit = Commit.objects.create(
            repository=self.repo,
            branch=self.branch,
            sha='abc123',
            message='Test commit',
            author='Test',
            author_email='test@example.com',
            committed_at=datetime.now(timezone.utc)
        )
        
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            container_status='running',
            host_port=8005,
            status='success'
        )
    
    @patch('builds.views.requests.get')
    @patch('builds.views.requests.post')
    def test_csrf_fails_when_posting_from_proxied_container(self, mock_post, mock_get):
        """
        Test que le POST via proxy fonctionne maintenant avec @csrf_exempt.
        
        Scénario:
        1. Utilisateur connecté à NoHands
        2. Accède à une page Django dans un conteneur via /builds/X/fwd/
        3. La page contient un formulaire avec CSRF token
        4. L'utilisateur soumet le formulaire
        5. SOLUTION: @csrf_exempt permet au POST de passer
        
        AVANT @csrf_exempt: ❌ FAIL (403)
        APRÈS @csrf_exempt: ✅ PASS (le POST est transmis au conteneur)
        """
        print("\n" + "="*70)
        print(" TEST: POST via proxy fonctionne avec @csrf_exempt ")
        print("="*70)
        
        client = Client(enforce_csrf_checks=True)
        client.login(username='testuser', password='testpass123')
        
        # ÉTAPE 1: GET d'une page via le proxy
        print(f"\n[1] GET /builds/{self.build.id}/fwd/login/")
        print("    (Page Django dans le conteneur)")
        
        # Mock de la réponse du conteneur avec un formulaire Django
        csrf_token_from_container = 'CONTAINER_CSRF_TOKEN_123'
        html_from_container = f'''
        <html>
        <form method="post" action="/login/">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token_from_container}">
            <input type="text" name="username">
            <button type="submit">Login</button>
        </form>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.content = html_from_container.encode('utf-8')
        mock_response.cookies = []
        mock_response.iter_content = lambda chunk_size: [mock_response.content]
        mock_get.return_value = mock_response
        
        response = client.get(f'/builds/{self.build.id}/fwd/login/')
        
        print(f"    Status: {response.status_code}")
        self.assertEqual(response.status_code, 200)
        
        # Extraire le token du conteneur dans le HTML
        content = response.content.decode('utf-8')
        match = re.search(r'value="([^"]*CONTAINER_CSRF_TOKEN[^"]*)"', content)
        self.assertIsNotNone(match)
        container_token = match.group(1)
        print(f"    Token du conteneur extrait: {container_token[:20]}...")
        
        # ÉTAPE 2: POST du formulaire via le proxy
        print(f"\n[2] POST /builds/{self.build.id}/fwd/login/")
        print("    L'utilisateur soumet le formulaire du conteneur")
        
        # Mock de la réponse POST du conteneur (succès)
        mock_post_response = Mock()
        mock_post_response.status_code = 302  # Redirect après login réussi
        mock_post_response.headers = {
            'content-type': 'text/html',
            'location': '/dashboard/'
        }
        mock_post_response.content = b''
        mock_post_response.cookies = []
        mock_post_response.iter_content = lambda chunk_size: [mock_post_response.content]
        mock_post.return_value = mock_post_response
        
        # POST avec le token du conteneur
        post_data = {
            'csrfmiddlewaretoken': container_token,
            'username': 'testuser',
        }
        
        response = client.post(
            f'/builds/{self.build.id}/fwd/login/',
            data=post_data
        )
        
        print(f"    Status: {response.status_code}")
        
        # VÉRIFICATION: Avec @csrf_exempt, on ne devrait PAS avoir de 403
        if response.status_code == 403:
            print("\n" + "!"*70)
            print(" ❌ ÉCHEC: Erreur 403 encore présente!")
            print(" @csrf_exempt n'a pas résolu le problème")
            print("!"*70)
            self.fail("@csrf_exempt n'a pas résolu le problème - erreur 403 encore présente")
        
        self.assertNotEqual(response.status_code, 403)
        print("\n" + "="*70)
        print(" ✅ SUCCÈS: Pas d'erreur 403!")
        print(" ✅ @csrf_exempt permet au POST de passer au conteneur!")
        print(" ✅ Le problème est RÉSOLU!")
        print("="*70)
    
    def test_csrf_cookie_path_conflict(self):
        """
        Test si le problème vient du path des cookies.
        
        Le cookie CSRF de NoHands a peut-être un path='/' qui interfère
        avec les requêtes vers /builds/X/fwd/
        """
        print("\n" + "="*70)
        print(" TEST: Vérification du path des cookies CSRF ")
        print("="*70)
        
        client = Client(enforce_csrf_checks=True)
        
        # GET d'une page NoHands normale
        print("\n[1] GET /accounts/github/login/ (NoHands)")
        response = client.get('/accounts/github/login/')
        
        if 'nohands_csrftoken' in response.cookies:
            cookie = response.cookies['nohands_csrftoken']
            path = cookie.get('path', '/')
            print(f"    Cookie NoHands CSRF path: {path}")
            
            if path == '/':
                print("    ⚠ Path='/' signifie que ce cookie sera envoyé PARTOUT")
                print("    Y compris vers /builds/X/fwd/ (le proxy!)")
                print("    Cela peut causer des conflits!")
        
        print("="*70)
