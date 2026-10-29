# Suivi des leads travaux : adoption et mesure

## 1. Faire adopter le suivi par le conducteur de travaux

**Partir de son problème, pas de l'outil.** Aujourd'hui, un lead Habitat Presto qui arrive pendant qu'il est sur un chantier est oublié ou ressaisi le soir. Je lui présente l'outil comme ce qui règle ce problème, pas comme un tableau de plus à remplir.

**Zéro travail en plus.** Le tableau se remplit tout seul : nom, téléphone, travaux, budget, délai. Sa seule action est de changer le **Statut** (Contacté, Devis envoyé, Gagné, Perdu) depuis l'appli Google Sheets sur son téléphone, en deux touches. Tout ce qu'il ne remplira pas sur un chantier est automatisé.

**15 minutes de prise en main sur un vrai lead.** Pas de formation théorique : on ouvre ensemble le lead du jour sur son téléphone, il appelle le client et passe la ligne en « Contacté ». Je lui montre aussi les deux couleurs à surveiller : rouge (pas rappelé depuis 24 h) et orange (lead à compléter).

**Un récapitulatif chaque matin.** Un message à 8 h liste les nouveaux leads et ceux en rouge. Il n'a pas besoin d'ouvrir le tableau pour savoir qui rappeler.

**Deux semaines d'essai, puis on ajuste avec lui.** À la fin, un point de 20 minutes : quelles colonnes servent, lesquelles manquent, ce qui le gêne. Le tableau devient le sien, ce qui compte plus que n'importe quelle fonctionnalité.

## 2. Mesurer que ça marche

Tout se calcule dans le Google Sheet, sans outil en plus :

| Indicateur | Objectif | Calcul dans le Sheet |
|---|---|---|
| **Leads enregistrés** | 100 % (aujourd'hui : inconnu) | Lignes de *Leads* + alertes « Erreur IA », comparées au nombre de mails du label Gmail sur la période |
| **Délai de 1er contact** | < 24 h | Moyenne de *Date de 1er contact* − *Date de réception* ; nombre de lignes en rouge |
| **Statuts mis à jour** | > 90 % | Part des leads de plus de 48 h dont le statut n'est plus « Nouveau » |
| **Conversion** | à suivre dès le 1er mois | Devis envoyés ÷ leads, puis Gagnés ÷ devis (`NB.SI` sur *Statut*) |
| **Temps gagné** | ≈ 1 h par semaine | Nombre de leads × 5 min de saisie évitée |
| **Erreurs rattrapées** | à suivre | Nombre de lignes de l'onglet *Alertes* par type : incomplet, doublon, erreur IA |

**Point de départ.** Avant le lancement, je compte avec lui les mails Habitat Presto du dernier mois et ce qu'ils sont devenus. Ce chiffre de référence montre l'écart.

**Rythme.** Un bilan à deux semaines avec ces six chiffres, puis un bilan mensuel. Si un indicateur ne bouge pas, par exemple trop de lignes en rouge, on en cherche la cause avec lui avant d'ajouter une fonctionnalité.
