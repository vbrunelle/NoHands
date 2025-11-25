"""
Test TDD pour identifier le problème CSRF exactement.

Hypothèse: Le problème vient peut-être de la configuration CSRF_COOKIE_NAME
avec le préfixe 'nohands_'. Le middleware CSRF Django pourrait chercher 
'csrftoken' au lieu de 'nohands_csrftoken'.
"""
from django.test import TestCase, Client, override_settings
from django.contrib.sites.models import Site
from django.middleware.csrf import get_token
from allauth.socialaccount.models import SocialApp


class CSRFCookieNameTest(TestCase):
    """Test que le nom personnalisé du cookie CSRF fonctionne correctement."""
    
    def setUp(self):
        """Setup GitHub OAuth."""
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
    
    def test_csrf_cookie_name_is_nohands_csrftoken(self):
        """Vérifie que le cookie CSRF utilise bien le nom personnalisé."""
        from django.conf import settings
        
        print(f"\n[CONFIG] CSRF_COOKIE_NAME = '{settings.CSRF_COOKIE_NAME}'")
        
        self.assertEqual(
            settings.CSRF_COOKIE_NAME,
            'nohands_csrftoken',
            "Le nom du cookie CSRF devrait être 'nohands_csrftoken'"
        )
    
    def test_csrf_with_custom_cookie_name(self):
        """
        Test que le CSRF fonctionne avec le nom de cookie personnalisé.
        
        Ce test échoue si Django cherche 'csrftoken' au lieu de 'nohands_csrftoken'.
        """
        print("\n" + "="*60)
        print("TEST: CSRF avec nom de cookie personnalisé")
        print("="*60)
        
        client = Client(enforce_csrf_checks=True)
        
        # GET pour obtenir le token
        print("\n[1] GET /accounts/github/login/")
        response = client.get('/accounts/github/login/')
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le cookie utilise le bon nom
        print(f"    Cookies définis: {list(response.cookies.keys())}")
        
        self.assertIn('nohands_csrftoken', response.cookies)
        self.assertNotIn('csrftoken', response.cookies)
        
        csrf_cookie = response.cookies['nohands_csrftoken'].value
        print(f"    Cookie nohands_csrftoken: {csrf_cookie[:20]}...")
        
        # Extraire le token du HTML
        import re
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        
        self.assertIsNotNone(match, "Token CSRF introuvable dans le HTML")
        csrf_token = match.group(1)
        print(f"    Token dans form: {csrf_token[:20]}...")
        
        # POST avec le token
        print("\n[2] POST /accounts/github/login/")
        post_data = {
            'csrfmiddlewaretoken': csrf_token,
        }
        
        response = client.post('/accounts/github/login/', data=post_data)
        
        print(f"    Status: {response.status_code}")
        
        # SI on a une erreur 403, c'est que Django ne reconnaît pas 
        # le cookie nohands_csrftoken
        if response.status_code == 403:
            print("\n❌ ERREUR 403 - Django ne reconnaît pas nohands_csrftoken!")
            print("Le middleware CSRF cherche probablement 'csrftoken' au lieu de 'nohands_csrftoken'")
            self.fail("Erreur 403: Django ne reconnaît pas le cookie CSRF personnalisé")
        
        self.assertNotEqual(response.status_code, 403)
        print("    ✅ CSRF fonctionne avec le nom personnalisé")
        print("="*60)
    
    def test_csrf_header_name_in_settings(self):
        """Vérifie si CSRF_HEADER_NAME est configuré si nécessaire."""
        from django.conf import settings
        
        print(f"\n[CONFIG] Vérification des settings CSRF:")
        print(f"  CSRF_COOKIE_NAME: {getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken')}")
        print(f"  CSRF_HEADER_NAME: {getattr(settings, 'CSRF_HEADER_NAME', 'HTTP_X_CSRFTOKEN')}")
        print(f"  CSRF_USE_SESSIONS: {getattr(settings, 'CSRF_USE_SESSIONS', False)}")
        print(f"  CSRF_COOKIE_HTTPONLY: {getattr(settings, 'CSRF_COOKIE_HTTPONLY', False)}")
        print(f"  CSRF_COOKIE_SAMESITE: {getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')}")
        
        # Note: Si CSRF_COOKIE_HTTPONLY=True, JavaScript ne peut pas lire le cookie
        # Ce qui peut causer des problèmes avec certains frameworks frontend
