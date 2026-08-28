
# import ollama
# import chromadb
# import time
# from config_sources import SOURCES, LIENS_UTILES
 
# MODELE_EMBEDDING = "nomic-embed-text"
# # TEST DE VITESSE : on repasse temporairement sur llama3.2 (plus leger que
# # llama3.1:8b) pour confirmer si la lenteur vient de la taille du modele.
# # Si les reponses redeviennent rapides avec ce modele, le probleme est
# # confirme : la machine n'a pas assez de RAM/CPU pour faire tourner
# # confortablement le modele 8B en local.
# MODELE_CHAT = "llama3.2"
# NOMBRE_ECHANGES_EN_MEMOIRE = 3
 
# # REDUIT temporairement pour diminuer la quantite de texte envoyee au
# # modele a chaque question -- moins de texte = generation plus rapide.
# # N_RESULTATS_TOTAL remplace les deux anciens parametres separes
# # (N_RESULTATS_PDF / N_RESULTATS_WEB) : on demande directement les N
# # meilleurs resultats TOUS TYPES CONFONDUS, classes par distance.
# N_RESULTATS_TOTAL = 4
 
# MARQUEUR_SOURCES = "SOURCES_UTILISEES:"
 
# # temperature basse = le modele suit les instructions plus fidelement,
# # quitte a etre un peu moins "creatif" -- exactement ce qu'on veut ici
# # (fidelite au contexte > style).
# OPTIONS_GENERATION = {"temperature": 0.1}
 
 
# class ChatEngine:
#     def __init__(self):
#         client_chroma = chromadb.PersistentClient(path="./base_vecteurs")
#         self.collection = client_chroma.get_or_create_collection(
#             name="ansd_unifie",
#             metadata={"hnsw:space": "cosine"},
#         )
#         self.historique = []
 
#     # ------------------------------------------------------------
#     def construire_bloc_historique(self):
#         if not self.historique:
#             return ""
#         derniers = self.historique[-NOMBRE_ECHANGES_EN_MEMOIRE:]
#         lignes = []
#         for echange in derniers:
#             lignes.append(f"Q: {echange['question']}")
#             lignes.append(f"R: {echange['reponse']}")
#         return "\n".join(lignes)
 
#     # ------------------------------------------------------------
#     def classifier_question(self, question):
#         """
#         Appel LLM court et focalise, dedie uniquement a decider si la
#         question est liee aux statistiques/genre/ANSD ou si elle est
#         banale/hors-sujet -- separe de la generation pour plus de
#         fiabilite avec un modele local.
#         """
#         prompt_classification = f"""Réponds UNIQUEMENT par un seul mot : PERTINENT ou BANALE.
 
# La question suivante porte-t-elle sur les statistiques, le genre, l'emploi, la démographie,
# la santé, l'éducation, ou plus généralement sur des données que produit un institut national
# de statistique (ANSD) ? Ou est-ce une question banale/hors-sujet (salutation, culture
# générale, calcul, question personnelle sur toi-même) ?
 
# Question : "{question}"
 
# Réponds uniquement par PERTINENT ou BANALE, rien d'autre."""
 
#         debut = time.time()
 
#         reponse = ollama.chat(
#             model=MODELE_CHAT,
#             messages=[{"role": "user", "content": prompt_classification}],
#             options=OPTIONS_GENERATION,
#         )
#         duree = time.time() - debut
#         print(f"[diagnostic] classifier_question() : {duree:.1f}s")
#         texte = reponse["message"]["content"].strip().upper()
#         return "PERTINENT" in texte
 
#     # ------------------------------------------------------------
#     def rechercher(self, question):
#         """
#         Recherche UNIFIEE, sans distinction PDF/web -- on interroge la
#         collection entiere (pas de "where" par type_source), et ChromaDB
#         renvoie directement les N meilleurs resultats TOUS TYPES CONFONDUS,
#         classes par distance croissante (le plus proche du sens de la
#         question en premier, peu importe qu'il vienne d'un rapport ANSD
#         ou d'une page web).
 
#         C'est le changement demande : on n'impose plus que les rapports
#         ANSD passent toujours avant le web -- c'est la PROXIMITE REELLE
#         de sens qui decide, pas la source d'origine.
#         """
#         debut = time.time()
#         embedding_question = ollama.embeddings(model=MODELE_EMBEDDING, prompt=question)["embedding"]
#         print(f"[diagnostic] embedding de la question : {time.time() - debut:.1f}s")
 
