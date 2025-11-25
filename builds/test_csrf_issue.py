"""
Test driven development pour résoudre le problème CSRF du proxy.

Ce test reproduit exactement le scénario utilisateur:
1. Utilisateur authentifié à NoHands
2. Accède à /builds/8/fwd/login/ (GET)
3. Soumet le formulaire de login (POST)
4. Devrait fonctionner sans erreur 403 CSRF

Actuellement, le test devrait ÉCHOUER avec une erreur 403.
Une fois le problème résolu, le test devrait PASSER.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from builds.models import Build
from projects.models import GitRepository, Branch, Commit
from unittest.mock import patch, MagicMock
import requests

User = get_user_model()


class CSRFProxyTestCase(TestCase):
    """Test le flux complet CSRF à travers le proxy."""
    
    def setUp(self):
        """Setup test data."""
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Créer une structure complète: repo -> branch -> commit -> build
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
            author='Test Author',
            author_email='test@example.com',
            committed_at='2024-01-01T00:00:00Z'
        )
        
        # Créer un build avec un conteneur "running"
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            dockerfile_content='FROM python:3.11',
            container_status='running',
            host_port=8005  # Port fictif pour les tests
        )
        
        # Client Django authentifié
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    @patch('builds.views.requests.get')
    @patch('builds.views.requests.post')
    def test_csrf_flow_through_proxy(self, mock_post, mock_get):
        """
        Test le flux complet:
        1. GET récupère une page avec token CSRF
        2. POST soumet le formulaire avec ce token
        3. Doit réussir sans 403
        """
        # Mock de la réponse GET du conteneur
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            'content-type': 'text/html; charset=utf-8',
        }
        
        # HTML avec un formulaire contenant un token CSRF
        csrf_token = 'fake-csrf-token-123456789'
        html_content = f'''
        <html>
        <body>
            <form method="post" action="/login/">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                <input type="text" name="username">
                <input type="password" name="password">
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        '''
        mock_get_response.content = html_content.encode('utf-8')
        
        # Mock du cookie CSRF du conteneur
        from http.cookiejar import Cookie
        mock_cookie = Cookie(
            version=0,
            name='csrftoken',
            value=csrf_token,
            port=None,
            port_specified=False,
            domain='127.0.0.1',
            domain_specified=True,
            domain_initial_dot=False,
            path='/',
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={'HttpOnly': None},
            rfc2109=False
        )
        
        mock_get_response.cookies = requests.cookies.RequestsCookieJar()
        mock_get_response.cookies.set_cookie(mock_cookie)
        mock_get.return_value = mock_get_response
        
        # 1. GET de la page de login
        print("\n=== ÉTAPE 1: GET /builds/{}/fwd/login/ ===".format(self.build.id))
        response = self.client.get(f'/builds/{self.build.id}/fwd/login/')
        
        print(f"Status code: {response.status_code}")
        print(f"Cookies set: {list(response.cookies.keys())}")
        
        # Vérifier que le GET réussit
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le cookie csrftoken est défini avec le bon path
        self.assertIn('csrftoken', response.cookies)
        cookie = response.cookies['csrftoken']
        expected_path = f'/builds/{self.build.id}/fwd/'
        print(f"Cookie path: {cookie.get('path', 'NOT SET')}")
        print(f"Expected path: {expected_path}")
        
        # Le cookie devrait avoir le path correct
        self.assertEqual(cookie.get('path'), expected_path)
        
        # Vérifier que le HTML contient le token
        html = response.content.decode('utf-8')
        self.assertIn(csrf_token, html)
        print(f"CSRF token found in HTML: {csrf_token[:20]}...")
        
        # Mock de la réponse POST du conteneur (succès)
        mock_post_response = MagicMock()
        mock_post_response.status_code = 302  # Redirect après login réussi
        mock_post_response.headers = {
            'content-type': 'text/html; charset=utf-8',
            'location': '/dashboard/'
        }
        mock_post_response.content = b''
        mock_post_response.cookies = requests.cookies.RequestsCookieJar()
        mock_post.return_value = mock_post_response
        
        # 2. POST du formulaire
        print("\n=== ÉTAPE 2: POST /builds/{}/fwd/login/ ===".format(self.build.id))
        
        # Extraire le cookie CSRF de la réponse précédente
        csrftoken_cookie = response.cookies['csrftoken'].value
        print(f"Cookie CSRF à envoyer: {csrftoken_cookie[:20]}...")
        
        # Soumettre le formulaire avec le token
        post_data = {
            'csrfmiddlewaretoken': csrf_token,
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        # Le client Django devrait automatiquement envoyer le cookie
        response = self.client.post(
            f'/builds/{self.build.id}/fwd/login/',
            data=post_data,
            follow=False  # Ne pas suivre les redirections
        )
        
        print(f"POST Status code: {response.status_code}")
        
        # Le point crucial: on ne doit PAS avoir une erreur 403
        self.assertNotEqual(
            response.status_code, 
            403, 
            "CSRF verification failed! Got 403 Forbidden"
        )
        
        # On s'attend à un 302 (redirect) ou 200 selon l'application
        self.assertIn(
            response.status_code,
            [200, 302],
            f"Expected 200 or 302, got {response.status_code}"
        )
        
        # Vérifier que le mock POST a été appelé
        self.assertTrue(mock_post.called, "POST request was not forwarded to container")
        
        # Vérifier que les headers transmis au conteneur sont corrects
        call_args = mock_post.call_args
        headers_sent = call_args[1]['headers']
        
        print("\n=== Headers envoyés au conteneur ===")
        print(f"Host: {headers_sent.get('Host')}")
        print(f"Referer: {headers_sent.get('Referer')}")
        print(f"Cookie: {headers_sent.get('Cookie', 'None')}")
        
        # Le cookie csrftoken doit être envoyé au conteneur
        cookie_header = headers_sent.get('Cookie', '')
        self.assertIn('csrftoken', cookie_header, "CSRF cookie not forwarded to container")
        
        print("\n✅ Test complet: le flux CSRF fonctionne correctement")
    
    def test_build_8_specifically(self):
        """Test spécifique pour le build #8 mentionné par l'utilisateur."""
        # Mettre à jour le build pour avoir l'ID 8
        self.build.id = 8
        self.build.save()
        
        # Appeler le test principal
        self.test_csrf_flow_through_proxy()


if __name__ == '__main__':
    import sys
    from django.core.management import execute_from_command_line
    
    sys.argv = ['manage.py', 'test', 'builds.test_csrf_issue', '-v', '2']
    execute_from_command_line(sys.argv)
