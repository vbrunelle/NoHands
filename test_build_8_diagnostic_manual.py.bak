"""
Test de diagnostic pour le build #8 réel dans le navigateur.
Ce script simule exactement ce que fait le navigateur.
"""
import requests
import re
from http.cookies import SimpleCookie

def test_build_8_real():
    """Test le build #8 réel avec le conteneur actuel."""
    
    # On doit d'abord se connecter à NoHands
    session = requests.Session()
    
    print("=" * 60)
    print("SIMULATION DU FLUX NAVIGATEUR POUR BUILD #8")
    print("=" * 60)
    
    # Étape 1: Se connecter à NoHands (simulé - normalement vous êtes déjà connecté)
    print("\n[1] Connexion à NoHands...")
    print("    NOTE: Dans ce script, on n'est pas authentifié")
    print("    Dans votre navigateur, vous ÊTES authentifié via GitHub")
    
    # Étape 2: GET de la page login du conteneur
    print("\n[2] GET http://localhost:8000/builds/8/fwd/login/")
    try:
        resp = session.get(
            'http://localhost:8000/builds/8/fwd/login/',
            allow_redirects=False
        )
        print(f"    Status: {resp.status_code}")
        
        if resp.status_code == 302:
            print(f"    ⚠️  Redirection vers: {resp.headers.get('Location')}")
            print("    Raison: Pas authentifié à NoHands (@login_required)")
            print("\n    SOLUTION: Ce script ne peut pas tester car non authentifié.")
            print("    Mais dans votre navigateur, vous ÊTES authentifié.")
            return
        
        print(f"    Cookies reçus: {list(resp.cookies.keys())}")
        
        if 'csrftoken' in resp.cookies:
            csrf_cookie = resp.cookies['csrftoken']
            print(f"    ✓ Cookie csrftoken: {csrf_cookie[:20]}...")
            
            # Vérifier le path du cookie
            for cookie in resp.cookies:
                if cookie.name == 'csrftoken':
                    print(f"    Path du cookie: {cookie.path}")
                    print(f"    Domain du cookie: {cookie.domain or '(non défini)'}")
        else:
            print("    ❌ Pas de cookie csrftoken reçu")
        
        # Extraire le token CSRF du HTML
        html = resp.text
        csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)', html)
        if csrf_match:
            html_token = csrf_match.group(1)
            print(f"    ✓ Token CSRF dans HTML: {html_token[:20]}...")
            
            # Vérifier si le cookie et le token HTML correspondent
            if 'csrftoken' in resp.cookies:
                if resp.cookies['csrftoken'] == html_token:
                    print("    ✓ Cookie et HTML token correspondent")
                else:
                    print("    ⚠️  Cookie et HTML token sont DIFFÉRENTS!")
                    print(f"       Cookie: {resp.cookies['csrftoken'][:20]}...")
                    print(f"       HTML:   {html_token[:20]}...")
        else:
            print("    ❌ Pas de token CSRF dans le HTML")
        
        # Étape 3: POST du formulaire
        if 'csrftoken' in resp.cookies and csrf_match:
            print("\n[3] POST http://localhost:8000/builds/8/fwd/login/")
            
            post_data = {
                'csrfmiddlewaretoken': html_token,
                'username': 'test',
                'password': 'test123'
            }
            
            print(f"    Data: username=test, csrfmiddlewaretoken={html_token[:20]}...")
            print(f"    Cookie envoyé: csrftoken={resp.cookies['csrftoken'][:20]}...")
            
            resp2 = session.post(
                'http://localhost:8000/builds/8/fwd/login/',
                data=post_data,
                allow_redirects=False
            )
            
            print(f"    Status: {resp2.status_code}")
            
            if resp2.status_code == 403:
                print("    ❌ ERREUR 403 - CSRF a échoué")
                print("\n    Contenu de la réponse:")
                print("    " + resp2.text[:200])
            elif resp2.status_code == 302:
                print(f"    ✓ Redirection vers: {resp2.headers.get('Location')}")
            else:
                print(f"    Réponse: {resp2.status_code}")
        
    except requests.exceptions.ConnectionError:
        print("    ❌ Impossible de se connecter à localhost:8000")
        print("    Assurez-vous que manage.py runserver est en cours d'exécution")
    except Exception as e:
        print(f"    ❌ Erreur: {e}")
    
    print("\n" + "=" * 60)
    print("ANALYSE")
    print("=" * 60)
    print("""
Si le test ci-dessus montre:
- Status 302 = Redirection car non authentifié (normal pour ce script)
  → Dans votre navigateur, vous êtes authentifié, donc ça devrait fonctionner

Si dans votre navigateur vous avez:
- Cookie défini avec le bon path ✓
- Token HTML présent ✓
- Mais toujours erreur 403 ❌

Alors le problème peut être:
1. Le navigateur n'envoie pas le cookie (vérifiez DevTools → Network → Headers)
2. Le cookie a un attribut qui empêche son envoi (SameSite, Domain, etc.)
3. Le middleware CSRF de Django dans le conteneur bloque quand même

SOLUTION DÉJÀ IMPLÉMENTÉE:
Le nouveau Dockerfile template désactive automatiquement le middleware CSRF
dans les conteneurs. Il faut rebuilder le build #8 pour que ça prenne effet.
""")

if __name__ == '__main__':
    test_build_8_real()
