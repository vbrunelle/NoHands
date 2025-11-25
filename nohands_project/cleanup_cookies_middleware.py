"""
Middleware pour nettoyer les anciens cookies et éviter les conflits CSRF.

Ce middleware:
1. Expire tout ancien cookie 'csrftoken' pour éviter les conflits avec 'nohands_csrftoken'
2. Expire tout ancien cookie 'sessionid' pour éviter les conflits avec 'nohands_sessionid'
"""


class CleanupOldCookiesMiddleware:
    """
    Middleware pour expirer les anciens cookies qui pourraient causer des conflits.
    
    Quand on renomme des cookies (ex: csrftoken -> nohands_csrftoken), les navigateurs
    gardent les anciens cookies. Ce middleware les expire pour éviter tout conflit.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Liste des anciens noms de cookies à expirer
        self.old_cookies_to_expire = [
            'csrftoken',    # Ancien nom avant 'nohands_csrftoken'
            'sessionid',    # Ancien nom avant 'nohands_sessionid'
        ]
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Pour chaque ancien cookie, si présent dans la requête, l'expirer
        for old_cookie_name in self.old_cookies_to_expire:
            if old_cookie_name in request.COOKIES:
                # Expirer le cookie en le définissant avec max_age=0
                response.delete_cookie(
                    old_cookie_name,
                    path='/',
                    domain=None,  # Utilise le domaine par défaut
                    samesite='Lax',
                )
        
        return response