#         resultats = self.collection.query(
#             query_embeddings=[embedding_question],
#             n_results=N_RESULTATS_TOTAL,
#             include=["documents", "metadatas", "distances"],
#         )
 
#         morceaux = resultats["documents"][0] if resultats["documents"] else []
#         metadatas = resultats["metadatas"][0] if resultats["metadatas"] else []
#         distances = resultats["distances"][0] if resultats["distances"] else []
 
#         # Affichage diagnostic : pour chaque resultat, sa distance ET son
#         # origine (pdf/web) -- utile pour voir concretement, dans ta
#         # console, que le classement melange bien les deux types selon la
#         # distance reelle, sans favoriser un type par defaut.
#         for m, meta, d in zip(morceaux, metadatas, distances):
#             print(f"[diagnostic] distance={d:.3f}  type={meta['type_source']}  titre={meta['titre'][:50]}")
 
#         return morceaux, metadatas
 
#     # ------------------------------------------------------------
#     def construire_contexte(self, morceaux, metadatas):
#         """
#         Construit le contexte comme une liste UNIQUE de fragments, deja
#         classes par pertinence (le plus proche en premier).
 
#         IMPORTANT : le titre entre crochets doit rester EXACTEMENT
#         identique au titre stocke dans les metadonnees (m['titre']),
#         car le modele est charge de le RECOPIER TEL QUEL dans la ligne
#         SOURCES_UTILISEES -- toute modification ici (ex: ajouter le type
#         de source) casse la correspondance exacte utilisee ensuite pour
#         filtrer les sources reellement utilisees (voir
#         extraire_reponse_et_sources_utilisees). Le type de source reste
#         visible dans les metadonnees (meta['type_source']) sans avoir
#         besoin d'etre affiche dans le titre lui-meme.
#         """
#         blocs = [f"[{m['titre']}]\n{t}" for t, m in zip(morceaux, metadatas)]
#         if not blocs:
#             return "(aucun extrait trouve)"
#         return "\n\n---\n\n".join(blocs)
 
#     # ------------------------------------------------------------
#     def formater_sources(self, metadatas):
#         vues = set()
#         sources_formatees = []
#         for meta in metadatas:
#             cle = (meta["titre"], meta["lien"])
#             if cle not in vues:
#                 vues.add(cle)
#                 sources_formatees.append({
#                     "type": meta["type_source"],
#                     "titre": meta["titre"],
#                     "editeur": meta["editeur"],
#                     "annee": meta["annee"],
#                     "lien": meta["lien"],
#                 })
#         return sources_formatees
 
#     # ------------------------------------------------------------
#     def extraire_reponse_et_sources_utilisees(self, texte_brut):
#         if MARQUEUR_SOURCES not in texte_brut:
#             return texte_brut.strip(), None
 
#         reponse_finale, partie_sources = texte_brut.rsplit(MARQUEUR_SOURCES, 1)
#         reponse_finale = reponse_finale.strip()
 
#         titres_utilises = [t.strip() for t in partie_sources.split(";") if t.strip()]
#         titres_utilises = [t for t in titres_utilises if t.lower() not in ("aucune", "aucun", "none")]
 
#         return reponse_finale, titres_utilises
 
#     # ------------------------------------------------------------
#     def repondre_question_banale(self, question):
#         """
#         Repond a une question banale/hors-sujet. La phrase de redirection
#         vers l'ANSD est AJOUTEE PAR LE CODE PYTHON, pas generee par le
#         modele -- ca elimine tout risque que le modele invente une URL
#         (comme "ansd.sr" au lieu de "ansd.sn", deja observe) ou une
#         formulation trompeuse. Le modele ne repond qu'a la question
#         elle-meme, rien d'autre.
#         """
#         prompt = f"""Tu es l'assistant du Gender Data Lab du Sénégal.
 
# Réponds directement et brièvement à cette question banale/générale, avec tes
# connaissances générales. Ne mentionne PAS l'ANSD, aucun lien, ni aucune phrase
# de redirection -- cela sera ajouté automatiquement après ta réponse.
 
# Question : {question}
 
# Réponse :"""
 
