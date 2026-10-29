// Test rapide du nettoyage, sans dépendance : node src/nettoyage.test.js
const assert = require('node:assert/strict');
const n = require('./nettoyage');

let ok = 0;
function test(nom, fn) {
  try { fn(); ok++; console.log(`  ✓ ${nom}`); } catch (e) { console.error(`  ✗ ${nom}\n    ${e.message}`); process.exitCode = 1; }
}

const mail = (id) => ({ subject: 'Nouveau projet', body: '...', received_at: '2026-10-29T08:12:00Z', message_id: id, source: 'Habitat Presto (test webhook)' });

// Ce que l'IA renvoie pour chaque mail de test-leads/ (même schéma que le Structured Output Parser).
const IA = {
  exemple: { nom: 'Mme Claire D.', telephone: '06 12 34 56 78', email: 'claire.d@exemple.fr', ville: 'Saint-Chamond', code_postal: null, departement: '42',
    type_travaux: 'salle de bain', description: 'Rénovation salle de bain complète (douche à l\'italienne, carrelage, meuble vasque)',
    budget_min: 8000, budget_max: 12000, delai_texte: 'sous 3 mois', delai_mois: 3 },
  autreFormat: { nom: 'M. Karim Haddad', telephone: '+33 (0)7 81 45 22 90', email: 'K.Haddad@Exemple.com', ville: 'Saint-Étienne', code_postal: '42100', departement: null,
    type_travaux: 'cuisine', description: 'Remplacement complet de la cuisine', budget_min: '15k€', budget_max: '20 000 €', delai_texte: 'dans 6 semaines', delai_mois: 1.5 },
  incomplet: { nom: 'M. Julien P.', telephone: null, email: null, ville: 'Firminy', code_postal: null, departement: '42',
    type_travaux: 'isolation', description: 'Isolation des combles perdus, environ 70 m²', budget_min: null, budget_max: null, delai_texte: 'dès que possible', delai_mois: 0 },
  memeTelephone: { nom: 'Claire Durand', telephone: '0612345678', email: null, ville: 'Saint-Chamond', code_postal: null, departement: null,
    type_travaux: 'Salle de bains', description: 'Demande de rappel pour sa salle de bains', budget_min: null, budget_max: '12 000 euros', delai_texte: "avant l'été", delai_mois: 8 },
  toiture: { nom: 'Famille Ribeiro', telephone: '04 77 31 08 64', email: 'ribeiro.famille@exemple.org', ville: 'Rive-de-Gier', code_postal: '42800', departement: null,
    type_travaux: 'Toiture', description: 'Réfection de la couverture et des gouttières', budget_min: 20000, budget_max: 25000, delai_texte: 'au printemps 2027', delai_mois: 5 },
};

console.log('Nettoyage des leads');

test('téléphone au format +33', () => {
  assert.equal(n.normaliserTelephone('06 12 34 56 78'), '+33612345678');
  assert.equal(n.normaliserTelephone('+33 (0)7 81 45 22 90'), '+33781452290');
  assert.equal(n.normaliserTelephone('0033 6 12 34 56 78'), '+33612345678');
  assert.equal(n.normaliserTelephone('06.12.34.56.78'), '+33612345678');
  assert.equal(n.normaliserTelephone('12 34'), null);
  assert.equal(n.formaterTelephone('+33612345678'), '+33 6 12 34 56 78');
});

test('email en minuscules, invalide -> null', () => {
  assert.equal(n.normaliserEmail(' K.Haddad@Exemple.com '), 'k.haddad@exemple.com');
  assert.equal(n.normaliserEmail('non renseigné'), null);
  assert.equal(n.normaliserEmail('claire.d@'), null);
});

test('budgets en nombres', () => {
  assert.equal(n.parserBudget('8 000 €'), 8000);
  assert.equal(n.parserBudget('15k€'), 15000);
  assert.equal(n.parserBudget('12.000 euros'), 12000);
  assert.equal(n.parserBudget(12000), 12000);
  assert.equal(n.parserBudget('non communiqué'), null);
});

test('délai en mois', () => {
  assert.equal(n.calculerDelaiMois('sous 3 mois'), 3);
  assert.equal(n.calculerDelaiMois('Démarrage souhaité : dans 6 semaines'), 1.4);
  assert.equal(n.calculerDelaiMois('entre 2 et 4 mois'), 4);
  assert.equal(n.calculerDelaiMois('dès que possible'), 0);
  assert.equal(n.calculerDelaiMois("avant l'été", 8), 8); // l'IA a estimé, on garde sa valeur
  assert.equal(n.calculerDelaiMois(null, null), null);
});

