"""

 
`requests` + `BeautifulSoup` (methode statique) ne recuperent jamais le
contenu injecte par JavaScript, du coup des sites comme ONU
Femmes qui sont des dashbords dynamiques
 
Cette version ajoute un autre essai automatique : si le scraping statique
recupere moins de 300 caracteres, on relance avec `Playwright`, un vrai
navigateur (Chromium) execute en arriere-plan, il execute le JavaScript de
la page avant de recuperer le HTML final.

"""
 
# import os
# import re
# import requests
# from bs4 import BeautifulSoup
# from config_sources import LIENS_UTILES
 
# os.makedirs("textes", exist_ok=True)
 
# SEUIL_CONTENU_SUFFISANT = 300
 
 
# def nom_fichier_depuis_url(url):
#     sans_protocole = re.sub(r"^https?://", "", url)
#     nettoye = re.sub(r"[^a-zA-Z0-9]+", "-", sans_protocole).strip("-")
#     return f"web_{nettoye}.txt"
 
 
# def nettoyer_html(html_brut):
#     """Fonction commune : retire scripts/styles/menus et normalise les
#     espaces, que le HTML vienne de requests ou de Playwright."""
#     soupe = BeautifulSoup(html_brut, "html.parser")
#     for balise in soupe(["script", "style", "nav", "footer", "header", "noscript"]):
#         balise.decompose()
#     texte = soupe.get_text(separator=" ", strip=True)
#     return re.sub(r"\s+", " ", texte)
 
 
# def scraper_page_statique(lien):
#     """Methode 1 (rapide) : requete HTTP simple, ne voit PAS le JavaScript."""
#     try:
#         reponse = requests.get(lien, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
#         reponse.raise_for_status()
#         return nettoyer_html(reponse.text)
#     except Exception as erreur:
#         print(f"    -> ÉCHEC (méthode statique) : {erreur}")
#         return ""
 
 
# def scraper_page_navigateur(lien, timeout_ms=20000):
#     """
#     Methode 2 (fallback, plus lente) : ouvre un vrai navigateur Chromium en
#     arriere-plan, attend que la page (et son JavaScript) finisse de
#     charger, puis recupere le HTML final tel qu'affiche a l'ecran.
#     """
#     try:
#         from playwright.sync_api import sync_playwright
#     except ImportError:
#         print("    -> Playwright non installé (pip install playwright && playwright install chromium)")
#         return ""
 
#     try:
#         with sync_playwright() as p:
#             navigateur = p.chromium.launch()
#             page = navigateur.new_page()
#             page.goto(lien, timeout=timeout_ms, wait_until="networkidle")
#             html = page.content()
#             navigateur.close()
#         return nettoyer_html(html)
#     except Exception as erreur:
#         print(f"    -> ÉCHEC (navigateur headless) : {erreur}")
#         return ""
 
 
# print("Scraping des pages web\n")
 
# resume_final = []  # pour afficher un tableau recapitulatif a la toute fin
 
# for source in LIENS_UTILES:
#     lien = source["lien"]
#     nom = source["nom"]
#     print(f"Scraping de : {nom} ({lien})")
 
#     # --- Tentative 1 : methode statique (rapide) ---
#     print("  [1/2] Tentative avec requête HTTP statique...")
#     texte = scraper_page_statique(lien)
#     methode_utilisee = "statique"
 
#     # --- Tentative 2 : navigateur headless, seulement si necessaire ---
#     if len(texte) < SEUIL_CONTENU_SUFFISANT:
#         print(f"  !! Contenu insuffisant en statique ({len(texte)} caractères) -- probablement du JavaScript.")
#         print("  [2/2] Nouvelle tentative avec navigateur headless (Playwright)...")
#         texte_navigateur = scraper_page_navigateur(lien)
#         if len(texte_navigateur) > len(texte):
#             texte = texte_navigateur
#             methode_utilisee = "navigateur headless"
 
#     nb_caracteres = len(texte)
#     nom_fichier = nom_fichier_depuis_url(lien)
#     chemin = os.path.join("textes", nom_fichier)
 
#     with open(chemin, "w", encoding="utf-8") as f:
#         f.write(f"[SOURCE: {nom}]\n[LIEN: {lien}]\n\n{texte}")
 