#         reponse = ollama.chat(
#             model=MODELE_CHAT,
#             messages=[{"role": "user", "content": prompt}],
#             options=OPTIONS_GENERATION,
#         )
#         texte_reponse = reponse["message"]["content"].strip()
 
#         # Phrase de redirection FIXE (jamais generee par le modele) --
#         # texte exact demande : une invitation naturelle a poser une
#         # question sur le sujet du chatbot, sans lien invente.
#         texte_final = (
#             f"{texte_reponse}\n\n"
#             "À présent, comment puis-je répondre à vos questions "
#             "sur les statistiques de genre au Sénégal ?"
#         )
 
#         self.historique.append({"question": question, "reponse": texte_final})
 
#         return {"reponse": texte_final, "sources": []}
 
#     # ------------------------------------------------------------
#     def repondre_question_pertinente(self, question):
#         bloc_historique = self.construire_bloc_historique()
#         morceaux, metadatas = self.rechercher(question)
#         contexte = self.construire_contexte(morceaux, metadatas)
 
#         aucun_extrait_pertinent = (len(morceaux) == 0)
 
#         prompt = f"""Tu es l'assistant du Gender Data Lab du Sénégal.
 
# Cette question porte sur les statistiques/genre/ANSD. Les extraits ci-dessous sont
# CLASSES PAR PERTINENCE : le premier extrait est celui dont le sens est le plus proche
# de la question, peu importe qu'il provienne d'un rapport ANSD ou d'un site web.
 
# 1. Utilise en priorité l'extrait (ou les extraits) qui répond le mieux à la question,
#    quelle que soit sa source d'origine (rapport ANSD ou site web) -- ce n'est pas la
#    source qui decide, c'est la pertinence reelle du contenu par rapport a la question.
# 2. Relis ATTENTIVEMENT chaque extrait un par un avant de conclure -- l'information peut
#    se trouver dans n'importe lequel des extraits, pas seulement le premier.
# 3. Si aucun extrait ne contient l'information demandée, dis-le CLAIREMENT, par exemple :
#    "Je n'ai pas trouvé cette information dans les documents disponibles." NE TENTE JAMAIS
#    de deviner ou d'improviser une réponse dans ce cas.
# {"[ATTENTION] Fait vérifié côté système : aucun extrait n'a été trouvé pour cette question. Applique le point 3 ci-dessus." if aucun_extrait_pertinent else ""}
 
# Autres règles :
# - Réponds UNIQUEMENT à partir du contexte ci-dessous. Ne l'invente jamais.
# - N'invente JAMAIS la signification d'un sigle (ex: ENR-VFFS) s'il n'est pas explicité
#   dans le contexte : garde le sigle tel quel.
# - N'invente JAMAIS le nom d'une enquête ou d'un rapport qui n'apparaît pas explicitement
#   dans le contexte ci-dessous.
# - Donne les statistiques PAR GENRE (homme/femme) quand disponible. Si un seul genre est
#   disponible, donne-le et précise clairement l'absence de données pour l'autre.
# - Si plusieurs extraits donnent des chiffres différents sur le même sujet, signale-le
#   explicitement plutôt que de n'en choisir qu'un sans le dire.
# - Ne mentionne PAS de nom de fichier dans ta réponse.
 
# =======================================================
# RÈGLE OBLIGATOIRE SUR LES SOURCES :
# À la TOUTE FIN de ta réponse, sur une NOUVELLE LIGNE, ajoute EXACTEMENT :
 
# SOURCES_UTILISEES: titre_exact_1; titre_exact_2
 
# en recopiant tel quel le titre entre crochets [ ] des SEULS extraits réellement utilisés.
# Si aucun extrait n'a été utilisé, écris exactement : SOURCES_UTILISEES: aucune
# =======================================================
 
# Échanges précédents (pour contexte, si pertinent) :
# {bloc_historique if bloc_historique else "(aucun échange précédent)"}
 
# Contexte (classé par pertinence) :
# {contexte}
 
# Question : {question}
 
# Réponse :"""
 
#         debut_generation = time.time()
#         reponse = ollama.chat(
#             model=MODELE_CHAT,
#             messages=[{"role": "user", "content": prompt}],
#             options=OPTIONS_GENERATION,
#         )
#         print(f"[diagnostic] génération de la réponse : {time.time() - debut_generation:.1f}s "
#               f"(longueur du prompt envoyé : {len(prompt)} caractères)")
#         texte_brut = reponse["message"]["content"]
 
