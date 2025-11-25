"""
Test TDD pour reproduire l'erreur 403 CSRF comme un vrai navigateur.

Ce test utilise requests au lieu du Django test client pour simuler
un vrai navigateur et reproduire l'erreur 403 que l'utilisateur voit.
"""
from django.test import TestCase, LiveServerTestCase
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import requests
import re


class RealBrowserLoginCSRFTest(LiveServerTestCase):
    """Test le flux CSRF comme un vrai navigateur avec requests."""
    
    @classmethod
    def setUpClass(cls):
        """Setup pour le serveur de test."""
        super().setUpClass()
        
        # Créer un site pour allauth
        site = Site.objects.get_or_create(
            id=1,
            defaults={'domain': 'testserver', 'name': 'Test Site'}
        )[0]
        
        # Créer une app GitHub pour allauth
        github_app = SocialApp.objects.create(
            provider='github',
            name='GitHub Test',
            client_id='test-client-id',
            secret='test-secret'
        )
        github_app.sites.add(site)
    
    def test_login_csrf_like_real_browser(self):
        """
        Simule exactement ce qu'un navigateur fait:
        1. GET /accounts/github/login/
        2. Extraire le cookie et le token du HTML
        3. POST avec ces valeurs
        4. Devrait réussir, pas 403
        """
        print("\n" + "="*60)
        print("TEST: Flux CSRF comme un VRAI navigateur")
        print("="*60)
        
        # Créer une session requests (comme un navigateur)
        session = requests.Session()
        
        # ÉTAPE 1: GET pour obtenir le formulaire
        url = f'{self.live_server_url}/accounts/github/login/'
        print(f"\n[1] GET {url}")
        
        response = session.get(url)
        print(f"    Status: {response.status_code}")
        print(f"    Cookies reçus: {list(response.cookies.keys())}")
        
        # Afficher tous les cookies avec leur nom exact
        for cookie_name, cookie_value in response.cookies.items():
            print(f"    - {cookie_name}: {cookie_value[:20]}...")
        
        self.assertEqual(response.status_code, 200)
        
        # Extraire le token CSRF du HTML
        html = response.text
        csrf_match = re.search(
            r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']',
            html
        )
        
        self.assertIsNotNone(csrf_match, "Token CSRF introuvable dans le HTML!")
        csrf_token = csrf_match.group(1)
        print(f"    Token CSRF extrait: {csrf_token[:20]}...")
        
        # Vérifier quel cookie CSRF est défini
        csrf_cookie_name = None
        csrf_cookie_value = None
        
        # Chercher le cookie avec 'csrf' dans le nom
        for cookie_name in response.cookies.keys():
            if 'csrf' in cookie_name.lower():
                csrf_cookie_name = cookie_name
                csrf_cookie_value = response.cookies[cookie_name]
                print(f"    Cookie CSRF trouvé: {cookie_name} = {csrf_cookie_value[:20]}...")
                break
        
        self.assertIsNotNone(csrf_cookie_name, "Aucun cookie CSRF trouvé!")
        
        # ÉTAPE 2: POST comme le ferait un navigateur
        print(f"\n[2] POST {url}")
        print(f"    Envoi du token: {csrf_token[:20]}...")
        print(f"    Cookie {csrf_cookie_name}: {csrf_cookie_value[:20]}...")
        
        post_data = {
            'csrfmiddlewaretoken': csrf_token,
        }
        
        # Le POST (session garde automatiquement les cookies)
        response = session.post(url, data=post_data, allow_redirects=False)
        
        print(f"    Response status: {response.status_code}")
        
        # VÉRIFICATION CRITIQUE: reproduire l'erreur 403
        if response.status_code == 403:
            print("\n" + "!"*60)
            print("❌ ERREUR 403 REPRODUITE!")
            print("!"*60)
            print(f"Content preview: {response.text[:500]}")
            
            # Afficher les détails pour le debugging
            print("\n--- DEBUGGING INFO ---")
            print(f"Cookie envoyé: {csrf_cookie_name} = {csrf_cookie_value[:20]}...")
            print(f"Token envoyé: csrfmiddlewaretoken = {csrf_token[:20]}...")
            print(f"Token == Cookie? {csrf_token == csrf_cookie_value}")
            
            # Ce fail est ATTENDU - on reproduit le problème
            self.fail(
                f"ERREUR 403 CSRF reproduite!\n"
                f"Cookie name: {csrf_cookie_name}\n"
                f"Token != Cookie: {csrf_token != csrf_cookie_value}"
            )
        
        # Si on arrive ici, le test PASSE (pas de 403)
        self.assertNotEqual(response.status_code, 403)
        print(f"    ✅ Pas d'erreur 403!")
        print("="*60)
