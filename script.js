/* 
   SCRIPT.JS — LOGIQUE COTE NAVIGATEUR

   Ce fichier ne contient AUCUNE logique RAG (pas de prompt, pas de calcul de
   similarite) -- tout ca vit plutot du cote du serveur, dans rag_engine.py. Ici, on ne
   fait que 4 choses :
     1. Envoyer la question de l'utilisateur a /api/chat
     2. Afficher la reponse + les etiquettes de source recues
     3. Charger la liste des sources connues au demarrage (/api/sources)
     4. Faire tourner le ticker de questions suggerees (element signature)
    */


// QUESTIONS SUGGEREES POUR LE TICKER — a adapter librement selon
// les rapports reellement charges dans SOURCES (config_sources.py).
// Ce sont des points de depart pour l'utilisateur.

const QUESTIONS_SUGGEREES = [
  "Quel est le taux d'alphabétisation des femmes au Sénégal ?",
  "Que disent les rapports sur les violences basées sur le genre ?",
  "Compare les données ANSD et les sources web sur l'emploi des femmes",
  "Quelles sont les principales conclusions du rapport ENR-VFFS ?",

];

const fil = document.getElementById("thread");
const formulaire = document.getElementById("composer");
const champQuestion = document.getElementById("champ-question");
const boutonEnvoyer = document.getElementById("btn-send");
const indicateurEcriture = document.getElementById("thinking");
const boutonReset = document.getElementById("btn-reset");
const gabaritMessage = document.getElementById("gabarit-message-assistant");
const gabaritSource = document.getElementById("gabarit-source");


// ENVOI D'UNE QUESTION


async function envoyerQuestion(question) {
  ajouterMessageUtilisateur(question);
  champQuestion.value = "";
  redimensionnerChamp();
  basculerFormulaire(false);
  indicateurEcriture.hidden = false;
  fil.scrollTop = fil.scrollHeight;

  try {
    const reponseHTTP = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!reponseHTTP.ok) {
      const erreur = await reponseHTTP.json().catch(() => ({}));
      throw new Error(erreur.erreur || "Le serveur a renvoyé une erreur.");
    }

    const resultat = await reponseHTTP.json();
    ajouterMessageAssistant(resultat.reponse, resultat.sources || []);

  } catch (erreur) {
    // On affiche l'erreur DANS le fil de discussion plutot qu'une alerte
    // le navigateur  garde l'utilisateur dans le contexte de la conversation,
    // et explique en langage clair ce qui s'est passe et quoi faire.
    ajouterMessageAssistant(
      "Une erreur est survenue en contactant le serveur. Vérifiez qu'Ollama et le serveur Flask sont bien lancés, puis réessayez.",
      []
    );
    console.error(erreur);
  } finally {
    indicateurEcriture.hidden = true;
    basculerFormulaire(true);
    fil.scrollTop = fil.scrollHeight;
  }
}

function basculerFormulaire(actif) {
  champQuestion.disabled = !actif;
  boutonEnvoyer.disabled = !actif;
  if (actif) champQuestion.focus();
}

// AFFICHAGE DES MESSAGES

function ajouterMessageUtilisateur(texte) {
  const div = document.createElement("div");
  div.className = "msg msg-utilisateur";
  div.innerHTML = `
    <div class="msg-avatar">Vous</div>
    <div class="msg-body"><p></p></div>
  `;
  div.querySelector("p").textContent = texte;
  fil.appendChild(div);
  fil.scrollTop = fil.scrollHeight;
}

function ajouterMessageAssistant(texte, sources) {
  const noeud = gabaritMessage.content.cloneNode(true);
  noeud.querySelector(".msg-texte").textContent = texte;

  const conteneurSources = noeud.querySelector(".msg-sources");
  sources.forEach((source) => {
    const tag = gabaritSource.content.cloneNode(true);
    const lien = tag.querySelector(".source-tag");
    lien.href = source.lien || "#";
    lien.querySelector(".dot").classList.add(source.type === "pdf" ? "dot-pdf" : "dot-web");
    lien.querySelector(".source-tag-titre").textContent = source.titre;
    lien.title = `${source.titre}${source.annee ? " — " + source.annee : ""}`;
    conteneurSources.appendChild(tag);
  });

  fil.appendChild(noeud);
}


// PANNEAU LATERAL : chargement des sources connues au demarrage


async function chargerSources() {
  const listePDF = document.getElementById("liste-sources-pdf");
  const listeWeb = document.getElementById("liste-sources-web");

  try {
    const reponse = await fetch("/api/sources");
    const sources = await reponse.json();

    sources.forEach((source) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = source.lien || "#";
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = source.annee ? `${source.titre} (${source.annee})` : source.titre;
      li.appendChild(a);
      (source.type === "pdf" ? listePDF : listeWeb).appendChild(li);
    });
  } catch (erreur) {
    // Si le panneau de sources ne charge pas, ce n'est pas bloquant pour le chat lui-meme
    //  on le signale juste discretement en console.
    console.error("Impossible de charger la liste des sources :", erreur);
  }
}


// TICKER DE QUESTIONS SUGGEREES (element signature de la page)


let indexTicker = 0;
const boutonTicker = document.getElementById("ticker-question");

function afficherQuestionTicker() {
  boutonTicker.textContent = QUESTIONS_SUGGEREES[indexTicker];
}

function tournerTicker() {
  boutonTicker.classList.add("fading");
  setTimeout(() => {
    indexTicker = (indexTicker + 1) % QUESTIONS_SUGGEREES.length;
    afficherQuestionTicker();
    boutonTicker.classList.remove("fading");
  }, 250);
}

boutonTicker.addEventListener("click", () => {
  champQuestion.value = boutonTicker.textContent;
  redimensionnerChamp();
  champQuestion.focus();
});


// COMPORTEMENT DU CHAMP DE SAISIE

function redimensionnerChamp() {
  champQuestion.style.height = "auto";
  champQuestion.style.height = Math.min(champQuestion.scrollHeight, 160) + "px";
}

champQuestion.addEventListener("input", redimensionnerChamp);

champQuestion.addEventListener("keydown", (evenement) => {
  // Entree seule = envoyer ; Maj+Entree = nouvelle ligne (convention
  // standard des messageries, attendue par la plupart des utilisateurs).
  if (evenement.key === "Enter" && !evenement.shiftKey) {
    evenement.preventDefault();
    formulaire.requestSubmit();
  }
});

formulaire.addEventListener("submit", (evenement) => {
  evenement.preventDefault();
  const question = champQuestion.value.trim();
  if (!question || champQuestion.disabled) return;
  envoyerQuestion(question);
});


// BOUTON "NOUVELLE CONVERSATION"

boutonReset.addEventListener("click", async () => {
  try {
    await fetch("/api/reset", { method: "POST" });
  } catch (erreur) {
    console.error("Impossible de réinitialiser la mémoire côté serveur :", erreur);
  }
  // On vide aussi le fil visuellement, en remettant uniquement le message
  // d'accueil d'origine (au lieu de recharger toute la page).
  fil.innerHTML = "";
  const accueil = document.createElement("div");
  accueil.className = "msg msg-assistant";
  accueil.innerHTML = `
    <div class="msg-avatar">AD</div>
    <div class="msg-body">
      <p>Nouvelle conversation. Posez votre question sur les données genre de l'ANSD.</p>
    </div>
  `;
  fil.appendChild(accueil);
});


// INITIALISATION


chargerSources();
afficherQuestionTicker();
setInterval(tournerTicker, 6000);
redimensionnerChamp();
champQuestion.focus();