#     if nb_caracteres >= SEUIL_CONTENU_SUFFISANT:
#         statut = f" bien marche  ({methode_utilisee})"
#     else:
#         statut = " ÉCHEC "
#         print(f"  !! ATTENTION : même le navigateur headless n'a récupéré que {nb_caracteres} caractères.")
#         print("     Solutions possibles : chercher l'API JSON interne du site (onglet Réseau du")
#         print("     navigateur, F12), ou rédiger un résumé manuel dans ce fichier :")
#         print(f"     {chemin}")
 
#     print(f"  -> {nb_caracteres} caractères récupérés -> {chemin} [{statut}]\n")
#     resume_final.append((nom, nb_caracteres, statut))
 
# print("=" * 70)
# print("RÉCAPITULATIF")
# print("=" * 70)
# for nom, nb_caracteres, statut in resume_final:
#     print(f"  {statut:20s} {nb_caracteres:6d} caractères -- {nom}")
 
# print("\nScraping terminé.")



import os
import re
import concurrent.futures
import requests
import urllib3
from bs4 import BeautifulSoup
from config_sources import LIENS_UTILES
 
os.makedirs("textes", exist_ok=True)
 
# Sous ce nombre de caracteres recuperes, on considere que le contenu
# n'est pas suffisant, et on declenche la methode de secours (navigateur
# headless).
SEUIL_CONTENU_SUFFISANT = 300
 
 
def nom_fichier_depuis_url(url):
    """
    Transforme une URL en un nom de fichier propre et utilisable sur
    disque.
    Ex: "https://data.unwomen.org/country/senegal"
        -> "web_data-unwomen-org-country-senegal.txt"
 
    re.sub(r"^https?://", "", url) : supprime le debut "http://" ou
    "https://" de l'URL (le "?" rend le "s" optionnel, donc ca couvre les
    deux cas).
 
    re.sub(r"[^a-zA-Z0-9]+", "-", sans_protocole) : remplace tout groupe
    de caracteres qui N'EST PAS une lettre ou un chiffre (donc les points,
    slashs, tirets existants...) par un seul tiret "-".
 
    .strip("-") : enleve un eventuel tiret en trop au tout debut ou a la
    toute fin du resultat.
    """
    sans_protocole = re.sub(r"^https?://", "", url)
    nettoye = re.sub(r"[^a-zA-Z0-9]+", "-", sans_protocole).strip("-")
    return f"web_{nettoye}.txt"
 
 
def nettoyer_html(html_brut):
    """
    Prend du HTML brut (recupere soit par requests, soit par Playwright)
    et en extrait uniquement le texte lisible, en supprimant tout ce qui
    n'est pas du contenu pour un humain.
 
    BeautifulSoup(html_brut, "html.parser") : cree un objet "soupe" qui
    represente toute la structure du HTML, navigable en Python (comme un
    arbre de balises imbriquees). "html.parser" est l'analyseur HTML
    integre a Python, suffisant ici (pas besoin d'un analyseur externe
    plus rapide comme lxml).
 
    soupe(["script", "style", "nav", "footer", "header", "noscript"]) :
    cherche TOUTES les balises de ces types (menus de navigation, scripts
    JavaScript, styles CSS, pieds de page...) -- .decompose() les
    supprime completement de la structure, pour qu'elles n'apparaissent
    pas dans le texte final.
 
    soupe.get_text(separator=" ", strip=True) : recupere tout le texte
    restant, en inserant un espace entre chaque morceau de texte
    initialement separe par des balises (separator=" "), et en retirant
    les espaces inutiles en debut/fin de chaque morceau (strip=True).
 
    re.sub(r"\\s+", " ", texte) : remplace toute SUITE d'espaces/sauts de
    ligne/tabulations (\\s+ = un ou plusieurs caracteres d'espacement) par
    un seul espace -- necessaire car get_text() laisse souvent des
    espaces multiples quand le HTML source est plein de balises imbriquees.
    """
    soupe = BeautifulSoup(html_brut, "html.parser")
    for balise in soupe(["script", "style", "nav", "footer", "header", "noscript"]):
        balise.decompose()
    texte = soupe.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", texte)
 
 
