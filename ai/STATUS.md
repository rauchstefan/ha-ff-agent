# Projektstand

Was ist der aktuelle Stand der Integration? Diese Datei beantwortet das für jede neue
Session. Von Hand gepflegt.

- **Version:** 0.1.0 im Manifest, kein Release
- **Integration:** MVP in Arbeit (ADR 0002, Plan docs/plaene/261017-mvp-alarm-zusage.md).
  Erledigt sind PR 1 und 2 von 6:
  - Config Flow (eine Person je Eintrag), Parser für die Rückmelde-URL, Webhook-URL
    (Cloudhook, extern, intern)
  - Webhook-Empfang (GET/POST) mit optionalem Zusatz-Token und Repair-Issue; erfasst wird
    nur die Form des Aufrufs, Diagnostics sind redigiert

  Es gibt noch keine Entitäten (PR 3) und keine Rückmeldung (PR 4).
- **CI:** `validate.yml` (hassfest, HACS-Action) und `tests.yml` (ruff, pytest mit
  pytest-homeassistant-custom-component, Python 3.14, Abdeckung mindestens 95 %),
  Dependabot
- **Letzte Änderung:** 2026-10-17 – MVP PR 2 (rauchstefan/ha-ff-agent#3)

## Was funktioniert

- hassfest, ruff und pytest laufen grün in GitHub Actions, die Abdeckung liegt bei 100 %.
- Der Config Flow speichert nur die UUID und den Host der Rückmelde-URL und zeigt die
  Webhook-URL an. Die Cloud-API ist nur gestubbt getestet; ein Vertragstest prüft die
  Signaturen.

## Bekannte Einschränkungen

- Das Repo ist privat, daher funktioniert keine HACS-Installation und der HACS-Job in
  der CI wird übersprungen.
- Ein Webhook-Aufruf wird nur gezählt und in der Diagnose als Form sichtbar. Alarm-Entitäten
  folgen mit PR 3.
- Das Token ist vor PR 5 (Options Flow) in der UI nicht sichtbar. Die Token-Prüfung lässt
  sich deshalb noch nicht einschalten.
- Ein echter Test (FF Agent → HA) ist möglich, steht aber noch aus und braucht die Freigabe
  des Nutzers.
- Die Icons sind Platzhalter, die Rechte am FF-Agent-Logo sind ungeklärt.
- Lokal gibt es kein Python. Tests laufen nur in GitHub Actions.

## Zugänge und Testumgebung

- FF-Agent-Testzugang: unbekannt (siehe `docs/projekt-brief.md`, Fragen an den Nutzer)
- Home-Assistant-Testinstanz: noch nicht festgelegt
