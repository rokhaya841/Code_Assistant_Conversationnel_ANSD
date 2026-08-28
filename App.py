

# import os
# import uuid
# from flask import Flask, render_template, request, jsonify, session
# from rag_engine import ChatEngine, lister_sources_disponibles

# app = Flask(__name__)

# # Necessaire pour que flask.session fonctionne (signature des cookies) --
# # une simple chaine fixe suffit pour un usage local, pas besoin de la
# # generer aleatoirement ici puisqu'il n'y a pas d'authentification a proteger.
# app.secret_key = "cle-locale-simple"

# # Dictionnaire central : cle = identifiant de session (texte genere via
# # uuid), valeur = instance de ChatEngine PROPRE a ce visiteur.
# moteurs_par_session = {}


# def obtenir_moteur_de_session():
#     """
#     Renvoie le ChatEngine associe au visiteur actuel, en le creant s'il
#     n'existe pas encore (premiere question de ce visiteur). C'est ce qui
#     garantit que 2 personnes qui utilisent le chatbot en meme temps ont
#     chacune leur propre historique de conversation, independant.
#     """
#     if "id_session" not in session:
#         session["id_session"] = str(uuid.uuid4())

#     id_session = session["id_session"]

#     if id_session not in moteurs_par_session:
#         moteurs_par_session[id_session] = ChatEngine()

#     return moteurs_par_session[id_session]


# @app.route("/")
# def accueil():
#     return render_template("index.html")


# @app.route("/api/sources")
# def api_sources():
#     return jsonify(lister_sources_disponibles())


# @app.route("/api/chat", methods=["POST"])
# def api_chat():
#     donnees = request.get_json(silent=True) or {}
#     question = (donnees.get("question") or "").strip()

#     if not question:
#         return jsonify({"erreur": "La question est vide."}), 400

#     moteur = obtenir_moteur_de_session()
#     resultat = moteur.repondre(question)
#     return jsonify(resultat)


# @app.route("/api/reset", methods=["POST"])
# def api_reset():
#     """Vide la memoire de conversation -- UNIQUEMENT celle du visiteur
#     actuel, pas celle des autres utilisateurs connectes en meme temps."""
#     moteur = obtenir_moteur_de_session()
#     moteur.reinitialiser()
#     return jsonify({"ok": True})


# if __name__ == "__main__":
#     from waitress import serve
#     print("Serveur démarré sur : http://127.0.0.1:5000")
#     serve(app, host="0.0.0.0", port=5000, threads=8)


import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from rag_engine import ChatEngine, lister_sources_disponibles
 
app = Flask(__name__)
 
# Necessaire pour que flask.session fonctionne (signature des cookies) --
# une simple chaine fixe suffit pour un usage local, pas besoin de la
# generer aleatoirement ici puisqu'il n'y a pas d'authentification a proteger.
app.secret_key = "cle-locale-simple"
 
# Dictionnaire central : cle = identifiant de session (texte genere via
# uuid), valeur = instance de ChatEngine PROPRE a ce visiteur.
moteurs_par_session = {}
 
 
def obtenir_moteur_de_session():
    """
    Renvoie le ChatEngine associe au visiteur actuel, en le creant s'il
    n'existe pas encore (premiere question de ce visiteur). C'est ce qui
    garantit que 2 personnes qui utilisent le chatbot en meme temps ont
    chacune leur propre historique de conversation, independant.
    """
    if "id_session" not in session:
        session["id_session"] = str(uuid.uuid4())
 
    id_session = session["id_session"]
 
    if id_session not in moteurs_par_session:
        moteurs_par_session[id_session] = ChatEngine()
 
    return moteurs_par_session[id_session]
 
 
@app.route("/")
def accueil():
    return render_template("index.html")
 
 
@app.route("/api/sources")
def api_sources():
    return jsonify(lister_sources_disponibles())
 
 
@app.route("/api/chat", methods=["POST"])
def api_chat():
    donnees = request.get_json(silent=True) or {}
    question = (donnees.get("question") or "").strip()
 
    if not question:
        return jsonify({"erreur": "La question est vide."}), 400
 
    moteur = obtenir_moteur_de_session()
    resultat = moteur.repondre(question)
    return jsonify(resultat)
 
 
@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Vide la memoire de conversation -- UNIQUEMENT celle du visiteur
    actuel, pas celle des autres utilisateurs connectes en meme temps."""
    moteur = obtenir_moteur_de_session()
    moteur.reinitialiser()
    return jsonify({"ok": True})
 
 
if __name__ == "__main__":
    from waitress import serve
    print("Serveur démarré sur : http://127.0.0.1:5000")
    serve(app, host="0.0.0.0", port=5000, threads=8)
 