test('lead officiel : complet, statut Nouveau', () => {
  const r = n.nettoyerLead(IA.exemple, mail('m1'));
  assert.equal(r.complet, true);
  assert.equal(r.ligne.Statut, 'Nouveau');
  assert.equal(r.ligne['Téléphone'], '+33 6 12 34 56 78');
  assert.equal(r.ligne['Département'], '42');
  assert.equal(r.ligne['Type de travaux'], 'salle de bain');
  assert.equal(r.ligne['Budget min (€)'], 8000);
  assert.equal(r.ligne['Budget max (€)'], 12000);
  assert.equal(r.ligne['Délai (mois)'], 3);
  assert.equal(r.ligne['Date de réception'], '2026-10-29 09:12');
  assert.match(r.ligne.ID, /^HP-20261029-[0-9A-Z]{6}$/);
  assert.equal(r.alerte, null);
});

test('autre format : département depuis le code postal, budget "15k€"', () => {
  const r = n.nettoyerLead(IA.autreFormat, mail('m2'));
  assert.equal(r.ligne.Email, 'k.haddad@exemple.com');
  assert.equal(r.ligne['Département'], '42');
  assert.equal(r.ligne['Budget min (€)'], 15000);
  assert.equal(r.ligne['Délai (mois)'], 1.4);
  assert.equal(r.ligne.Statut, 'Nouveau');
});

test('lead incomplet : statut À compléter + alerte, jamais ignoré', () => {
  const r = n.nettoyerLead(IA.incomplet, mail('m3'));
  assert.equal(r.complet, false);
  assert.equal(r.ligne.Statut, 'À compléter');
  assert.deepEqual(r.champs_manquants, ['téléphone ou email']);
  assert.equal(r.alerte.Type, 'Lead incomplet');
  assert.match(r.ligne['Prochaine action'], /Compléter : téléphone ou email/);
});

test('sortie IA vide : tout est manquant mais la ligne existe', () => {
  const r = n.nettoyerLead({}, mail('m4'));
  assert.deepEqual(r.champs_manquants, ['nom', 'téléphone ou email', 'type de travaux']);
  assert.equal(r.ligne.Statut, 'À compléter');
});

test('type de travaux ramené à une catégorie', () => {
  assert.equal(n.categoriserTravaux('Salle de bains'), 'salle de bain');
  assert.equal(n.categoriserTravaux('Rénovation salle de bain complète'), 'salle de bain');
  assert.equal(n.categoriserTravaux('Rénovation complète appartement'), 'rénovation complète');
  assert.equal(n.categoriserTravaux('Isolation des combles'), 'isolation');
  assert.equal(n.categoriserTravaux('Peinture'), 'autre');
  assert.equal(n.categoriserTravaux(null), null);
});

test('doublons : même téléphone écrit autrement, même email, ou nouveau', () => {
  const sheet = [{ ID: 'HP-20261029-AAAAAA', 'Téléphone': '+33 6 12 34 56 78', Email: 'claire.d@exemple.fr', 'Nb de demandes': 1 }];
  const exact = n.nettoyerLead(IA.exemple, mail('m5'));
  assert.equal(n.trouverDoublon(exact, sheet).critere, 'téléphone');
  const tel = n.nettoyerLead(IA.memeTelephone, mail('m6'));
  assert.equal(n.trouverDoublon(tel, sheet).ligne.ID, 'HP-20261029-AAAAAA');
  const parEmail = n.nettoyerLead({ ...IA.autreFormat, telephone: null, email: 'Claire.D@exemple.fr' }, mail('m7'));
  assert.equal(n.trouverDoublon(parEmail, sheet).critere, 'email');
  assert.equal(n.trouverDoublon(n.nettoyerLead(IA.toiture, mail('m8')), sheet), null);
  assert.equal(n.trouverDoublon(n.nettoyerLead(IA.incomplet, mail('m9')), sheet), null);
  assert.equal(n.trouverDoublon(exact, []), null);
});

test('même mail = même ID (rejouer un mail ne crée pas un nouvel ID)', () => {
  assert.equal(n.genererLeadId('abc', '2026-10-29T08:00:00Z'), n.genererLeadId('abc', '2026-10-29T08:00:00Z'));
  assert.notEqual(n.genererLeadId('abc', '2026-10-29T08:00:00Z'), n.genererLeadId('abd', '2026-10-29T08:00:00Z'));
});

console.log(process.exitCode ? '\nÉCHEC' : `\n${ok} tests OK`);
