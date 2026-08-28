import os
import re
import numpy as np
import chromadb
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config_sources import SOURCES, LIENS_UTILES

MODELE_EMBEDDING = "nomic-embed-text"

# Longueur minimale (caracteres utiles) sous laquelle un chunk est ignore
# avant l'embedding - evite les "embeddings vides ou quasi-vides".
LONGUEUR_MIN_CHUNK_UTILE = 25

# Documents dont le texte natif est propre et suffisant :
# on utilise le decoupage recursif, rapide et suffisant. 
#Tous les autres PDF du dictionnaire SOURCES (issus de l'OCR) ainsi que les txt. files des sites scrappes 
# utiliseront le decoupage semantique 
SOURCES_TEXTE_NATIF = {"doc1.pdf", "doc2.pdf"}

# Parametres du decoupage semantique
TAILLE_MAX_CHUNK_SEMANTIQUE = 800    # comparable a taille_chunk du recursif
SEUIL_SIMILARITE_SEMANTIQUE = 0.55   #  si on est en dessous -> alors on considere que le sujet change


#  Decoupeur recursif (LangChain), utilise pour le texte natif propre 
splitter_recursif = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)



# DECOUPAGE SEMANTIQUE


def embedding_de_phrase(phrase):
    """Calcule l'embedding d'une seule phrase, renvoye comme tableau numpy
    (plus pratique pour les calculs de similarite qui suivent)."""
    reponse = ollama.embeddings(model=MODELE_EMBEDDING, prompt=phrase)
    return np.array(reponse["embedding"])


def similarite_cosinus(vecteur_a, vecteur_b):
    """cos(theta) entre deux vecteurs - voir la formule detaillee deja
    expliquee : produit scalaire divise par le produit des normes."""
    norme_a = np.linalg.norm(vecteur_a)
    norme_b = np.linalg.norm(vecteur_b)
    if norme_a == 0 or norme_b == 0:
        return 0.0
    return float(np.dot(vecteur_a, vecteur_b) / (norme_a * norme_b))


# FILET DE SECURITE -- decoupage force des "phrases" anormalement longues
# (ajoute suite a l'erreur "the input length exceeds the context length"
# rencontree sur doc6.pdf : un texte OCR de mauvaise qualite, presque sans
# ponctuation reconnue, fait que re.split() renvoie parfois TOUT le texte
# comme une seule "phrase", bien trop longue pour etre embeddee d'un coup.)

# Longueur maximale (en caracteres) qu'une "phrase" est autorisee a avoir
# avant d'etre decoupee de force. Marge de securite large par rapport a
# la limite reelle du modele.
TAILLE_MAX_PHRASE_AVANT_DECOUPE_FORCEE = 1500


def _decouper_si_trop_long(phrase, taille_max=TAILLE_MAX_PHRASE_AVANT_DECOUPE_FORCEE):
    """
    Si une "phrase" (obtenue apres le decoupage par ponctuation) est plus
    longue que taille_max, on la decoupe de force en morceaux plus
    petits, en coupant aux ESPACES les plus proches de la limite --
    jamais en plein milieu d'un mot.

    Si la phrase est deja assez courte, elle est renvoyee telle quelle
    dans une liste a un seul element -- cette fonction ne change donc
    rien au comportement normal sur un texte bien ponctue.
    """
    if len(phrase) <= taille_max:
        return [phrase]

    morceaux = []
    debut = 0
    while debut < len(phrase):
        fin_visee = debut + taille_max
        if fin_visee >= len(phrase):
            morceaux.append(phrase[debut:].strip())
            break
        position_espace = phrase.rfind(" ", debut, fin_visee)
        if position_espace == -1 or position_espace <= debut:
            position_espace = fin_visee
        morceau = phrase[debut:position_espace].strip()
        if morceau:
            morceaux.append(morceau)
        debut = position_espace + 1

    return morceaux


