# Extraire le texte de doc1.pdf et doc2.pdf

 
# import fitz  # pymupdf - lire PDF 
# import os
# from config_sources import SOURCES # importer le dictionnaire SOURCES creer plus tot  



# # creer le dossier "textes" s'il n'existe pas (okay/continuer s'il existe deja)
# os.makedirs("textes", exist_ok=True)
 
# # Boucle pour traiter chaque fichier PDF un par un
# for nom_fichier in SOURCES.keys():
#     print(f"Lecture de : {nom_fichier}")
 
#     document = fitz.open(nom_fichier)
 
#     texte_complet = ""
#     for numero_page, page in enumerate(document, start=1):
#         texte_page = page.get_text()
#         texte_complet += f"\n\n[PAGE {numero_page}]\n{texte_page}"
 
#     document.close() 
 
#     nom_txt = nom_fichier.replace(".pdf", ".txt")
#     chemin_txt = os.path.join("textes", nom_txt)
 
#     with open(chemin_txt, "w", encoding="utf-8") as f:
#         f.write(texte_complet)
 
#     print(f"  -> Texte sauvegarde dans : {chemin_txt} ({len(texte_complet)} caracteres)")
 
# print("\nTermine. Peut aller a l'etape 2.") 

# import fitz

# for nom in ["doc3.pdf", "doc5.pdf", "doc6.pdf", "doc10.pdf"]:
#     doc = fitz.open(nom)
#     print(f"\n=== {nom} ({len(doc)} pages au total) ===")
#     for i, page in enumerate(doc):
#         if i >= 15:  # on regarde les 15 premières pages cette fois
#             break
#         texte = page.get_text().strip()
#         print(f"  page {i+1} : {len(texte)} caractères")
#     doc.close()






'''
 - doc3.pdf (17 pages au total) 
  page 1 : 0 caractères
  page 2 : 51 caractères
  page 3 : 16 caractères
  page 4 : 3 caractères
  page 5 : 3 caractères
  page 6 : 3 caractères
  page 7 : 3 caractères
  page 8 : 3 caractères
  page 9 : 0 caractères
  page 10 : 0 caractères
  page 11 : 3 caractères
  page 12 : 3 caractères
  page 13 : 3 caractères
  page 14 : 3 caractères
  page 15 : 3 caractères

- doc5.pdf (33 pages au total) 
  page 1 : 0 caractères
  page 2 : 40 caractères
  page 3 : 54 caractères
  page 4 : 3 caractères
  page 5 : 3 caractères
  page 6 : 3 caractères
  page 7 : 3 caractères
  page 8 : 16 caractères
  page 9 : 3 caractères
  page 10 : 923 caractères
  page 11 : 20 caractères
  page 12 : 0 caractères
  page 13 : 97 caractères
  page 14 : 18 caractères
  page 15 : 18 caractères

- doc6.pdf (2 pages au total) 
  page 1 : 0 caractères
  page 2 : 0 caractères

- doc10.pdf (16 pages au total) 
  page 1 : 122 caractères
  page 2 : 0 caractères
  page 3 : 0 caractères
  page 4 : 0 caractères
  page 5 : 0 caractères
  page 6 : 0 caractères
  page 7 : 0 caractères
  page 8 : 0 caractères
  page 9 : 0 caractères
  page 10 : 0 caractères
  page 11 : 6 caractères
  page 12 : 0 caractères
  page 13 : 0 caractères
  page 14 : 0 caractères
  page 15 : 0 caractères

'''

'''
doc1.pdf — page 1 : 0 caractères de texte, 1 image(s)
doc1.pdf — page 2 : 2310 caractères de texte, 0 image(s)
doc1.pdf — page 3 : 2260 caractères de texte, 0 image(s)
doc2.pdf — page 1 : 12 caractères de texte, 1 image(s)
doc2.pdf — page 2 : 3219 caractères de texte, 0 image(s)
doc2.pdf — page 3 : 2021 caractères de texte, 0 image(s)
doc3.pdf — page 1 : 0 caractères de texte, 2 image(s)
doc3.pdf — page 2 : 51 caractères de texte, 2 image(s)
doc3.pdf — page 3 : 16 caractères de texte, 1 image(s)
doc5.pdf — page 1 : 0 caractères de texte, 2 image(s)
doc5.pdf — page 2 : 40 caractères de texte, 2 image(s)
doc5.pdf — page 3 : 54 caractères de texte, 1 image(s)
doc6.pdf — page 1 : 0 caractères de texte, 7 image(s)
doc6.pdf — page 2 : 0 caractères de texte, 7 image(s)
doc10.pdf — page 1 : 122 caractères de texte, 4 image(s)
doc10.pdf — page 2 : 0 caractères de texte, 9 image(s)
doc10.pdf — page 3 : 0 caractères de texte, 1 image(s)

'''



