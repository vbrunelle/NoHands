"""
Test TDD pour le problème CSRF sur la page de login de NoHands.

Scénario utilisateur:
1. Aller sur /accounts/github/login/
2. Entrer un nom d'utilisateur quelconque
3. Cliquer sur "Se connecter"
4. Actuellement: erreur 403 CSRF
5. Attendu: devrait fonctionner

Ce test devrait ÉCHOUER initialement, puis PASSER une fois le problème résolu.
"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

User = get_user_model()


class NoHandsLoginCSRFTest(TestCase):
    """Test le flux CSRF sur la page de login de NoHands elle-même."""
    
    def setUp(self):
        """Setup test client et GitHub OAuth."""
        # Créer un site pour allauth
        self.site = Site.objects.get_or_create(
            id=1,
            defaults={'domain': 'testserver', 'name': 'Test Site'}
        )[0]
        
        # Créer une app GitHub pour allauth
        self.github_app = SocialApp.objects.create(
            provider='github',
            name='GitHub Test',
            client_id='test-client-id',
            secret='test-secret'
        )
        self.github_app.sites.add(self.site)
        
        self.client = Client(enforce_csrf_checks=True)
    
    def test_login_page_csrf_flow(self):
        """
        Test le flux complet de login avec CSRF:
        1. GET /accounts/github/login/ pour obtenir le token
        2. POST avec le token CSRF
        3. Devrait réussir (ou rediriger), pas 403
        """
        print("\n" + "="*60)
        print("TEST: Flux CSRF sur la page de login NoHands")
        print("="*60)
        
        # ÉTAPE 1: GET pour obtenir le token CSRF
        print("\n[1] GET /accounts/github/login/")
        response = self.client.get('/accounts/github/login/', follow=True)
        
        print(f"    Status: {response.status_code}")
        print(f"    Cookies: {list(response.cookies.keys())}")
        
        # Si erreur 500, afficher les détails
        if response.status_code == 500:
            if hasattr(response, 'content'):
                print(f"    Error content: {response.content.decode('utf-8')[:500]}")
        
        # Vérifier que le GET réussit
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le cookie csrftoken est présent
        # Note: NoHands utilise le préfixe "nohands_" pour ses cookies
        self.assertIn('nohands_csrftoken', response.cookies)
        csrf_cookie = response.cookies['nohands_csrftoken'].value
        print(f"    CSRF cookie value: {csrf_cookie[:20]}...")
        
        # Extraire le token du contexte ou du HTML
        csrf_token_from_form = None
        if hasattr(response, 'context') and response.context:
            csrf_token = response.context.get('csrf_token')
            if csrf_token:
                csrf_token_from_form = str(csrf_token)
                print(f"    CSRF token from context: {csrf_token_from_form[:20]}...")
        
        # Si pas trouvé dans le contexte, extraire du HTML
        if not csrf_token_from_form:
            import re
            content = response.content.decode('utf-8')
            match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', content)
            if match:
                csrf_token_from_form = match.group(1)
                print(f"    CSRF token from HTML: {csrf_token_from_form[:20]}...")
        
        # ÉTAPE 2: POST avec le token CSRF
        print("\n[2] POST /accounts/github/login/")
        print(f"    Cookie nohands_csrftoken: {csrf_cookie[:20]}...")
        
        # Préparer les données du POST
        post_data = {
            'csrfmiddlewaretoken': csrf_token_from_form or csrf_cookie,
        }
        
        # Faire le POST en réutilisant le client (qui garde les cookies)
        response = self.client.post(
            '/accounts/github/login/',
            data=post_data,
            follow=False
        )
        
        print(f"    Response status: {response.status_code}")
        
        # VÉRIFICATION CRITIQUE: pas d'erreur 403
        if response.status_code == 403:
            print(f"    ❌ ERREUR 403 CSRF détectée!")
            print(f"    Content: {response.content.decode('utf-8')[:500]}")
            self.fail("Erreur 403 CSRF détectée! Le problème est reproduit.")
        
        # Le test passe si on n'a PAS d'erreur 403 CSRF
        # On peut avoir 302 (redirect), 200 (page d'erreur de login), etc.
        # mais PAS 403
        self.assertNotEqual(
            response.status_code, 
            403, 
            "Erreur 403 CSRF détectée! Le problème persiste."
        )
        
        print(f"    ✅ Pas d'erreur 403 - CSRF fonctionne!")
        print("="*60)
    
    def test_login_csrf_token_in_form(self):
        """Vérifie que le formulaire de login contient bien un token CSRF."""
        response = self.client.get('/accounts/github/login/')
        
        # Le HTML devrait contenir un champ csrfmiddlewaretoken
        content = response.content.decode('utf-8')
        self.assertIn('csrfmiddlewaretoken', content)
        print("✅ Token CSRF présent dans le formulaire de login")
    
    def test_login_csrf_cookie_set(self):
        """Vérifie que le cookie CSRF est bien défini sur la page de login."""
        response = self.client.get('/accounts/github/login/')
        
        self.assertIn('csrftoken', response.cookies)
        
        cookie = response.cookies['csrftoken']
        print(f"✅ Cookie CSRF défini: {cookie.value[:20]}...")
        print(f"   Path: {cookie.get('path', '/')}")
        print(f"   SameSite: {cookie.get('samesite', 'not set')}")
