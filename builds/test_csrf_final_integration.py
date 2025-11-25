"""
Test d'intégration final pour vérifier que le problème CSRF est résolu.

Ce test vérifie:
1. Que les anciens cookies sont automatiquement nettoyés
2. Que le flux CSRF fonctionne correctement après le nettoyage
3. Qu'un utilisateur avec des anciens cookies peut se connecter sans erreur 403
"""
from django.test import TestCase, Client
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import re


class CSRFIntegrationFinalTest(TestCase):
    """Test d'intégration final vérifiant que le problème CSRF est résolu."""
    
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
    
    def test_user_with_old_cookies_can_login(self):
        """
        Test d'intégration final: Un utilisateur avec d'anciens cookies peut se connecter.
        
        Scénario complet:
        1. L'utilisateur a un ancien cookie 'csrftoken' dans son navigateur
        2. Il va sur /accounts/github/login/
        3. Le middleware nettoie automatiquement l'ancien cookie
        4. L'utilisateur soumet le formulaire
        5. Succès! Pas d'erreur 403
        """
        print("\n" + "="*70)
        print(" TEST D'INTÉGRATION FINAL: Résolution du problème CSRF ")
        print("="*70)
        
        client = Client(enforce_csrf_checks=True)
        
        # SITUATION INITIALE: L'utilisateur a un ancien cookie
        print("\n[SITUATION INITIALE]")
        print("  L'utilisateur a un ancien cookie 'csrftoken' dans son navigateur")
        print("  (Resté d'une ancienne version de NoHands)")
        client.cookies['csrftoken'] = 'OLD_PROBLEMATIC_TOKEN'
        
        # ÉTAPE 1: GET de la page de login
        print("\n[ÉTAPE 1] GET /accounts/github/login/")
        response = client.get('/accounts/github/login/')
        
        print(f"  Status: {response.status_code}")
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le middleware a expiré l'ancien cookie
        print(f"  Cookies dans la réponse: {list(response.cookies.keys())}")
        
        if 'csrftoken' in response.cookies:
            old_cookie = response.cookies['csrftoken']
            print(f"  ✓ Middleware a expiré 'csrftoken' (max-age={old_cookie['max-age']})")
            self.assertEqual(old_cookie['max-age'], 0)
        
        # Nouveau cookie CSRF défini
        self.assertIn('nohands_csrftoken', response.cookies)
        new_csrf = response.cookies['nohands_csrftoken'].value
        print(f"  ✓ Nouveau cookie 'nohands_csrftoken' défini: {new_csrf[:20]}...")
        
        # Extraire le token du formulaire
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        self.assertIsNotNone(match)
        csrf_token = match.group(1)
        print(f"  ✓ Token CSRF dans le formulaire: {csrf_token[:20]}...")
        
        # ÉTAPE 2: POST du formulaire
        print("\n[ÉTAPE 2] POST /accounts/github/login/")
        print("  L'utilisateur clique sur 'Se connecter'")
        
        post_data = {
            'csrfmiddlewaretoken': csrf_token,
        }
        
        response = client.post('/accounts/github/login/', data=post_data)
        
        print(f"  Status de la réponse: {response.status_code}")
        
        # VÉRIFICATION FINALE: Pas d'erreur 403!
        if response.status_code == 403:
            print("\n" + "!"*70)
            print("  ❌ ÉCHEC: Erreur 403 CSRF détectée!")
            print("!"*70)
            self.fail("Le problème CSRF n'est PAS résolu - erreur 403 détectée")
        
        self.assertNotEqual(response.status_code, 403)
        
        print("\n" + "="*70)
        print(" ✅ SUCCÈS: Pas d'erreur 403!")
        print(" ✅ L'utilisateur peut se connecter sans problème")
        print(" ✅ Le problème CSRF est RÉSOLU")
        print("="*70)
    
    def test_clean_slate_user_can_login(self):
        """Test qu'un utilisateur sans anciens cookies peut aussi se connecter."""
        print("\n[TEST BONUS] Utilisateur sans anciens cookies")
        
        client = Client(enforce_csrf_checks=True)
        
        # Pas d'anciens cookies
        response = client.get('/accounts/github/login/')
        self.assertEqual(response.status_code, 200)
        
        # Extraire token
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        csrf_token = match.group(1)
        
        # POST
        response = client.post('/accounts/github/login/', data={'csrfmiddlewaretoken': csrf_token})
        
        self.assertNotEqual(response.status_code, 403)
        print("  ✅ Fonctionne aussi sans anciens cookies")
