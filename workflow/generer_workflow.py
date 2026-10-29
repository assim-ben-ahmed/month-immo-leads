"""Génère workflow/lead-habitat-presto.json à partir de src/nettoyage.js.

À relancer si vous modifiez src/nettoyage.js (le code testé par node src/nettoyage.test.js est ainsi
exactement celui qui tourne dans n8n), ou pour inscrire l'ID de votre Google Sheet avant l'import :

    python workflow/generer_workflow.py --sheet-id 1AbC...xyz
"""
import argparse
import json
import uuid
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
LIB = (RACINE / "src" / "nettoyage.js").read_text(encoding="utf-8")
SORTIE = RACINE / "workflow" / "lead-habitat-presto.json"

WEBHOOK_PATH = "lead-habitat-presto"
_parser = argparse.ArgumentParser(description="Génère le workflow n8n.")
_parser.add_argument("--sheet-id", default="COLLER_ICI_L_ID_DU_GOOGLE_SHEET",
                     help="ID du Google Sheet (la partie entre /d/ et /edit dans son URL)")
SHEET_ID = _parser.parse_args().sheet_id
MODELE_MISTRAL = "ministral-8b-latest"  # inclus dans l'offre gratuite de Mistral (contrairement à mistral-small)
CREDENTIAL_MISTRAL = {"mistralCloudApi": {"id": "mistralLeadsHP01", "name": "Mistral"}}
CREDENTIAL_SHEETS = {"googleSheetsOAuth2Api": {"id": "googleSheetsHP01", "name": "Google Sheets (Month'immo)"}}
CREDENTIAL_GMAIL = {"gmailOAuth2": {"id": "gmailHP01", "name": "Gmail (Month'immo)"}}

COLONNES_LEADS = ["ID", "Date de réception", "Nom", "Téléphone", "Email", "Ville", "Département", "Type de travaux",
                  "Description", "Budget min (€)", "Budget max (€)", "Délai (texte)", "Délai (mois)", "Statut",
                  "Responsable", "Date de 1er contact", "Prochaine action", "Nb de demandes", "Source", "ID du mail",
                  "Dernière demande"]
COLONNES_ALERTES = ["Date", "Type", "ID du lead", "Nom", "Détail", "Extrait du mail", "ID du mail"]
# Colonnes écrites telles quelles (nombres, dates). Les autres sont préfixées d'une apostrophe :
# Google Sheets les garde alors comme du texte (pas de formule injectée par un mail, "+33…" et "01" restent intacts).
NON_TEXTE = {"Date de réception", "Dernière demande", "Date", "Budget min (€)", "Budget max (€)", "Délai (mois)",
             "Nb de demandes"}


def uid():
    return str(uuid.uuid4())


SYSTEME = """Tu extrais les informations d'un mail de lead travaux envoyé par la plateforme Habitat Presto à Month'immo (rénovation, Saint-Étienne).

Règles :
- Recopie uniquement ce qui est écrit dans le mail. N'invente jamais rien. Si une information est absente, illisible ou « non communiquée », mets null.
- nom : tel qu'écrit, avec la civilité si elle est présente (ex. Mme Claire D.).
- telephone et email : tels qu'écrits. Une mention comme « à consulter dans votre espace » vaut null.
- ville : la commune du chantier, sans code postal. code_postal : 5 chiffres s'il est écrit, sinon null. departement : numéro de département s'il est écrit, par exemple 42, sinon null.
- type_travaux : une seule catégorie parmi : salle de bain, cuisine, toiture, isolation, rénovation complète, autre.
- description : résumé fidèle des travaux demandés, en une phrase.
- budget_min et budget_max : nombres en euros, sans espace ni symbole. « 8 000 à 12 000 € » donne 8000 et 12000. « environ 10 000 € » donne 10000 et 10000. « jusqu'à 12 000 € » ou « maximum 12 000 € » donne budget_min null et budget_max 12000.
- delai_texte : le délai souhaité tel qu'écrit. delai_mois : nombre de mois entre la date de réception et le démarrage souhaité (« sous 3 mois » donne 3, « dès que possible » donne 0 ; pour une saison ou un mois, estime à partir de la date de réception) ; null s'il n'y a aucun délai.
- Réponds uniquement avec l'objet JSON demandé."""

PROMPT = """=Objet du mail : {{ $json.subject }}
Reçu le : {{ $json.received_at }}

Corps du mail :
{{ $json.body }}"""


def champ(t, desc):
    return {"type": [t, "null"], "description": desc}