"""

EXTRACTION DES RAPPORTS PDF DE L'ANSD



Pour chaque PDF listé dans config_sources.py le code :
  - ouvre le PDF et parcourt chaque page une par une.
  - Pour chaque page, decide automatiquement comment l'extraire en fonction de son contenu :
      * Si la page contient du vraie texte/ texte "natif" (du vrai texte, pas une image)
        -> extraction directe du texte + detection des tableaux via leur
        structure (lignes/colonnes visibles dans le PDF).
      * Si la page est en realite une image scannee ce qui fait que le texte n'est pas selectionable 
      ->  donc on utilise l'OCR pour "lire" le texte sur l'image, et reconstituer les tableaux a partir de l'image aussi.
  - Colle tout le texte de la page (avec un marqueur "[PAGE X]" pour
    savoir d'ou vient chaque passage), et sauvegarde le resultat complet
    dans un fichier .txt, dans le dossier "textes/" dans mon folder.




"""

import fitz            # PyMuPDF - lecture du texte natif des PDF
import pdfplumber       # detection de tableaux sur du texte natif
import pytesseract      # pont Python vers le moteur OCR Tesseract
from pdf2image import convert_from_path   # convertit une page PDF en image
import os               # manipulation de fichiers/dossiers (module standard Python)
import re               # expressions regulieres (module standard Python)
import time             # mesure du temps ecoule (module standard Python)
from config_sources import SOURCES   # notre dictionnaire de documents (voir config_sources.py)

# img2table : detection de tableaux + OCR combines, specifiquement pour
# les pages SCANNEES (images), contrairement a pdfplumber qui ne marche
# que sur du texte natif.
from img2table.document import PDF as PDF_Img2Table
from img2table.ocr import TesseractOCR



# Configuration -chemins et parametres a adapter a mon ordi


# Cree le dossier "textes" s'il n'existe pas deja. exist_ok=True veut dire
# "si le dossier existe deja, ne pas generer d'erreur, continue simplement"
# indispensable car  relance ce script plusieurs fois.
os.makedirs("textes", exist_ok=True)

# pytesseract's path vers le vrai programme Tesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# img2table, lui, cherche "tesseract" directement dans la variable
# d'environnement PATH du systeme 
os.environ["PATH"] += os.pathsep + r"C:\Program Files\Tesseract-OCR"

# Chemin vers le dossier "bin" de Poppler, necessaire a convert_from_path()
# pour transformer une scan PDF en vrai image.
POPPLER_PATH = r"C:\Users\Wahaya\ANSD-python-project\poppler-26.02.0\Library\bin"

# Lorsque le nombre de caracteres alphanumeriques utiles sur une page est inferireur a un certain nombre/seuil
# on considere que c'est probablement un scan  plutot que du texte selectionable
#  du coup on bascule sur l'OCR seulement pour cette page.
SEUIL_CARACTERES_PAGE = 40

# Resolution (en DPI, points par pouce) utilisee pour convertir une page
# suspecte (scan pdf) en image avant l'OCR. Plus ce chiffre est haut, plus l'image
# est nette (meilleure precision OCR), mais en contrepartit plus c'est lent et lourd.
# 300 est un bon compromis standard pour du texte imprime.
DPI_OCR = 300

# Un seul moteur OCR partage (instance de TesseractOCR), reutilise par
# toutes les pages scannees du script c inutile d'en recreer un a chaque
# fois, c'est le meme outil qui sert a lire le contenu de chaque cellule
# de tableau detectee par img2table.
moteur_ocr_tableaux = TesseractOCR(lang="fra")




def caracteres_utiles(texte):
    """
    Compte uniquement les caracteres "utiles" d'un texte : lettres(majuscules comme miniscules)
    (y compris les  accents francais , ex: e, e, a, c) et chiffres

    les espaces, sauts de ligne, ponctuation isolee ne compte pas et sont donc ignores

 fitz.get_text() peut parfois renvoyer
quelques espaces ou caracteres parasites  a une nouvelle page
donc ceci permet de s'assurer de compter compter que  les caracteres utiles 
et donne une mesure plus fiable pour decider si une page contient du
    texte reel ou non.

    """
    return len(re.sub(r"[^a-zA-Z0-9À-ÿ]", "", texte))