def decouper_semantiquement(texte, taille_max=TAILLE_MAX_CHUNK_SEMANTIQUE,
                             seuil_similarite=SEUIL_SIMILARITE_SEMANTIQUE):
    """
    Regroupe les phrases du texte en chunks selon leur PROXIMITE DE SENS,
    pas selon leur position typographique.

    Principe :
      1. On decoupe le texte en phrases individuelles (regex sur la
         ponctuation de fin de phrase).
      2. On calcule l'embedding de CHAQUE phrase.
      3. On parcourt les phrases dans l'ordre. Pour chaque nouvelle
         phrase, on compare son embedding a l'embedding MOYEN du chunk en
         cours de construction :
           - si la similarite reste HAUTE (>= seuil) ET que la taille
             maximale n'est pas depassee -> on ajoute la phrase au chunk
             actuel (meme sujet, on continue) ;
           - sinon -> on ferme le chunk actuel et on en commence un
             nouveau avec cette phrase (changement de sujet detecte, ou
             chunk deja assez grand).

    L'embedding "moyen" du chunk est recalcule a chaque ajout de phrase
    (moyenne courante), ce qui represente le "sens global" du chunk en
    cours plutot que de ne comparer qu'a la toute derniere phrase seule
    (plus stable face a des variations mineures de formulation).
    """
    phrases_brutes = [p.strip() for p in re.split(r'(?<=[.!?])\s+', texte) if p.strip()]

    # Filet de securite : toute "phrase" trop longue (texte OCR sans
    # ponctuation) est redecoupee ici, avant meme d'etre embeddee.
    phrases = []
    for p in phrases_brutes:
        phrases.extend(_decouper_si_trop_long(p))

    if len(phrases) == 0:
        return []
    if len(phrases) == 1:
        return phrases

    embeddings_phrases = [embedding_de_phrase(p) for p in phrases]

    chunks = []
    chunk_phrases = [phrases[0]]
    embedding_moyen_chunk = embeddings_phrases[0]
    taille_chunk_actuel = len(phrases[0])

    for i in range(1, len(phrases)):
        phrase = phrases[i]
        embedding_phrase = embeddings_phrases[i]

        sim = similarite_cosinus(embedding_moyen_chunk, embedding_phrase)
        depasse_taille_max = taille_chunk_actuel + len(phrase) > taille_max
        changement_de_sujet = sim < seuil_similarite

        if depasse_taille_max or changement_de_sujet:
            # On ferme le chunk en cours, on en commence un nouveau
            chunks.append(" ".join(chunk_phrases))
            chunk_phrases = [phrase]
            embedding_moyen_chunk = embedding_phrase
            taille_chunk_actuel = len(phrase)
        else:
            # Meme sujet, on continue a remplir le chunk actuel
            chunk_phrases.append(phrase)
            n = len(chunk_phrases)
            # Moyenne courante : integre la nouvelle phrase au "sens
            # global" du chunk sans avoir a tout recalculer depuis zero.
            embedding_moyen_chunk = (embedding_moyen_chunk * (n - 1) + embedding_phrase) / n
            taille_chunk_actuel += len(phrase)

    if chunk_phrases:
        chunks.append(" ".join(chunk_phrases))

    return chunks


#  Choix du decoupage en foncton source - choisit automatiquement recursif ou semantique


def decouper_texte(texte, nom_source_pdf=None, est_web=False):
    """
    Point d'entree unique utilise par le reste du script, decide, selon
    la source, quelle methode de decoupage appliquer :
      - nom_source_pdf fourni ET present dans SOURCES_TEXTE_NATIF
            -> decoupage RECURSIF (structure typographique fiable)
      - nom_source_pdf fourni mais issu de l'OCR (pas dans la liste),
        OU est_web=True
            -> decoupage SEMANTIQUE (structure typographique non fiable)
    """
    if est_web:
        return decouper_semantiquement(texte)

    if nom_source_pdf is not None and nom_source_pdf in SOURCES_TEXTE_NATIF:
        return splitter_recursif.split_text(texte)

    # PDF issu de l'OCR (ou cas non precise) -> semantique par defaut
    return decouper_semantiquement(texte)


def chunk_est_utile(morceau):
    """Filtre de qualite avant embedding : rejette les chunks quasi-vides
    (ex: artefacts de mise en page, pages blanches mal OCRisees)."""
    caracteres_utiles = len(re.sub(r"[^a-zA-Z0-9À-ÿ]", "", morceau))
    return caracteres_utiles >= LONGUEUR_MIN_CHUNK_UTILE



# INDEXATION DANS CHROMADB


client_chroma = chromadb.PersistentClient(path="./base_vecteurs")

try:
    client_chroma.delete_collection(name="ansd_unifie")
except Exception:
    pass

collection = client_chroma.get_or_create_collection(
    name="ansd_unifie",
    metadata={"hnsw:space": "cosine"},
)

