"""
Tests TDD pour le middleware de nettoyage des anciens cookies.
"""
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from nohands_project.cleanup_cookies_middleware import CleanupOldCookiesMiddleware


class CleanupOldCookiesMiddlewareTest(TestCase):
    """Test que le middleware nettoie correctement les anciens cookies."""
    
    def setUp(self):
        """Setup pour les tests."""
        self.factory = RequestFactory()
        
        # Middleware test simple
        def simple_view(request):
            return HttpResponse("OK")
        
        self.middleware = CleanupOldCookiesMiddleware(simple_view)
    
    def test_middleware_expires_old_csrftoken_cookie(self):
        """Test que le middleware expire l'ancien cookie 'csrftoken'."""
        print("\n" + "="*60)
        print("TEST: Middleware expire l'ancien cookie csrftoken")
        print("="*60)
        
        # Créer une requête avec un ancien cookie csrftoken
        request = self.factory.get('/')
        request.COOKIES = {'csrftoken': 'OLD_TOKEN'}
        
        print("    Requête avec: csrftoken=OLD_TOKEN")
        
        # Appeler le middleware
        response = self.middleware(request)
        
        # Vérifier que le cookie est expiré dans la réponse
        cookies_header = response.cookies
        
        print(f"    Cookies dans la réponse: {list(cookies_header.keys())}")
        
        # Le cookie csrftoken devrait être présent avec max_age=0 (expiré)
        self.assertIn('csrftoken', cookies_header)
        csrf_cookie = cookies_header['csrftoken']
        
        print(f"    Cookie csrftoken:")
        print(f"      value: {csrf_cookie.value}")
        print(f"      max-age: {csrf_cookie['max-age']}")
        
        # Vérifier que max-age=0 (cookie expiré)
        self.assertEqual(csrf_cookie['max-age'], 0)
        self.assertEqual(csrf_cookie.value, '')
        
        print("    ✅ L'ancien cookie csrftoken est bien expiré!")
        print("="*60)
    
    def test_middleware_expires_old_sessionid_cookie(self):
        """Test que le middleware expire l'ancien cookie 'sessionid'."""
        print("\n" + "="*60)
        print("TEST: Middleware expire l'ancien cookie sessionid")
        print("="*60)
        
        request = self.factory.get('/')
        request.COOKIES = {'sessionid': 'OLD_SESSION'}
        
        print("    Requête avec: sessionid=OLD_SESSION")
        
        response = self.middleware(request)
        
        self.assertIn('sessionid', response.cookies)
        session_cookie = response.cookies['sessionid']
        
        print(f"    Cookie sessionid max-age: {session_cookie['max-age']}")
        
        self.assertEqual(session_cookie['max-age'], 0)
        self.assertEqual(session_cookie.value, '')
        
        print("    ✅ L'ancien cookie sessionid est bien expiré!")
        print("="*60)
    
    def test_middleware_doesnt_touch_new_cookies(self):
        """Test que le middleware ne touche pas aux nouveaux cookies."""
        print("\n" + "="*60)
        print("TEST: Middleware ne touche pas aux nouveaux cookies")
        print("="*60)
        
        request = self.factory.get('/')
        request.COOKIES = {
            'nohands_csrftoken': 'NEW_TOKEN',
            'nohands_sessionid': 'NEW_SESSION'
        }
        
        print("    Requête avec les NOUVEAUX cookies (nohands_*)")
        
        response = self.middleware(request)
        
        # Ces cookies ne devraient PAS être dans la réponse
        # car le middleware ne les expire pas
        print(f"    Cookies expirés: {list(response.cookies.keys())}")
        
        self.assertNotIn('nohands_csrftoken', response.cookies)
        self.assertNotIn('nohands_sessionid', response.cookies)
        
        print("    ✅ Les nouveaux cookies ne sont pas affectés!")
        print("="*60)
    
    def test_middleware_handles_multiple_old_cookies(self):
        """Test que le middleware gère plusieurs anciens cookies en même temps."""
        print("\n" + "="*60)
        print("TEST: Middleware gère plusieurs anciens cookies")
        print("="*60)
        
        request = self.factory.get('/')
        request.COOKIES = {
            'csrftoken': 'OLD_CSRF',
            'sessionid': 'OLD_SESSION',
            'nohands_csrftoken': 'NEW_CSRF',  # Nouveau, ne devrait pas être touché
        }
        
        print("    Requête avec csrftoken ET sessionid (anciens)")
        
        response = self.middleware(request)
        
        # Les deux anciens cookies devraient être expirés
        self.assertIn('csrftoken', response.cookies)
        self.assertIn('sessionid', response.cookies)
        self.assertEqual(response.cookies['csrftoken']['max-age'], 0)
        self.assertEqual(response.cookies['sessionid']['max-age'], 0)
        
        # Le nouveau ne devrait pas être touché
        self.assertNotIn('nohands_csrftoken', response.cookies)
        
        print("    ✅ Tous les anciens cookies sont expirés!")
        print("="*60)
