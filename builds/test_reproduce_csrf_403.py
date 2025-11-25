"""
Test TDD pour REPRODUIRE et RÉSOUDRE l'erreur 403 CSRF.

CYCLE TDD COMPLET:
1. RED: Test échoue avec 403 (problème reproduit)
2. GREEN: Middleware CleanupOldCookiesMiddleware résout le problème
3. Le test passe maintenant!
"""
from django.test import TestCase, Client
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import re


class ReproduceCSRF403ErrorTest(TestCase):
    """
    Test qui reproduisait une erreur 403, maintenant résolu par le middleware.
    
    AVANT le middleware: ❌ FAIL (403 CSRF error)
    APRÈS le middleware: ✅ PASS (problème résolu)
    """
    
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
    
    def test_csrf_works_with_old_cookie_cleaned_by_middleware(self):
        """
        Test TDD complet: Ancien cookie 'csrftoken' nettoyé par le middleware.
        
        Scénario:
        - Utilisateur a un ancien cookie 'csrftoken' (d'avant le renommage)
        - GET: Middleware expire automatiquement l'ancien cookie
        - GET: Django définit le nouveau cookie 'nohands_csrftoken'
        - POST: Fonctionne sans erreur 403
        
        AVANT middleware: ❌ Erreur 403
        APRÈS middleware: ✅ Succès
        """
        print("\n" + "="*70)
        print(" TEST TDD: Résolution de l'erreur 403 CSRF ")
        print("="*70)
        
        client = Client(enforce_csrf_checks=True)
        
        # SITUATION: Utilisateur avec ancien cookie
        print("\n[SITUATION] Utilisateur a un ancien cookie 'csrftoken'")
        client.cookies['csrftoken'] = 'OLD_TOKEN_FROM_BEFORE'
        
        # ÉTAPE 1: GET - middleware nettoie l'ancien cookie
        print("\n[ÉTAPE 1] GET /accounts/github/login/")
        response = client.get('/accounts/github/login/')
        self.assertEqual(response.status_code, 200)
        
        print(f"  Cookies dans la réponse: {list(response.cookies.keys())}")
        
        # Vérifier que le middleware a expiré l'ancien cookie
        if 'csrftoken' in response.cookies:
            print(f"  ✓ Middleware a expiré 'csrftoken' (max-age={response.cookies['csrftoken']['max-age']})")
            self.assertEqual(response.cookies['csrftoken']['max-age'], 0)
        
        # Nouveau cookie défini
        self.assertIn('nohands_csrftoken', response.cookies)
        csrf_cookie = response.cookies['nohands_csrftoken'].value
        print(f"  ✓ Nouveau cookie 'nohands_csrftoken': {csrf_cookie[:20]}...")
        
        # Extraire token du formulaire
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        self.assertIsNotNone(match)
        csrf_token = match.group(1)
        print(f"  ✓ Token dans formulaire: {csrf_token[:20]}...")
        
        # ÉTAPE 2: POST - devrait fonctionner
        print("\n[ÉTAPE 2] POST /accounts/github/login/")
        response = client.post('/accounts/github/login/', data={'csrfmiddlewaretoken': csrf_token})
        
        print(f"  Status: {response.status_code}")
        
        # ASSERTION PRINCIPALE: Pas d'erreur 403
        self.assertNotEqual(response.status_code, 403, 
            "Erreur 403 détectée! Le middleware n'a pas résolu le problème."
        )
        
        print("\n" + "="*70)
        print(" ✅ SUCCÈS: Pas d'erreur 403!")
        print(" ✅ Le middleware CleanupOldCookiesMiddleware résout le problème!")
        print("="*70)

    
    def test_csrf_security_validates_cookie_presence(self):
        """
        Test de sécurité: POST sans cookie CSRF doit être rejeté.
        
        Ce test VALIDE que la sécurité CSRF fonctionne correctement:
        un POST sans cookie CSRF doit être rejeté avec 403.
        
        C'est le comportement ATTENDU pour la sécurité.
        """
        print("\n" + "="*70)
        print(" TEST SÉCURITÉ: CSRF rejette POST sans cookie ")
        print("="*70)
        
        client = Client(enforce_csrf_checks=True)
        
        # GET
        response = client.get('/accounts/github/login/')
        self.assertEqual(response.status_code, 200)
        
        # Extraire token
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        csrf_token = match.group(1)
        
        print(f"    Token: {csrf_token[:20]}...")
        
        # SUPPRIMER TOUS LES COOKIES (simule une attaque CSRF)
        print("\n    Suppression de TOUS les cookies CSRF (attaque simulée)")
        client.cookies.clear()
        
        # POST sans cookie - DOIT échouer pour la sécurité
        print(f"    POST sans aucun cookie CSRF")
        response = client.post('/accounts/github/login/', data={'csrfmiddlewaretoken': csrf_token})
        
        print(f"    Status: {response.status_code}")
        
        # VALIDATION: Une attaque CSRF DOIT être rejetée avec 403
        self.assertEqual(response.status_code, 403, 
            "La sécurité CSRF devrait rejeter un POST sans cookie!"
        )
        print("    ✅ Sécurité validée: POST sans cookie correctement rejeté")
        print("="*70)
    
    def test_csrf_security_validates_token_match(self):
        """
        Test de sécurité: POST avec token != cookie doit être rejeté.
        
        Ce test VALIDE que la sécurité CSRF fonctionne correctement:
        un POST où le token ne correspond pas au cookie doit être rejeté avec 403.
        
        C'est le comportement ATTENDU pour la sécurité.
        """
        print("\n" + "="*70)
        print(" TEST SÉCURITÉ: CSRF rejette token invalide ")
        print("="*70)
        
        client = Client(enforce_csrf_checks=True)
        
        # GET
        response = client.get('/accounts/github/login/')
        
        # Extraire token
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        csrf_token = match.group(1)
        
        print(f"    Token du formulaire: {csrf_token[:20]}...")
        
        # Changer le cookie pour un autre valeur (simule une attaque)
        print("\n    Modification du cookie (attaque simulée)")
        client.cookies['nohands_csrftoken'] = 'DIFFERENT_VALUE_123456789'
        
        # POST avec token != cookie - DOIT échouer pour la sécurité
        print(f"    POST avec token valide mais cookie modifié")
        response = client.post('/accounts/github/login/', data={'csrfmiddlewaretoken': csrf_token})
        
        print(f"    Status: {response.status_code}")
        
        # VALIDATION: Une attaque CSRF DOIT être rejetée avec 403
        self.assertEqual(response.status_code, 403,
            "La sécurité CSRF devrait rejeter un POST avec token != cookie!"
        )
        print("    ✅ Sécurité validée: Token invalide correctement rejeté")
        print("="*70)
