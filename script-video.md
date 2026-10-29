# Script vidéo : 3 minutes

**Avant d'enregistrer**
- n8n ouvert sur le workflow, identifiants branchés, déjà testé une fois.
- Google Sheet ouvert sur l'onglet *Leads*, **vidé** (en-têtes seulement), onglet *Alertes* vidé aussi.
- Terminal ouvert dans le dossier, police grossie (Ctrl + molette).
- Trois fenêtres côte à côte ou en alternance (Alt+Tab) : n8n, Sheet, terminal.
- **Workflow activé** pour enchaîner sans cliquer : `python send_test_lead.py N --prod`. Pour voir le parcours s'allumer en vert, utiliser plutôt le mode test (*Execute workflow*, puis envoi sans `--prod`).
- Outil d'enregistrement : Win + G (Xbox Game Bar) ou OBS. Micro testé.

---

## 0:00 – 0:20 · Le problème (20 s)

**À l'écran :** le mail d'exemple Habitat Presto (`test-leads/01-exemple-officiel.txt` ou dans Gmail).

> « Le pôle travaux de Month'immo reçoit jusqu'à deux leads par jour d'Habitat Presto, par mail. Si personne ne les saisit à la main, ils n'existent nulle part : pas de suivi, pas de relance, des clients perdus. J'ai construit un workflow qui transforme chaque mail en ligne de suivi, automatiquement. »

## 0:20 – 1:00 · Le workflow (40 s)

**À l'écran :** le workflow entier dans n8n, puis zoom sur chaque bloc en le survolant.

> « Deux entrées : Gmail, qui surveille le label Habitat Presto, et un webhook pour la démo.
> Ensuite, une IA, Mistral, extrait les informations : nom, téléphone, email, ville, type de travaux, budget, délai. Il est à température zéro, avec un schéma JSON strict : si une info manque, il répond null, il n'invente rien. S'il échoue, il réessaie une fois, puis le mail brut part dans les alertes.
> Un nœud de nettoyage met le téléphone au format +33, les budgets en nombres, le délai en mois. Ce code est testé à part.
> Puis deux contrôles : le lead est-il complet ? est-ce un doublon ? Et l'écriture dans Google Sheets. »

## 1:00 – 1:45 · Démo : lead normal (45 s)

**À l'écran :** terminal → `python send_test_lead.py 1` → n8n (exécution verte) → Sheet.

> « J'envoie le lead d'exemple. »
*(lancer la commande)*
> « Le parcours passe au vert. Dans le Sheet, la ligne est là : Mme Claire D., téléphone au format +33, Saint-Chamond, département 42, salle de bain, budget 8 000 à 12 000 euros, délai 3 mois. Statut "Nouveau", et en prochaine action "Appeler sous 24 h". »

**Montrer** la colonne Statut avec sa liste déroulante, et dire : « Si personne ne rappelle dans les 24 heures, la ligne passe en rouge. »

*Option si le temps le permet :* `python send_test_lead.py 2`, le format très différent, extrait aussi correctement.

## 1:45 – 2:10 · Démo : lead incomplet (25 s)

**À l'écran :** `python send_test_lead.py 3` → Sheet onglet *Leads* → onglet *Alertes*.

> « Ce lead n'a ni téléphone, ni email, ni budget. Il n'est pas perdu pour autant : la ligne est créée en "À compléter", avec ce qui manque. Et une alerte est écrite dans l'onglet Alertes. Un lead n'est jamais ignoré en silence. »

## 2:10 – 2:35 · Démo : doublon (25 s)

**À l'écran :** `python send_test_lead.py 4` puis `python send_test_lead.py 5` → Sheet (pas de nouvelle ligne, *Nb de demandes* = 3) → *Alertes*.

> « Même cliente, deux fois : d'abord le même mail, puis une demande de rappel formulée autrement, avec juste le numéro écrit sans espaces. Pas de nouvelle ligne : le compteur passe à 3 et la date de dernière demande est mise à jour. Cliente motivée, à rappeler en priorité. »

## 2:35 – 3:00 · Adoption et mesure (25 s)

**À l'écran :** `note-adoption.md` ou le Sheet sur l'appli mobile (si possible, filmer le téléphone).

> « Pour le conducteur de travaux, zéro saisie : il change seulement le statut depuis son téléphone. Je le forme en 15 minutes sur un vrai lead, on teste deux semaines, puis on ajuste ensemble.
> On mesure : 100 % des leads enregistrés, premier contact en moins de 24 heures, et la conversion de lead à devis, puis à chantier signé. Tout se calcule directement dans le Sheet. Merci. »

---

**Après l'enregistrement :** couper les blancs, vérifier que la durée est inférieure à 3:00, exporter en MP4.
