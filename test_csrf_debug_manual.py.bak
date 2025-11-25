#!/usr/bin/env python
"""
Script de diagnostic CSRF pour le proxy NoHands
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-key-for-debugging')
os.environ['DJANGO_SETTINGS_MODULE'] = 'nohands_project.settings'
django.setup()

import requests
from http.cookies import SimpleCookie

print("=== Test de diagnostic CSRF ===\n")

# Test 1: Vérifier que le conteneur renvoie un cookie
print("1. Test du conteneur direct (port 8004):")
resp = requests.get('http://127.0.0.1:8004/signup/')
print(f"   Status: {resp.status_code}")
print(f"   Cookies: {resp.cookies}")
if resp.cookies:
    for cookie in resp.cookies:
        print(f"   - {cookie.name}={cookie.value[:20]}...")
        print(f"     Path: {cookie.path}")
        print(f"     Domain: {cookie.domain}")
print()

# Test 2: S'authentifier à NoHands d'abord
print("2. Authentification à NoHands:")
session = requests.Session()
# D'abord GET pour récupérer le token CSRF de NoHands
resp = session.get('http://localhost:8000/accounts/login/')
print(f"   Status login page: {resp.status_code}")

# Extraire le token CSRF de NoHands de la page de login
import re
csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)', resp.text)
if csrf_match:
    nohands_csrf = csrf_match.group(1)
    print(f"   Token CSRF NoHands: {nohands_csrf[:20]}...")
    
    # Vous devez mettre vos vraies credentials ici
    print("   ⚠️  Authentification impossible automatiquement")
    print("   NOTE: Le test suivant échouera car non authentifié")
    print()
else:
    print("   ❌ Token CSRF introuvable")
    print()

# Test 3: Vérifier le proxy GET (sans auth, va rediriger)
print("3. Test du proxy GET (via NoHands, sans auth):")
resp = session.get('http://localhost:8000/builds/7/fwd/signup/', allow_redirects=False)
print(f"   Status: {resp.status_code}")
if resp.status_code == 302:
    print(f"   Redirige vers: {resp.headers.get('Location', 'inconnu')}")
    print("   → Ceci explique pourquoi aucun cookie n'est reçu!")
    print("   → La vue proxy_to_container a un @login_required")
print(f"   Cookies reçus: {resp.cookies}")
print()

print("CONCLUSION:")
print("Le proxy nécessite une authentification à NoHands.")
print("Dans votre navigateur, vous devez:")
print("1. Être connecté à NoHands (ce qui est le cas)")
print("2. Le navigateur doit envoyer le cookie nohands_sessionid")
print("3. Puis le proxy transmet la requête au conteneur")
print()
print("Vérifiez dans les logs de manage.py runserver si vous voyez")
print("des requêtes GET/POST arriver au proxy quand vous testez manuellement.")

print("\n=== Fin du diagnostic ===")