compteur_id = 0
compteur_chunks_ignores = 0


def indexer_morceau(morceau, metadata):
    global compteur_id, compteur_chunks_ignores

    if not chunk_est_utile(morceau):
        compteur_chunks_ignores += 1
        return

    reponse = ollama.embeddings(model=MODELE_EMBEDDING, prompt=morceau)
    vecteur = reponse["embedding"]

    compteur_id += 1
    identifiant = f"chunk_{compteur_id}"

    collection.add(
        ids=[identifiant],
        embeddings=[vecteur],
        documents=[morceau],
        metadatas=[metadata],
    )


print("=== Indexation des PDF ===")
for nom_pdf, infos in SOURCES.items():
    nom_txt = nom_pdf.replace(".pdf", ".txt")
    chemin_txt = os.path.join("textes", nom_txt)

    if not os.path.exists(chemin_txt):
        print(f"  !! Fichier introuvable, ignoré : {chemin_txt} (as-tu lancé 1_extraire_pdf.py ?)")
        continue

    methode = "recursif" if nom_pdf in SOURCES_TEXTE_NATIF else "sémantique"
    print(f"\nTraitement de : {nom_pdf} ({infos['titre']}) -- méthode : {methode}")

    with open(chemin_txt, "r", encoding="utf-8") as f:
        texte = f.read()

    morceaux = decouper_texte(texte, nom_source_pdf=nom_pdf)
    print(f"  -> {len(morceaux)} morceaux créés (avant filtrage qualité)")

    avant = compteur_chunks_ignores
    for morceau in morceaux:
        indexer_morceau(morceau, {
            "type_source": "pdf",
            "titre": infos["titre"],
            "editeur": infos["editeur"],
            "annee": infos["annee"],
            "lien": infos["lien"],
        })
    ignores_ce_doc = compteur_chunks_ignores - avant

    print(f"  -> Embeddings créés et stockés pour {nom_pdf}"
          + (f" ({ignores_ce_doc} chunk(s) ignoré(s) car quasi-vides)" if ignores_ce_doc else ""))

    if len(morceaux) > 0 and ignores_ce_doc / len(morceaux) > 0.5:
        print(f"  warning:  plus de 50% des chunks de {nom_pdf} ont été ignorés.")
        print(" most likely un probleme au niveau de l'extraction de ce document")



# PARTIE B : PAGES WEB (toujours en decoupage semantique)

print("\n=== Indexation des pages web (découpage sémantique) ===")

noms_par_lien = {source["lien"]: source["nom"] for source in LIENS_UTILES}
fichiers_web = [f for f in os.listdir("textes") if f.startswith("web_") and f.endswith(".txt")]

if not fichiers_web:
    print("   Aucun fichier web_*.txt trouvé dans ./textes/. ")

for nom_fichier in fichiers_web:
    chemin_txt = os.path.join("textes", nom_fichier)
    print(f"\nTraitement de : {nom_fichier}")

    with open(chemin_txt, "r", encoding="utf-8") as f:
        contenu = f.read()

    lignes = contenu.split("\n", 3)
    lien_original = ""
    for ligne in lignes:
        if ligne.startswith("[LIEN: "):
            lien_original = ligne.replace("[LIEN: ", "").rstrip("]")
            break

    texte_seul = contenu.split("\n\n", 1)[1] if "\n\n" in contenu else contenu

    if len(texte_seul.strip()) < 300:
        print(f"  ! Contenu très court ({len(texte_seul.strip())} caractères) - donc source ignorée.")
        continue

    morceaux = decouper_texte(texte_seul, est_web=True)
    print(f"  -> {len(morceaux)} morceaux créés")

    nom_source = noms_par_lien.get(lien_original, lien_original or nom_fichier)

    for morceau in morceaux:
        indexer_morceau(morceau, {
            "type_source": "web",
            "titre": nom_source,
            "editeur": "Source web",
            "annee": "consulté via scraping",
            "lien": lien_original,
        })

    print(f"  -> Embeddings créés et stockés pour {nom_fichier}")


print(f"\nTerminé. {compteur_id} morceaux vectorisés et stockés "
      f"({compteur_chunks_ignores} chunk(s) ignoré(s) au total car quasi-vides).")
print("Base de données sauvegardée dans ./base_vecteurs (collection 'ansd_unifie').")