def scraper_page_statique(lien):
    """
    METHODE 1 (rapide) : envoie une simple requete HTTP et recupere le
    HTML brut, SANS executer le JavaScript de la page.
 
    requests.get(lien, timeout=15, headers={"User-Agent": "Mozilla/5.0"}) :
      - timeout=15 : abandonne la requete si le serveur ne repond pas
        dans les 15 secondes (evite de rester bloque indefiniment).
      - headers={"User-Agent": "Mozilla/5.0"} : certains sites refusent
        de repondre correctement si la requete ne "ressemble" pas a un
        vrai navigateur -- on se presente donc comme tel.
 
    reponse.raise_for_status() : declenche une erreur si le serveur a
    renvoye un code d'erreur HTTP (ex: 404 page introuvable, 500 erreur
    serveur) -- sans cette ligne, on continuerait avec une reponse
    invalide sans s'en rendre compte.
 
    GESTION SPECIFIQUE DES ERREURS SSL : certains sites (notamment
    womencount.ansd.sn dans notre cas) ont un certificat HTTPS mal
    configure cote serveur (chaine de certificats incomplete). Ce n'est
    pas reparable de notre cote -- on retente donc la requete avec
    verify=False (verification du certificat desactivee), avec un
    avertissement clair affiche, car c'est un compromis de securite
    (on ne verifie plus que le site est authentique).
    """
    try:
        reponse = requests.get(lien, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        reponse.raise_for_status()
        return nettoyer_html(reponse.text)
 
    except requests.exceptions.SSLError:
        print("    !! Certificat SSL invalide/mal configuré côté serveur -- "
              "nouvelle tentative SANS vérification SSL...")
        try:
            # Desactive l'avertissement urllib3 correspondant, pour ne
            # pas afficher deux fois le meme genre de message.
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            reponse = requests.get(
                lien, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, verify=False
            )
            reponse.raise_for_status()
            print("    ⚠️  Contenu récupéré SANS vérification SSL -- à utiliser avec prudence "
                  "(vérifie que le lien est bien le site officiel).")
            return nettoyer_html(reponse.text)
        except Exception as erreur:
            print(f"    -> ÉCHEC (même sans vérification SSL) : {erreur}")
            return ""
 
    except Exception as erreur:
        print(f"    -> ÉCHEC (méthode statique) : {erreur}")
        return ""
 
 
def _tache_playwright(lien, timeout_ms):
    """
    Le vrai travail Playwright -- EXECUTE A L'INTERIEUR D'UN THREAD SEPARE
    (voir scraper_page_navigateur juste apres), pour eviter un conflit
    technique avec la boucle asyncio parfois deja active dans certains
    environnements Python interactifs.
 
    from playwright.sync_api import sync_playwright : import fait A
    L'INTERIEUR de la fonction (pas en haut du fichier) volontairement --
    ca permet au reste du script de fonctionner meme si Playwright n'est
    pas installe, tant que cette fonction n'est jamais appelee (utile si
    la methode statique suffit pour la plupart des sites).
 
    sync_playwright() : demarre Playwright et gere sa fermeture propre
    automatiquement a la fin du bloc "with".
 
    p.chromium.launch() : lance un navigateur Chromium en arriere-plan,
    sans fenetre visible (mode "headless" par defaut).
 
    page.goto(lien, timeout=timeout_ms, wait_until="networkidle") :
    demande au navigateur d'aller sur cette URL, et attend jusqu'a
    "networkidle" -- c'est-a-dire jusqu'a ce qu'il n'y ait plus de
    requetes reseau actives depuis un moment, signe que la page (et son
    JavaScript) a fini de charger son contenu dynamique.
 
    page.content() : recupere le HTML final de la page, TEL QU'IL EST
    APRES l'execution du JavaScript -- contrairement au HTML brut initial
    que requests aurait recupere.
    """
    from playwright.sync_api import sync_playwright
 
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        page = navigateur.new_page()
        page.goto(lien, timeout=timeout_ms, wait_until="networkidle")
        html = page.content()
        navigateur.close()
    return html
 
 
def scraper_page_navigateur(lien, timeout_ms=20000):
    """
    METHODE 2 (fallback, plus lente) : lance _tache_playwright() dans un
    THREAD DEDIE, via concurrent.futures.ThreadPoolExecutor.
 
    POURQUOI UN THREAD SEPARE : l'API "synchrone" de Playwright (celle
    qu'on utilise, plus simple a lire que l'API asynchrone) refuse de
    s'executer si elle detecte une boucle asyncio deja active dans le
    thread courant -- ce qui arrive dans certains terminaux Python
    interactifs (comme celui de Positron). Un THREAD TOUT NEUF, cree ici,
    demarre sans boucle asyncio heritee, ce qui evite completement ce
    conflit, quel que soit l'environnement d'ou le script est lance.
 
    executeur.submit(_tache_playwright, lien, timeout_ms) : lance la
    fonction dans le thread, et renvoie immediatement un objet "future"
    (une sorte de "promesse" du resultat a venir).
 
    future.result(timeout=...) : attend que le thread termine son travail
    (bloque jusqu'a ce moment-la), avec un delai maximum de securite un
    peu plus long que le timeout de Playwright lui-meme, pour laisser le
    temps a une fermeture propre en cas de souci.
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executeur:
            future = executeur.submit(_tache_playwright, lien, timeout_ms)
            html = future.result(timeout=(timeout_ms / 1000) + 15)
        return nettoyer_html(html)
    except Exception as erreur:
        print(f"    -> ÉCHEC (navigateur headless) : {erreur}")
        return ""
 

# Boucle Principale - traite chaque lien liste dans config_sources.py

 
print("Scraping des pages web\n")
 
resume_final = []   # accumule (nom, nb_caracteres, statut) pour le recapitulatif final
 
for source in LIENS_UTILES:
    lien = source["lien"]
    nom = source["nom"]
    print(f"Scraping de : {nom} ({lien})")
 
    # Methode 1 : methode statique (rapide) 
    print("  requête HTTP statique...")
    texte = scraper_page_statique(lien)
    methode_utilisee = "statique"
 
    # --- Tentative 2 : navigateur headless, SEULEMENT si necessaire ---
    if len(texte) < SEUIL_CONTENU_SUFFISANT:
        print(f"   Contenu insuffisant en statique ({len(texte)} caractères) - probablement du JavaScript.")
        print("  [2/2] Nouvelle tentative avec navigateur headless (Playwright)")
        texte_navigateur = scraper_page_navigateur(lien)
        # On ne garde le resultat du navigateur que s'il est effectivement
        # meilleur que ce que la methode statique avait deja recupere.
        if len(texte_navigateur) > len(texte):
            texte = texte_navigateur
            methode_utilisee = "navigateur headless"
 
    nb_caracteres = len(texte)
    nom_fichier = nom_fichier_depuis_url(lien)
    chemin = os.path.join("textes", nom_fichier)
 
    # On sauvegarde le lien d'origine et le nom de la source en tete du
    # fichier texte. ca servira de metadonnee "lien"/"titre" a l'etape 3
    # (indexation), sans avoir besoin d'un fichier de config supplementaire.
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(f"[SOURCE: {nom}]\n[LIEN: {lien}]\n\n{texte}")
 
    if nb_caracteres >= SEUIL_CONTENU_SUFFISANT:
        statut = f"C OK ({methode_utilisee})"
    else:
        statut = "ÉCHEC "
        print(f"   probleme : même le navigateur headless n'a récupéré que {nb_caracteres} caractères.")
        print("     Solutions possibles : chercher l'API JSON interne du site (onglet Réseau du")
        print("     navigateur, F12), ou rédiger un résumé manuel dans le fichier :")
        print(f"     {chemin}")
 
    print(f"  -> {nb_caracteres} caractères récupérés -> {chemin} [{statut}]\n")
    resume_final.append((nom, nb_caracteres, statut))
 
print("=" * 70)
print("RÉCAPITULATIF")
print("=" * 70)
for nom, nb_caracteres, statut in resume_final:
    print(f"  {statut:20s} {nb_caracteres:6d} caractères -- {nom}")
 
print("\nScraping terminé.")
 