SCHEMA = {
    "type": "object",
    "properties": {
        "nom": champ("string", "Nom du particulier, avec civilité si présente"),
        "telephone": champ("string", "Téléphone tel qu'écrit"),
        "email": champ("string", "Email tel qu'écrit"),
        "ville": champ("string", "Commune du chantier"),
        "code_postal": champ("string", "Code postal à 5 chiffres"),
        "departement": champ("string", "Numéro de département"),
        "type_travaux": champ("string", "salle de bain, cuisine, toiture, isolation, rénovation complète ou autre"),
        "description": champ("string", "Résumé des travaux en une phrase"),
        "budget_min": champ("number", "Budget minimum en euros"),
        "budget_max": champ("number", "Budget maximum en euros"),
        "delai_texte": champ("string", "Délai souhaité tel qu'écrit"),
        "delai_mois": champ("number", "Délai en mois depuis la réception"),
    },
    "required": ["nom", "telephone", "email", "ville", "code_postal", "departement", "type_travaux", "description",
                 "budget_min", "budget_max", "delai_texte", "delai_mois"],
}

CODE_ENTREE = r"""// Ramène les deux déclencheurs au même format : { subject, body, received_at, message_id, source }
const html = (h) => String(h || '').replace(/<style[\s\S]*?<\/style>/gi, '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();

return $input.all().map((item) => {
  const j = item.json;
  if (j.body && typeof j.body === 'object') {
    // Webhook de démo (send_test_lead.py)
    const b = j.body;
    return { json: {
      subject: String(b.subject || ''),
      body: String(b.body || ''),
      received_at: b.received_at || new Date().toISOString(),
      message_id: b.message_id || `webhook-${Date.now()}`,
      source: 'Habitat Presto (test webhook)',
    } };
  }
  // Gmail Trigger (option "Simplify" désactivée)
  return { json: {
    subject: String(j.subject || ''),
    body: String(j.text || html(j.html) || j.snippet || ''),
    received_at: j.date ? new Date(j.date).toISOString() : new Date().toISOString(),
    message_id: j.id || j.messageId || `gmail-${Date.now()}`,
    source: 'Habitat Presto (Gmail)',
  } };
});"""

CODE_NETTOYAGE = LIB + r"""

// ---------- Exécution dans n8n ----------
const entrees = $('Entrée normalisée').all();
return $input.all().map((item, i) => {
  let mail;
  try { mail = $('Entrée normalisée').itemMatching(i).json; } catch (e) { mail = (entrees[i] || entrees[0]).json; }
  return { json: { ...nettoyerLead(item.json.output, mail), mail }, pairedItem: i };
});"""

CODE_DOUBLONS = LIB + r"""

// ---------- Exécution dans n8n ----------
// Entrée : toutes les lignes du Sheet (lu une seule fois). Les leads viennent du nœud Nettoyage.
const lignes = $input.all().map((i) => i.json).filter((r) => r && r.ID);
return $('Nettoyage').all().map((item, i) => {
  const lead = item.json;
  const trouve = trouverDoublon(lead, lignes);
  if (!trouve) {
    lignes.push({ ...lead.ligne }); // un 2e mail identique dans le même lot sera aussi vu comme doublon
    return { json: { ...lead, doublon: false }, pairedItem: 0 };
  }
  const existante = trouve.ligne;
  const nb = (parseInt(existante['Nb de demandes'], 10) || 1) + 1;
  existante['Nb de demandes'] = nb;
  return { json: {
    ...lead,
    doublon: true,
    maj: { ID: existante.ID, 'Nb de demandes': nb, 'Dernière demande': lead.ligne['Dernière demande'] },
    alerte: ligneAlerte('Doublon', { ...lead.ligne, ID: existante.ID },
      `Même ${trouve.critere} que ${existante.ID} : pas de nouvelle ligne, ${nb}e demande enregistrée.`, lead.mail),
  }, pairedItem: 0 };
});"""

CODE_ERREUR_IA = LIB + r"""

// ---------- Exécution dans n8n ----------
// L'IA a échoué deux fois (ou a renvoyé un JSON invalide) : on garde le mail brut dans Alertes.
const entrees = $('Entrée normalisée').all();
return $input.all().map((item, i) => {
  let mail;
  try { mail = $('Entrée normalisée').itemMatching(i).json; } catch (e) { mail = (entrees[i] || entrees[0] || { json: {} }).json; }
  const erreur = item.json.error ? (item.json.error.message || item.json.error) : JSON.stringify(item.json);
  return { json: { alerte: ligneAlerte('Erreur IA', null, `Extraction impossible après 2 essais : ${String(erreur).slice(0, 300)}. Lead à saisir à la main.`, mail) } };
});"""


def doc(sheet):
    return {
        "resource": "sheet",
        "documentId": {"__rl": True, "mode": "id", "value": SHEET_ID},
        "sheetName": {"__rl": True, "mode": "name", "value": sheet},
    }


