"""Envoie un lead de test au webhook n8n (Python 3, aucune dépendance).

Exemples :
  python send_test_lead.py            -> liste les leads disponibles
  python send_test_lead.py 1          -> envoie test-leads/01-... à l'URL de test
  python send_test_lead.py 3 --prod   -> envoie à l'URL de production (workflow activé)
  python send_test_lead.py 1 --url http://localhost:5678/webhook-test/lead-habitat-presto
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

DOSSIER = Path(__file__).parent / "test-leads"
CHEMIN = "lead-habitat-presto"
URL_TEST = f"http://localhost:5678/webhook-test/{CHEMIN}"   # quand on clique « Listen for test event » / « Execute workflow »
URL_PROD = f"http://localhost:5678/webhook/{CHEMIN}"        # quand le workflow est activé


def lire_lead(fichier):
    lignes = fichier.read_text(encoding="utf-8").strip().splitlines()
    sujet = lignes[0].split(":", 1)[1].strip() if lignes and lignes[0].lower().startswith("objet") else ""
    corps = "\n".join(lignes[1:] if sujet else lignes).strip()
    return sujet, corps


def main():
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Envoie un lead de test au webhook n8n.")
    p.add_argument("lead", nargs="?", help="numéro (1, 2…) ou nom du fichier dans test-leads/")
    p.add_argument("--prod", action="store_true", help="utiliser l'URL de production /webhook/")
    p.add_argument("--url", help="URL complète du webhook (remplace les autres options)")
    a = p.parse_args()

    fichiers = sorted(DOSSIER.glob("*.txt"))
    if not a.lead:
        print("Leads disponibles :")
        for f in fichiers:
            print(f"  {f.name}")
        print("\nUsage : python send_test_lead.py 1   (ou --prod si le workflow est activé)")
        return

    choix = [f for f in fichiers if f.name == a.lead or f.name.startswith(a.lead.zfill(2) + "-")]
    if not choix:
        sys.exit(f"Lead introuvable : {a.lead}")
    sujet, corps = lire_lead(choix[0])

    payload = {
        "subject": sujet,
        "body": corps,
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message_id": f"test-{choix[0].stem}-{uuid.uuid4().hex[:8]}",  # nouvel ID à chaque envoi, comme un vrai nouveau mail
    }
    url = a.url or (URL_PROD if a.prod else URL_TEST)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    print(f"Envoi de {choix[0].name} -> {url}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"OK ({r.status}) : {r.read().decode('utf-8', 'replace')}")
    except urllib.error.HTTPError as e:
        print(f"Erreur {e.code} : {e.read().decode('utf-8', 'replace')}")
        if e.code == 404:
            print("-> En mode test, cliquez d'abord sur « Execute workflow » dans n8n (l'URL de test n'écoute qu'une fois).\n"
                  "-> Sinon activez le workflow et relancez avec --prod.")
        sys.exit(1)
    except urllib.error.URLError as e:
        sys.exit(f"n8n injoignable ({e.reason}). Est-il lancé ? (npx n8n)")


if __name__ == "__main__":
    main()