#         texte_reponse, titres_utilises = self.extraire_reponse_et_sources_utilisees(texte_brut)
 
#         toutes_metadonnees = metadatas
 
#         if titres_utilises is None:
#             # CORRECTION IMPORTANTE : si le modele a completement omis la
#             # ligne "SOURCES_UTILISEES:" (peut arriver avec un petit modele
#             # local qui ne respecte pas toujours parfaitement le format
#             # demande), on ne peut PAS savoir avec certitude quels fragments
#             # ont reellement ete utilises pour construire la reponse.
#             #
#             # Dans ce cas, on choisit de n'afficher AUCUNE source plutot que
#             # de les afficher toutes -- afficher tout reviendrait a montrer
#             # des "sources consultees" comme si elles etaient des "sources
#             # utilisees", ce qui serait trompeur pour l'utilisateur (voir
#             # exigence : uniquement les sources reellement mobilisees dans
#             # la reponse, jamais l'ensemble de ce qui a ete recupere).
#             metadonnees_retenues = []
#         elif len(titres_utilises) == 0:
#             metadonnees_retenues = []
#         else:
#             titres_normalises = {t.lower() for t in titres_utilises}
#             metadonnees_retenues = [
#                 m for m in toutes_metadonnees if m["titre"].lower() in titres_normalises
#             ]
 
#         indices_aucune_info = [
#             "je n'ai pas trouvé", "n'ai pas trouvé cette information",
#             "aucune information", "ne figure pas dans", "pas d'information disponible",
#             "je ne dispose pas de cette information", "n'a pas cette information",
#         ]
#         reponse_normalisee = texte_reponse.lower()
#         if any(indice in reponse_normalisee for indice in indices_aucune_info):
#             metadonnees_retenues = []
 
#         sources = self.formater_sources(metadonnees_retenues)
 
#         self.historique.append({"question": question, "reponse": texte_reponse})
 
#         return {"reponse": texte_reponse, "sources": sources}
 
#     # ------------------------------------------------------------
#     def repondre(self, question):
#         est_pertinente = self.classifier_question(question)
 
#         if est_pertinente:
#             return self.repondre_question_pertinente(question)
#         else:
#             return self.repondre_question_banale(question)
 
#     # ------------------------------------------------------------
#     def reinitialiser(self):
#         self.historique = []
 
 
# def lister_sources_disponibles():
#     sources = []
#     for infos in SOURCES.values():
#         sources.append({
#             "type": "pdf",
#             "titre": infos["titre"],
#             "editeur": infos["editeur"],
#             "annee": infos["annee"],
#             "lien": infos["lien"],
#         })
#     for source in LIENS_UTILES:
#         sources.append({
#             "type": "web",
#             "titre": source["nom"],
#             "editeur": "Source web",
#             "annee": "",
#             "lien": source["lien"],
#         })
#     return sources
 




import ollama
import chromadb
import time
from config_sources import SOURCES, LIENS_UTILES
 
MODELE_EMBEDDING = "nomic-embed-text"
# test de vitesse : on repasse temporairement sur llama3.2 (plus leger que
# llama3.1:8b) pour confirmer si la lenteur vient de la taille du modele.
# Si les reponses redeviennent rapides avec ce modele, le probleme est
# confirme ma machine n'a pas assez de RAM/CPU pour faire tourner
# confortablement le modele 8B en local.
MODELE_CHAT = "llama3.2"
NOMBRE_ECHANGES_EN_MEMOIRE = 3
 
# N_RESULTATS_TOTAL : nombre de resultats demandes a ChromaDB, TOUS TYPES

N_RESULTATS_TOTAL = 4
 
# Seuils de distance 
# un fragment n'est retenu que si sa distance a la question reste inferieure a son seuil (different selon
# qu'il provient d'un rapport PDF ou d'une page web
SEUIL_DISTANCE_PDF = 0.45
SEUIL_DISTANCE_WEB = 0.35
 
MARQUEUR_SOURCES = "SOURCES_UTILISEES:"
 