def tableau_vers_markdown(lignes_cellules):
    """
    Convertit un tableau represente en Python comme une liste de
    lignes, chaque ligne etant elle-meme une liste de cellules (du texte)
     en une chaine de caracteres au format Markdown, le format de
    tableau standard utilise par de nombreux outils texte est :

        | Region | Hommes | Femmes |
        | --- | --- | --- |
        | Dakar | 45.2 | 52.1 |

    

    On remplace les cellules vides / valeur None en Python  ce qui arrive
    frequemment quand une cellule de tableau est reellement vide dans le
    document source) par une chaine vide "" plutot que d'ecrire
    litteralement le mot "None" dans le texte final, ce qui polluerait
    inutilement le contexte envoye plus tard au chatbot.
    """
    if not lignes_cellules or len(lignes_cellules) == 0:
        return ""

    lignes_md = []

    # La premiere ligne de la liste devient l'en-tete du tableau Markdown.
    entete = [str(c) if c is not None else "" for c in lignes_cellules[0]]
    lignes_md.append("| " + " | ".join(entete) + " |")
    # Ligne de separation obligatoire en Markdown, une case "---" par colonne.
    lignes_md.append("| " + " | ".join(["---"] * len(entete)) + " |")

    # Toutes les lignes suivantes deviennent les lignes de donnees du tableau.
    for ligne in lignes_cellules[1:]:
        cellules = [str(c) if c is not None else "" for c in ligne]
        lignes_md.append("| " + " | ".join(cellules) + " |")

    return "\n".join(lignes_md)


def extraire_tableaux_page_native(chemin_pdf, numero_page_0_index):
    """
    Extrait les tableaux d'UNE PAGE, via pdfplumber -- utilisable
    UNIQUEMENT sur les pages qui contiennent du texte NATIF (pas une
    image scannee), car pdfplumber a besoin d'analyser la structure du
    texte reellement present dans le PDF.

    numero_page_0_index : pdfplumber compte ses pages a partir de 0 (la
    premiere page du PDF est la page 0), contrairement a fitz qui, dans
    la boucle principale plus bas, compte a partir de 1 -- d'ou le nom
    explicite du parametre, pour eviter toute confusion au moment de
    l'appel.

    page.extract_tables() est la methode fournie par pdfplumber qui fait
    tout le travail de detection : elle analyse les traits/alignements de
    la page et renvoie directement une liste de tableaux trouves, chacun
    deja sous forme de liste de lignes/cellules, on n'a plus qu'a les
    convertir en Markdown via notre fonction tableau_vers_markdown().
    """
    tableaux_markdown = []
    try:
        with pdfplumber.open(chemin_pdf) as pdf:
            page = pdf.pages[numero_page_0_index]
            for tableau in page.extract_tables():
                md = tableau_vers_markdown(tableau)
                if md:
                    tableaux_markdown.append(md)
    except Exception as erreur:
        print(f"     Erreur avec pdfplumber page {numero_page_0_index + 1} : {erreur}")
    return tableaux_markdown


def extraire_tableaux_page_scannee(chemin_pdf, numero_page_1_index):
    
    #Extrait les tableaux d'une page scannee /image, via img2table en addition a l'OCR.


   
    tableaux_markdown = []
    try:
        doc = PDF_Img2Table(src=chemin_pdf, pages=[numero_page_1_index - 1])
        resultats = doc.extract_tables(
            ocr=moteur_ocr_tableaux,
            implicit_rows=False,
            borderless_tables=True,
        )
        # les resultat est un dictionnaire {numero_de_page: [liste_de_tableaux]}
        # on parcourt tous les tableaux trouves sur cette page.
        for tableaux_de_la_page in resultats.values():
            for tableau in tableaux_de_la_page:
                df = tableau.df
                lignes_cellules = [list(df.columns)] + df.values.tolist()
                md = tableau_vers_markdown(lignes_cellules)
                if md:
                    tableaux_markdown.append(md)
    except Exception as erreur:
        print(f"    Erreur avec img2table page {numero_page_1_index} : {erreur}")
    return tableaux_markdown


def ocr_page(chemin_pdf, numero_page_1_index):
    """
    Extrait le TEXTE (pas les tableaux, juste le texte "normal") d'UNE
    PAGE SCANNEE, via OCR classique.

    1.  convert_from_path(...) : transforme cette page precise du
    PDF en une image (comme une capture d'ecran de cette page), a la
    resolution DPI_OCR. first_page et last_page, tous les deux fixes a la
    meme valeur, permettent de ne convertir que cette page-la, plutot que
    tout le PDF d'un coup 
    ce qui serait tres lent sur un document de
    plusieurs dizaines de pages.
     Le resultat est une liste d'images (une
    seule ici, vu qu'on n'a demande qu'une page)  d'ou images[0]
    juste apres.

    2.  pytesseract.image_to_string(...) : c'est ici que la
    "lecture" a proprement parler se produit. Tesseract regarde l'image
    et reconnait visuellement les caracteres qu'elle contient,  puis renvoie le texte reconnu sous forme de chaine
    de caracteres Python. lang="fra" indique d'utiliser le modele de
    reconnaissance francais (important pour bien reconnaitre les accents).
    """
    images = convert_from_path(
        chemin_pdf,
        dpi=DPI_OCR,
        first_page=numero_page_1_index,
        last_page=numero_page_1_index,
        poppler_path=POPPLER_PATH,
    )
    if not images:
        return ""
    return pytesseract.image_to_string(images[0], lang="fra")