def schema(cols):
    return [{"id": c, "displayName": c, "required": False, "defaultMatch": False, "display": True,
             "type": "string", "canBeUsedToMatch": True} for c in cols]


def valeur(objet, c, brut=False):
    ref = f'$json.{objet}["{c}"]'
    if brut or c in NON_TEXTE:  # brut : colonne de correspondance, comparée telle quelle (sans apostrophe)
        return f"={{{{ {ref} ?? '' }}}}"
    return f"={{{{ {ref} == null || {ref} === '' ? '' : \"'\" + {ref} }}}}"


def colonnes(objet, cols, matching=()):
    return {"mappingMode": "defineBelow", "value": {c: valeur(objet, c, brut=c in matching) for c in cols},
            "matchingColumns": list(matching), "schema": schema(cols)}


def node(name, type_, version, pos, params, **extra):
    n = {"parameters": params, "id": uid(), "name": name, "type": type_, "typeVersion": version, "position": list(pos)}
    n.update(extra)
    return n


def sticky(content, pos, w, h, color=7):
    return node(f"Note {uid()[:8]}", "n8n-nodes-base.stickyNote", 1, pos,
                {"content": content, "height": h, "width": w, "color": color})


def code(name, pos, js):
    return node(name, "n8n-nodes-base.code", 2, pos, {"jsCode": js})


def si(name, pos, gauche, operation):
    return node(name, "n8n-nodes-base.if", 2.2, pos, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": [{"id": uid(), "leftValue": gauche, "rightValue": "",
                            "operator": {"type": "boolean", "operation": operation, "singleValue": True}}],
            "combinator": "and",
        },
        "options": {},
    })


SHEETS = ("n8n-nodes-base.googleSheets", 4.7)
OPTIONS_ECRITURE = {"cellFormat": "USER_ENTERED"}

nodes = [
    node("Gmail : label Habitat Presto", "n8n-nodes-base.gmailTrigger", 1.3, (0, 0), {
        "pollTimes": {"item": [{"mode": "everyMinute"}]},
        "simple": False,
        "filters": {"labelIds": []},
        "options": {},
    }, credentials=CREDENTIAL_GMAIL),
    node("Webhook (démo)", "n8n-nodes-base.webhook", 2.1, (0, 220), {
        "httpMethod": "POST", "path": WEBHOOK_PATH, "responseMode": "onReceived", "options": {
            "responseData": "Lead reçu, traitement en cours."}}, webhookId=uid()),
    code("Entrée normalisée", (240, 110), CODE_ENTREE),
    node("Extraction IA", "@n8n/n8n-nodes-langchain.chainLlm", 1.7, (480, 110), {
        "promptType": "define",
        "text": PROMPT,
        "hasOutputParser": True,
        "messages": {"messageValues": [{"message": SYSTEME}]},
    }, retryOnFail=True, maxTries=2, waitBetweenTries=3000, onError="continueErrorOutput"),
    node("Modèle Mistral", "@n8n/n8n-nodes-langchain.lmChatMistralCloud", 1, (400, 340), {
        "model": MODELE_MISTRAL,
        "options": {"temperature": 0, "maxTokens": 1024, "maxRetries": 3},
    }, credentials=CREDENTIAL_MISTRAL),
    node("Format JSON strict", "@n8n/n8n-nodes-langchain.outputParserStructured", 1.3, (600, 340), {
        "schemaType": "manual", "inputSchema": json.dumps(SCHEMA, ensure_ascii=False, indent=2)}),
    code("Nettoyage", (800, 0), CODE_NETTOYAGE),
    node("Lire les leads existants", *SHEETS, (1020, 0), {
        "operation": "read", **doc("Leads"), "filtersUI": {}, "options": {}},
         executeOnce=True, alwaysOutputData=True, credentials=CREDENTIAL_SHEETS),
    code("Détection des doublons", (1240, 0), CODE_DOUBLONS),
    si("Doublon ?", (1460, 0), "={{ $json.doublon }}", "true"),
    node("Mettre à jour le lead existant", *SHEETS, (1720, -160), {
        "operation": "update", **doc("Leads"),
        "columns": colonnes("maj", ["ID", "Nb de demandes", "Dernière demande"], matching=["ID"]),
        "options": OPTIONS_ECRITURE}, credentials=CREDENTIAL_SHEETS),
    node("Ajouter le lead", *SHEETS, (1720, 80), {
        "operation": "append", **doc("Leads"), "columns": colonnes("ligne", COLONNES_LEADS),
        "options": OPTIONS_ECRITURE}, credentials=CREDENTIAL_SHEETS),
    si("Incomplet ?", (1720, 280), "={{ $json.complet }}", "false"),
    code("Préparer l'alerte erreur IA", (1720, 480), CODE_ERREUR_IA),
    node("Écrire dans Alertes", *SHEETS, (2000, 280), {
        "operation": "append", **doc("Alertes"), "columns": colonnes("alerte", COLONNES_ALERTES),
        "options": OPTIONS_ECRITURE}, credentials=CREDENTIAL_SHEETS),
]

