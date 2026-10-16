# Projektstand

Was ist der aktuelle Stand der Integration? Diese Datei beantwortet das für jede neue
Session. Von Hand gepflegt.

- **Version:** 0.1.0 im Manifest, kein Release
- **Integration:** HACS-konformes Grundgerüst ohne FF-Agent-Logik (Config-Flow nur mit
  Bestätigungsschritt, keine Entitäten)
- **CI:** `validate.yml` (hassfest, HACS-Action) und `tests.yml` (ruff, pytest mit
  pytest-homeassistant-custom-component, Python 3.14), Dependabot
- **Letzte Änderung:** 2026-10-16 – Grundgerüst + CI (PR rauchstefan/ha-ff-agent#1)

## Was funktioniert

- hassfest, ruff und pytest laufen grün in GitHub Actions.
- Die Integration lässt sich in den Tests einrichten, entladen und neu laden.

## Bekannte Einschränkungen

- Das Repo ist privat, daher funktioniert keine HACS-Installation und der HACS-Job in
  der CI wird übersprungen.
- `iot_class: cloud_polling` ist vorläufig, bis die FF-Agent-Schnittstelle bekannt ist.
- Die Icons sind Platzhalter, die Rechte am FF-Agent-Logo sind ungeklärt.
- Lokal gibt es kein Python. Tests laufen nur in GitHub Actions.

## Zugänge und Testumgebung

- FF-Agent-Testzugang: unbekannt (siehe `docs/projekt-brief.md`, Fragen an den Nutzer)
- Home-Assistant-Testinstanz: noch nicht festgelegt