# temperature basse = le modele suit les instructions plus fidelement,
# quitte a etre un peu moins "creatif"  exactement ce qu'on veut ici
# on priorise la fidelite au contexte.
OPTIONS_GENERATION = {"temperature": 0.1}
 
 
class ChatEngine:
    def __init__(self):
        client_chroma = chromadb.PersistentClient(path="./base_vecteurs")
        self.collection = client_chroma.get_or_create_collection(
            name="ansd_unifie",
            metadata={"hnsw:space": "cosine"},
        )
        self.historique = []
 
    # ------------------------------------------------------------
    def construire_bloc_historique(self):
        if not self.historique:
            return ""
        derniers = self.historique[-NOMBRE_ECHANGES_EN_MEMOIRE:]
        lignes = []
        for echange in derniers:
            lignes.append(f"Q: {echange['question']}")
            lignes.append(f"R: {echange['reponse']}")
        return "\n".join(lignes)
 
    # ------------------------------------------------------------
    def classifier_question(self, question):
     
        #Appel LLM court et focalise, dedie uniquement a decider si la question est liee aux statistiques/genre/ANSD ou si elle est
        #banale/hors-sujet  separe de la generation pour plus de fiabilite avec un modele local.
        
        prompt_classification = f"""Réponds UNIQUEMENT par un seul mot : PERTINENT ou BANALE.
 
La question suivante porte-t-elle sur les statistiques, le genre, l'emploi, la démographie,
la santé, l'éducation, ou plus généralement sur des données que produit un institut national
de statistique (ANSD) ? Ou est-ce une question banale/hors-sujet (salutation, culture
générale, calcul, question personnelle sur toi-même) ?
 
Question : "{question}"
 
Réponds uniquement par PERTINENT ou BANALE, rien d'autre."""
 
        debut = time.time()
 
        reponse = ollama.chat(
            model=MODELE_CHAT,
            messages=[{"role": "user", "content": prompt_classification}],
            options=OPTIONS_GENERATION,
        )
        duree = time.time() - debut
        print(f"[diagnostic] classifier_question() : {duree:.1f}s")
        texte = reponse["message"]["content"].strip().upper()
        return "PERTINENT" in texte
 
    # ------------------------------------------------------------
    def rechercher(self, question):
        """
        Recherche sans distinction PDF/web on interroge la
        collection entiere (pas de "where" par type_source), et ChromaDB
        renvoie directement les N meilleurs resultats tous type de source confondu,
        classes par distance croissante (le plus proche du sens de la
        question en premier, peu importe qu'il vienne d'un rapport ANSD
        ou d'une page web) pas de hierarchie imposee entre les sources a cette etape.
 
        Un filtrage par seuil est ensuite applique sur cette liste deja
        fusionnee : chaque fragment n'est retenu que si sa distance reste
        sous le seuil correspondant a son type (PDF ou web). Cela evite de
        transmettre au modele des fragments trop eloignes du sens de la
        question, meme s'ils font partie des N meilleurs resultats bruts.
        """
        debut = time.time()
        embedding_question = ollama.embeddings(model=MODELE_EMBEDDING, prompt=question)["embedding"]
        print(f"[diagnostic] embedding de la question : {time.time() - debut:.1f}s")
 
        resultats = self.collection.query(
            query_embeddings=[embedding_question],
            n_results=N_RESULTATS_TOTAL,
            include=["documents", "metadatas", "distances"],
        )
 
        morceaux_bruts = resultats["documents"][0] if resultats["documents"] else []
        metadatas_brutes = resultats["metadatas"][0] if resultats["metadatas"] else []
        distances = resultats["distances"][0] if resultats["distances"] else []
 
        morceaux = []
        metadatas = []
        for m, meta, d in zip(morceaux_bruts, metadatas_brutes, distances):
            seuil_applicable = SEUIL_DISTANCE_PDF if meta["type_source"] == "pdf" else SEUIL_DISTANCE_WEB
            retenu = d <= seuil_applicable
 
            # Affichage diagnostic : pour chaque resultat, sa distance, son
            # origine (pdf/web), et si le seuil le retient ou le rejette 
            # utile pour voir  l'effet reel du filtrage.
            statut = "retenu" if retenu else f"rejete (seuil={seuil_applicable})"
            print(f"[diagnostic] distance={d:.3f}  type={meta['type_source']}  {statut}  titre={meta['titre'][:50]}")
 
            if retenu:
                morceaux.append(m)
                metadatas.append(meta)
 
        return morceaux, metadatas
 
    # ------------------------------------------------------------
    def construire_contexte(self, morceaux, metadatas):
        """
        Construit le contexte comme une liste unique de fragments, deja
        classes par pertinence (le plus proche en premier).
        """
 
        # NB : le titre entre crochets doit rester EXACTEMENT identique au titre stocke dans les metadonnees (m['titre']),
        #car le modele est charge de le recopier tel quel dans la ligne
       
        blocs = [f"[{m['titre']}]\n{t}" for t, m in zip(morceaux, metadatas)]
        if not blocs:
            return "(aucun extrait trouve)"
        return "\n\n---\n\n".join(blocs)
 
    # ------------------------------------------------------------
    def formater_sources(self, metadatas):
        vues = set()
        sources_formatees = []
        for meta in metadatas:
            cle = (meta["titre"], meta["lien"])
            if cle not in vues:
                vues.add(cle)
                sources_formatees.append({
                    "type": meta["type_source"],
                    "titre": meta["titre"],
                    "editeur": meta["editeur"],
                    "annee": meta["annee"],
                    "lien": meta["lien"],
                })
        return sources_formatees
 
    # ------------------------------------------------------------
    def extraire_reponse_et_sources_utilisees(self, texte_brut):
        if MARQUEUR_SOURCES not in texte_brut:
            return texte_brut.strip(), None
 
        reponse_finale, partie_sources = texte_brut.rsplit(MARQUEUR_SOURCES, 1)
        reponse_finale = reponse_finale.strip()
 
        titres_utilises = [t.strip() for t in partie_sources.split(";") if t.strip()]
        titres_utilises = [t for t in titres_utilises if t.lower() not in ("aucune", "aucun", "none")]
 
        return reponse_finale, titres_utilises
 
    # ------------------------------------------------------------
    def repondre_question_banale(self, question):
        """
        Repond a une question banale/hors-sujet. La phrase de redirection
        vers l'ANSD est ajoutee par le code python , et non plus genere par le modele
        """
        prompt = f"""Tu es l'assistant du Gender Data Lab du Sénégal.
 
Réponds directement et brièvement à cette question banale/hors-sujet/générale, avec tes
connaissances générales. Ne mentionne PAS l'ANSD, aucun lien, ni aucune phrase
de redirection, cela sera ajouté automatiquement après ta réponse.
 
Question : {question}
 
Réponse :"""
 
        reponse = ollama.chat(
            model=MODELE_CHAT,
            messages=[{"role": "user", "content": prompt}],
            options=OPTIONS_GENERATION,
        )
        texte_reponse = reponse["message"]["content"].strip()
 
        # Phrase de redirection FIXE (jamais generee par le modele) --
        # texte exact demande : une invitation naturelle a poser une
        # question sur le sujet du chatbot, sans lien invente.
        texte_final = (
            f"{texte_reponse}\n\n"
            "À présent, comment puis-je répondre à vos questions "
            "sur les statistiques de genre au Sénégal ?"
        )
 
        self.historique.append({"question": question, "reponse": texte_final})
 
        return {"reponse": texte_final, "sources": []}
 
    # ------------------------------------------------------------
    def repondre_question_pertinente(self, question):
        bloc_historique = self.construire_bloc_historique()
        morceaux, metadatas = self.rechercher(question)
        contexte = self.construire_contexte(morceaux, metadatas)
 
        aucun_extrait_pertinent = (len(morceaux) == 0)
 
        prompt = f"""Tu es l'assistant du Gender Data Lab du Sénégal.
 
Cette question porte sur les statistiques/genre/ANSD. Les extraits ci-dessous sont
classes par pertinence : le premier extrait est celui dont le sens est le plus proche
de la question, peu importe qu'il provienne d'un rapport ANSD ou d'un site web.
 
1. Utilise en priorité l'extrait (ou les extraits) qui répond le mieux à la question,
   quelle que soit sa source d'origine (rapport ANSD ou site web)  ce n'est pas la
   source qui decide, c'est la pertinence reelle du contenu par rapport a la question.
2. Relis ATTENTIVEMENT chaque extrait un par un avant de conclure, l'information peut
   se trouver dans n'importe lequel des extraits, pas seulement le premier.
3. Si aucun extrait ne contient l'information demandée, dis-le CLAIREMENT, par exemple :
   "Je n'ai pas trouvé cette information dans les documents disponibles." NE TENTE JAMAIS
   de deviner ou d'improviser une réponse dans ce cas.

Autres règles :
- Réponds UNIQUEMENT à partir du contexte ci-dessous. Ne l'invente jamais.
- N'invente JAMAIS la signification d'un sigle (ex: ENR-VFFS) s'il n'est pas explicité
  dans le contexte : garde le sigle tel quel.
- N'invente JAMAIS le nom d'une enquête ou d'un rapport qui n'apparaît pas explicitement
  dans le contexte ci-dessous.
- Donne les statistiques PAR GENRE (homme/femme) quand disponible. Si un seul genre est
  disponible, donne-le et précise clairement l'absence de données pour l'autre.
- Si plusieurs extraits donnent des chiffres différents sur le même sujet, signale-le
  explicitement plutôt que de n'en choisir qu'un sans le dire.
- Ne mentionne PAS de nom de fichier dans ta réponse.
 

 
Échanges précédents (pour contexte, si pertinent) :
{bloc_historique if bloc_historique else "(aucun échange précédent)"}
 
Contexte (classé par pertinence) :
{contexte}
 
Question : {question}
 
Réponse :"""
 
        debut_generation = time.time()
        reponse = ollama.chat(
            model=MODELE_CHAT,
            messages=[{"role": "user", "content": prompt}],
            options=OPTIONS_GENERATION,
        )
        print(f"[diagnostic] génération de la réponse : {time.time() - debut_generation:.1f}s "
              f"(longueur du prompt envoyé : {len(prompt)} caractères)")
        texte_brut = reponse["message"]["content"]
 
        texte_reponse, titres_utilises = self.extraire_reponse_et_sources_utilisees(texte_brut)
 
        toutes_metadonnees = metadatas
 
        if titres_utilises is None:
            # CORRECTION IMPORTANTE : si le modele a completement omis la
            # ligne "SOURCES_UTILISEES:" (peut arriver avec un petit modele
            # local qui ne respecte pas toujours parfaitement le format
            # demande), on ne peut pas savoir avec certitude quels fragments
            # ont reellement ete utilises pour construire la reponse.
            #
            # Dans ce cas, on choisit de n'afficher aucune source plutot que
            # de les afficher toutes  afficher tout reviendrait a montrer
            # des "sources consultees" comme si elles etaient des "sources
            # utilisees", ce qui serait trompeur pour l'utilisateur (voir
            # exigence : uniquement les sources reellement mobilisees dans
            # la reponse, jamais l'ensemble de ce qui a ete recupere).
            metadonnees_retenues = []
        elif len(titres_utilises) == 0:
            metadonnees_retenues = []
        else:
            titres_normalises = {t.lower() for t in titres_utilises}
            metadonnees_retenues = [
                m for m in toutes_metadonnees if m["titre"].lower() in titres_normalises
            ]
 
        indices_aucune_info = [
            "je n'ai pas trouvé", "n'ai pas trouvé cette information",
            "aucune information", "ne figure pas dans", "pas d'information disponible",
            "je ne dispose pas de cette information", "n'a pas cette information",
        ]
        reponse_normalisee = texte_reponse.lower()
        if any(indice in reponse_normalisee for indice in indices_aucune_info):
            metadonnees_retenues = []
 
        sources = self.formater_sources(metadonnees_retenues)
 
        self.historique.append({"question": question, "reponse": texte_reponse})
 
        return {"reponse": texte_reponse, "sources": sources}
 
    # ------------------------------------------------------------
    def repondre(self, question):
        est_pertinente = self.classifier_question(question)
 
        if est_pertinente:
            return self.repondre_question_pertinente(question)
        else:
            return self.repondre_question_banale(question)
 
    # ------------------------------------------------------------
    def reinitialiser(self):
        self.historique = []
 
 
def lister_sources_disponibles():
    sources = []
    for infos in SOURCES.values():
        sources.append({
            "type": "pdf",
            "titre": infos["titre"],
            "editeur": infos["editeur"],
            "annee": infos["annee"],
            "lien": infos["lien"],
        })
    for source in LIENS_UTILES:
        sources.append({
            "type": "web",
            "titre": source["nom"],
            "editeur": "Source web",
            "annee": "",
            "lien": source["lien"],
        })
    return sources
 