notes = [
    sticky("## Leads Habitat Presto → Google Sheets\nChaque mail de lead devient une ligne de suivi. **Aucun lead n'est jamais perdu** : "
           "complet → statut *Nouveau* ; incomplet → *À compléter* + alerte ; doublon → compteur mis à jour + alerte ; "
           "échec de l'IA → mail brut dans l'onglet *Alertes*.\n\nRéglages : ID du Google Sheet dans les 4 nœuds Sheets, "
           "label Gmail dans le déclencheur, identifiants Google.", (-60, -420), 760, 220, 4),
    sticky("### 1. Déclencheurs\n**Gmail** : relève toutes les minutes les mails du label *Habitat Presto* (le vrai flux).\n"
           "**Webhook** : pour la démo, `python send_test_lead.py 1`.\nLes deux sont ramenés au même format "
           "(objet, corps, date, ID du mail).", (-60, -180), 460, 160),
    sticky("### 2. Extraction IA\nMistral, température 0, avec un **schéma JSON strict** (Structured Output Parser) : "
           "null si l'info manque, rien d'inventé.\nEn cas d'échec : **1 nouvel essai**, puis sortie *erreur* → alerte.\n"
           "Changer de modèle : remplacer *Modèle Mistral* par un autre nœud de modèle (OpenAI, Gemini, Ollama…).", (420, -180), 340, 220),
    sticky("### 3. Nettoyage (code testé)\nTéléphone en +33, email en minuscules, budgets en nombres, délai en mois, "
           "ID du lead, date de réception.\n**Validation** : nom + (téléphone ou email) + type de travaux, sinon "
           "*À compléter*.\nSource : `src/nettoyage.js`.", (780, -260), 400, 200),
    sticky("### 4. Doublons\nOn relit le Sheet et on compare le téléphone normalisé **ou** l'email.\n"
           "Doublon → pas de 2e ligne : *Nb de demandes* +1, *Dernière demande* mise à jour, alerte.", (1220, -260), 400, 160),
    sticky("### 5. Écriture\n*Nouveau* ou *À compléter* → onglet **Leads**.\nIncomplet, doublon ou erreur IA → onglet "
           "**Alertes** (avec l'extrait du mail).", (1700, -420), 400, 140),
]

ia = {"node": "Extraction IA", "type": "main", "index": 0}
alertes = {"node": "Écrire dans Alertes", "type": "main", "index": 0}
connexions = {
    "Gmail : label Habitat Presto": {"main": [[{"node": "Entrée normalisée", "type": "main", "index": 0}]]},
    "Webhook (démo)": {"main": [[{"node": "Entrée normalisée", "type": "main", "index": 0}]]},
    "Entrée normalisée": {"main": [[ia]]},
    "Modèle Mistral": {"ai_languageModel": [[{"node": "Extraction IA", "type": "ai_languageModel", "index": 0}]]},
    "Format JSON strict": {"ai_outputParser": [[{"node": "Extraction IA", "type": "ai_outputParser", "index": 0}]]},
    "Extraction IA": {"main": [[{"node": "Nettoyage", "type": "main", "index": 0}],
                               [{"node": "Préparer l'alerte erreur IA", "type": "main", "index": 0}]]},
    "Nettoyage": {"main": [[{"node": "Lire les leads existants", "type": "main", "index": 0}]]},
    "Lire les leads existants": {"main": [[{"node": "Détection des doublons", "type": "main", "index": 0}]]},
    "Détection des doublons": {"main": [[{"node": "Doublon ?", "type": "main", "index": 0}]]},
    "Doublon ?": {"main": [
        [{"node": "Mettre à jour le lead existant", "type": "main", "index": 0}, alertes],
        [{"node": "Ajouter le lead", "type": "main", "index": 0}, {"node": "Incomplet ?", "type": "main", "index": 0}],
    ]},
    "Incomplet ?": {"main": [[alertes], []]},
    "Préparer l'alerte erreur IA": {"main": [[alertes]]},
}

workflow = {
    "name": "Leads Habitat Presto → Google Sheets",
    "nodes": nodes + notes,
    "connections": connexions,
    "active": False,
    "settings": {"executionOrder": "v1", "timezone": "Europe/Paris"},
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False},
    "tags": [],
}

SORTIE.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Écrit : {SORTIE}")
