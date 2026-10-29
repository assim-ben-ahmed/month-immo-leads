// Nettoyage et contrôle des leads Habitat Presto.
// Ce fichier est copié tel quel dans les nœuds Code "Nettoyage" et "Détection des doublons"
// du workflow n8n (voir workflow/generer_workflow.py). Test : node src/nettoyage.test.js

const TYPES_TRAVAUX = ['salle de bain', 'cuisine', 'toiture', 'isolation', 'rénovation complète', 'autre'];

function sansAccents(s) {
  return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function texte(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).replace(/\s+/g, ' ').trim();
  return s && !/^(null|n\/a|non (renseigne|communique)e?s?|inconnue?)$/i.test(sansAccents(s)) ? s : null;
}

// "06 12 34 56 78", "+33 (0)7 81 45 22 90", "0033612345678" -> "+33612345678"
function normaliserTelephone(v) {
  const s = texte(v);
  if (!s) return null;
  let d = s.replace(/\(0\)/g, '').replace(/[^\d+]/g, '');
  if (d.startsWith('00')) d = '+' + d.slice(2);
  if (/^0\d{9}$/.test(d)) return '+33' + d.slice(1);
  if (/^33\d{9}$/.test(d)) return '+' + d;
  if (/^\+33\d{9}$/.test(d)) return d;
  if (/^\+\d{8,15}$/.test(d)) return d; // numéro étranger
  return null;
}

// "+33612345678" -> "+33 6 12 34 56 78" (lisible dans le Sheet)
function formaterTelephone(e164) {
  if (!e164) return null;
  const m = e164.match(/^\+33(\d)(\d{2})(\d{2})(\d{2})(\d{2})$/);
  return m ? `+33 ${m[1]} ${m[2]} ${m[3]} ${m[4]} ${m[5]}` : e164;
}

function normaliserEmail(v) {
  const s = texte(v);
  if (!s) return null;
  const e = s.toLowerCase().replace(/^mailto:/, '').replace(/\s/g, '');
  return /^[^@]+@[^@]+\.[a-z]{2,}$/.test(e) ? e : null;
}

// 8000, "8 000 €", "15k€", "12.000 euros" -> nombre
function parserBudget(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return Number.isFinite(v) && v > 0 ? Math.round(v) : null;
  let s = sansAccents(String(v)).toLowerCase().replace(/[\s  ]|€|euros?/g, '');
  let mult = 1;
  if (/k$/.test(s)) { mult = 1000; s = s.slice(0, -1); }
  if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, '');
  const n = parseFloat(s.replace(',', '.'));
  return Number.isFinite(n) && n > 0 ? Math.round(n * mult) : null;
}

// "sous 3 mois" -> 3, "dans 6 semaines" -> 1.4, "dès que possible" -> 0
function calculerDelaiMois(delaiTexte, valeurIA) {
  const s = sansAccents(texte(delaiTexte) || '').toLowerCase();
  if (/(des que possible|asap|urgent|immediat|au plus vite|tout de suite|rapidement)/.test(s)) return 0;
  const unites = [[/mois/, 1], [/semaines?/, 1 / 4.33], [/jours?/, 1 / 30], [/(ans?|annees?)\b/, 12]];
  for (const [re, facteur] of unites) {
    const m = s.match(new RegExp('((?:\\d+(?:[.,]\\d+)?\\s*(?:a|et|-|ou)\\s*)?\\d+(?:[.,]\\d+)?)\\s*' + re.source));
    if (m) {
      const nombres = m[1].match(/\d+(?:[.,]\d+)?/g).map((x) => parseFloat(x.replace(',', '.')));
      return Math.round(Math.max(...nombres) * facteur * 10) / 10;
    }
  }
  const n = typeof valeurIA === 'number' ? valeurIA : parseFloat(valeurIA);
  return Number.isFinite(n) && n >= 0 ? Math.round(n * 10) / 10 : null;
}

