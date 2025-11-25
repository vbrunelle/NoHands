"""
Test TDD pour identifier un problème CSRF potentiel avec des cookies conflictuels.

Hypothèse: Peut-être que le navigateur a des anciens cookies (csrftoken ET nohands_csrftoken)
qui causent un conflit.
"""
from django.test import TestCase, Client
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class CSRFConflictingCookiesTest(TestCase):
    """Test pour détecter des conflits potentiels avec plusieurs cookies CSRF."""
    
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
    
    def test_csrf_with_old_csrftoken_cookie(self):
        """
        Test si un ancien cookie 'csrftoken' cause un conflit.
        
        Scénario: L'utilisateur a un ancien cookie 'csrftoken' d'avant 
        que vous changiez le nom en 'nohands_csrftoken'.
        """
        print("\n" + "="*60)
        print("TEST: CSRF avec ancien cookie csrftoken conflictuel")
        print("="*60)
        
        client = Client(enforce_csrf_checks=True)
        
        # Simuler qu'il y a un ancien cookie 'csrftoken' dans le navigateur
        client.cookies['csrftoken'] = 'OLD_CSRF_TOKEN_FROM_BEFORE'
        
        # GET pour obtenir le nouveau token
        print("\n[1] GET /accounts/github/login/")
        print("    Cookie conflictuel présent: csrftoken=OLD_CSRF_TOKEN_FROM_BEFORE")
        response = client.get('/accounts/github/login/')
        
        self.assertEqual(response.status_code, 200)
        
        # Django devrait définir le nouveau cookie nohands_csrftoken
        print(f"    Cookies après GET: {list(response.cookies.keys())}")
        
        self.assertIn('nohands_csrftoken', response.cookies)
        new_csrf = response.cookies['nohands_csrftoken'].value
        print(f"    Nouveau cookie: nohands_csrftoken={new_csrf[:20]}...")
        
        # Extraire le token du HTML
        import re
        html = response.content.decode('utf-8')
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', html)
        csrf_token = match.group(1)
        print(f"    Token dans form: {csrf_token[:20]}...")
        
        # POST avec le nouveau token
        print("\n[2] POST /accounts/github/login/")
        print(f"    Cookies envoyés:")
        print(f"      - csrftoken=OLD_CSRF_TOKEN_FROM_BEFORE (ancien)")
        print(f"      - nohands_csrftoken={new_csrf[:20]}... (nouveau)")
        
        post_data = {
            'csrfmiddlewaretoken': csrf_token,
        }
        
        response = client.post('/accounts/github/login/', data=post_data)
        
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 403:
            print("\n❌ ERREUR 403 - L'ancien cookie csrftoken cause un conflit!")
            print("SOLUTION: Nettoyer les cookies du navigateur ou expirer csrftoken")
            self.fail(
                "Conflit détecté: L'ancien cookie 'csrftoken' interfère avec 'nohands_csrftoken'.\n"
                "L'utilisateur doit nettoyer ses cookies pour résoudre le problème."
            )
        
        self.assertNotEqual(response.status_code, 403)
        print("    ✅ Pas de conflit - Django gère correctement plusieurs cookies")
        print("="*60)
    
    def test_solution_clear_old_cookie(self):
        """
        Test que la solution consiste à expirer l'ancien cookie.
        
        Si test_csrf_with_old_csrftoken_cookie échoue, cette solution 
        devrait fonctionner: ajouter du code pour expirer 'csrftoken'.
        """
        print("\n" + "="*60)
        print("TEST: Solution - Expirer l'ancien cookie")
        print("="*60)
        
        client = Client(enforce_csrf_checks=True)
        
        # Ancien cookie présent
        client.cookies['csrftoken'] = 'OLD_TOKEN'
        
        # GET
        response = client.get('/accounts/github/login/')
        
        # SOLUTION: Le serveur devrait expirer l'ancien cookie
        # En vérifiant si une Set-Cookie supplémentaire est envoyée
        # pour expirer 'csrftoken'
        
        # Pour l'instant, notez juste si c'est nécessaire
        print("    Note: Si le test précédent échoue, il faudra ajouter")
        print("    un middleware pour expirer les anciens cookies 'csrftoken'")
        print("="*60)