# Boucle Principale qui traite chaque PDF  de la liste dans config_sources.py


for nom_fichier in SOURCES.keys():
    print(f"\nLecture de : {nom_fichier}")
    debut_traitement = time.time()   # pour mesurer la duree totale a la fin

    # fitz.open() ouvre le fichier PDF et renvoie un objet "document" qui
    # represente l'ensemble du PDF, page par page  c'est le point
    # d'entree de PyMuPDF pour manipuler un PDF en Python.
    document = fitz.open(nom_fichier)

    texte_complet = ""     # accumule tout le texte du document, page apres page
    nb_pages_ocr = 0        # compteur : combien de pages ont necessite l'OCR
    nb_tableaux_total = 0   # compteur : combien de tableaux detectes au total

    # enumerate(document, start=1) parcourt chaque page du document, en
    # donnant a la fois le numero de la page (a partir de 1, comme un
    # humain compterait les pages) et l'objet "page" lui-meme.
    for numero_page, page in enumerate(document, start=1):

        # page.get_text() extrait tout le texte selectionable 
        # parcontre si la page est une image scannee, ceci
        #renverra une chaine vide ou quasi vide.
        texte_page = page.get_text()

        # si le nombres de caracteres est inferieur au seuil definit on basculer sur l'OCR 
        if caracteres_utiles(texte_page) < SEUIL_CARACTERES_PAGE:
            # Page probablement scannee (image) : on utilise l'OCR pour le
            # texte, et img2table pour les eventuels tableaux de cette page.
            print(f"  page {numero_page} : texte insuffisant -> OCR texte + tableaux en cours...")
            texte_page = ocr_page(nom_fichier, numero_page)
            nb_pages_ocr += 1
            tableaux = extraire_tableaux_page_scannee(nom_fichier, numero_page)
        else:
            # Page avec texte natif exploitable : on utilise pdfplumber
            # pour detecter d'eventuels tableaux structures.
            tableaux = extraire_tableaux_page_native(nom_fichier, numero_page - 1)

        nb_tableaux_total += len(tableaux)

        # On assemble les tableaux trouves (s'il y en a) en un bloc de
        # texte Markdown, avec un marqueur indiquant leur origine.
        bloc_tableaux = ""
        if tableaux:
            bloc_tableaux = "\n\n" + "\n\n".join(
                f"[TABLEAU {i+1} PAGE {numero_page}]\n{md}"
                for i, md in enumerate(tableaux)
            )

        # On ajoute le texte de cette page (+ ses tableaux eventuels) au
        # texte complet du document, precede d'un marqueur "[PAGE X]" pour
        # garder une trace de l'origine de chaque passage.
        texte_complet += f"\n\n[PAGE {numero_page}]\n{texte_page}{bloc_tableaux}"

    # On ferme le document PDF proprement une fois toutes les pages lues
    #  libere la memoire/le fichier
    document.close()

    # On construit le nom du fichier .txt de sortie a partir du nom du
    # PDF, en remplacant simplement l'extension ".pdf" par ".txt".
    nom_txt = nom_fichier.replace(".pdf", ".txt")
    chemin_txt = os.path.join("textes", nom_txt)

    # On ecrit le texte complet extrait dans ce fichier .txt,
    # encoding="utf-8" pour gerer correctement les accents francais.
    with open(chemin_txt, "w", encoding="utf-8") as f:
        f.write(texte_complet)

    duree = time.time() - debut_traitement
    print(f"  -> Texte sauvegardé dans : {chemin_txt} ({len(texte_complet)} caractères)")
    print(f"  -> {nb_tableaux_total} tableau(x) détecté(s) au total")
    if nb_pages_ocr > 0:
        print(f"  -> {nb_pages_ocr} page(s) traitée(s) par OCR (sur {numero_page} au total) en {duree:.1f}s")
    else:
        print(f"  -> Aucune page n'a nécessité l'OCR ({duree:.1f}s)")

print("\nTerminé. ")