function categoriserTravaux(v, description) {
  const s = sansAccents(`${texte(v) || ''}`).toLowerCase();
  if (!s) return null;
  const d = sansAccents(`${s} ${description || ''}`).toLowerCase();
  if (/renovation (complete|totale|globale)|appartement complet|maison complete/.test(s)) return 'rénovation complète';
  if (/salle (de|d'eau|d eau)|bain|douche/.test(s)) return 'salle de bain';
  if (/cuisine/.test(s)) return 'cuisine';
  if (/toit|couverture|zinguerie|charpente/.test(s)) return 'toiture';
  if (/isol|combles/.test(s)) return 'isolation';
  if (/renovation (complete|totale|globale)/.test(d)) return 'rénovation complète';
  return 'autre';
}

function departementDepuis(codePostal, departement, ville) {
  const cp = String(codePostal || '').match(/\b(\d{5})\b/);
  if (cp) return cp[1].startsWith('97') ? cp[1].slice(0, 3) : cp[1].slice(0, 2);
  const dep = String(departement || '').match(/\b(\d{2,3}|2[ab])\b/i) || String(ville || '').match(/\((\d{2,3})\)/);
  return dep ? dep[1].toUpperCase() : null;
}

// Identifiant stable : le même mail donne toujours le même ID.
function genererLeadId(messageId, recuLe) {
  const base = String(messageId || recuLe || Math.random());
  let h = 5381;
  for (const c of base) h = ((h * 33) ^ c.charCodeAt(0)) >>> 0;
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 0x45d9f3b) >>> 0;
  const jour = dateParis(recuLe).slice(0, 10).replace(/-/g, '');
  return `HP-${jour}-${h.toString(36).toUpperCase().padStart(6, '0').slice(-6)}`;
}

// "2026-10-29 14:05" à l'heure de Paris (format reconnu comme date par Google Sheets)
function dateParis(v) {
  const d = v ? new Date(v) : new Date();
  const ok = Number.isNaN(d.getTime()) ? new Date() : d;
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(ok).replace('T', ' ');
}

function ligneAlerte(type, lead, detail, mail) {
  return {
    Date: dateParis(),
    Type: type,
    'ID du lead': lead ? lead['ID'] : null,
    Nom: lead ? lead['Nom'] : null,
    'Détail': detail,
    'Extrait du mail': mail ? `${mail.subject || ''}\n\n${mail.body || ''}`.slice(0, 5000) : null,
    'ID du mail': mail ? mail.message_id : lead ? lead['ID du mail'] : null,
  };
}

// extrait = sortie de l'IA, mail = { subject, body, received_at, message_id, source }
function nettoyerLead(extrait, mail) {
  const x = extrait || {};
  const m = mail || {};
  const tel = normaliserTelephone(x.telephone);
  const email = normaliserEmail(x.email);
  const description = texte(x.description);
  const type = categoriserTravaux(x.type_travaux, description);
  let bmin = parserBudget(x.budget_min);
  let bmax = parserBudget(x.budget_max);
  if (bmin && bmax && bmin > bmax) [bmin, bmax] = [bmax, bmin];
  const delaiTexte = texte(x.delai_texte);
  const nom = texte(x.nom);

  const manquants = [];
  if (!nom) manquants.push('nom');
  if (!tel && !email) manquants.push('téléphone ou email');
  if (!type) manquants.push('type de travaux');
  const aPreciser = [];
  if (!bmin && !bmax) aPreciser.push('budget');
  if (!delaiTexte) aPreciser.push('délai');
  if (!texte(x.ville)) aPreciser.push('ville');

  const complet = manquants.length === 0;
  const ligne = {
    ID: genererLeadId(m.message_id, m.received_at),
    'Date de réception': dateParis(m.received_at),
    Nom: nom,
    'Téléphone': formaterTelephone(tel),
    Email: email,
    Ville: texte(x.ville),
    'Département': departementDepuis(x.code_postal, x.departement, x.ville),
    'Type de travaux': type,
    Description: description ? description.slice(0, 500) : null,
    'Budget min (€)': bmin,
    'Budget max (€)': bmax,
    'Délai (texte)': delaiTexte,
    'Délai (mois)': calculerDelaiMois(delaiTexte, x.delai_mois),
    Statut: complet ? 'Nouveau' : 'À compléter',
    Responsable: null,
    'Date de 1er contact': null,
    'Prochaine action': complet
      ? 'Appeler sous 24 h' + (aPreciser.length ? ` (demander : ${aPreciser.join(', ')})` : '')
      : `Compléter : ${manquants.join(', ')} (voir l'espace Habitat Presto)`,
    'Nb de demandes': 1,
    Source: m.source || 'Habitat Presto',
    'ID du mail': m.message_id || null,
    'Dernière demande': dateParis(m.received_at),
  };
  return {
    ligne,
    telephone_normalise: tel,
    email_normalise: email,
    complet,
    champs_manquants: manquants,
    alerte: complet ? null : ligneAlerte('Lead incomplet', ligne, `Champs manquants : ${manquants.join(', ')}`, m),
  };
}

// Cherche une ligne existante avec le même téléphone ou le même email.
function trouverDoublon(lead, lignes) {
  for (const r of lignes || []) {
    if (!r || !r['ID']) continue;
    const tel = normaliserTelephone(r['Téléphone']);
    const email = normaliserEmail(r['Email']);
    if (lead.telephone_normalise && tel === lead.telephone_normalise) return { ligne: r, critere: 'téléphone' };
    if (lead.email_normalise && email === lead.email_normalise) return { ligne: r, critere: 'email' };
  }
  return null;
}

if (typeof module !== 'undefined') {
  module.exports = {
    TYPES_TRAVAUX, normaliserTelephone, formaterTelephone, normaliserEmail, parserBudget, calculerDelaiMois,
    categoriserTravaux, departementDepuis, genererLeadId, dateParis, ligneAlerte, nettoyerLead, trouverDoublon,
  };
}
