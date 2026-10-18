# Erster echter Test: Anleitung für den Nutzer

TODO-ID: `261017-echter-test` · Freigabe des Nutzers am 2026-10-17 erteilt · Stand:
Release v0.2.0 (Vorabversion), Installation über HACS

Ziel: Herausfinden, wie sich FF Agent wirklich verhält. Die Annahmen aus ADR 0002
(A1–A13) werden geprüft. Was du siehst, trägst du in die **Rückmeldeliste** am Ende ein
und gibst sie dem Projektleiter.

**Grundregeln**
- Gib keine Webhook-URL, kein Token, keine Rückmelde-URL und keine echten Einsatzdaten an
  Claude oder ins Repo weiter. Die Diagnose-Datei der Integration ist redigiert und darf
  weitergegeben werden. Schau trotzdem kurz hinein, bevor du sie teilst.
- Keine Debug-Logs teilen. Sie enthalten Geheimnisse (siehe README, „Datenschutz“).
- Zu- und Absagen nur während eines **Testalarms**.

## 0. Vorbereitung (ca. 10 min)

1. **Backup** deiner Home-Assistant-Instanz anlegen (Einstellungen → System → Backups).
2. **Version prüfen:** Einstellungen → Info. Nötig ist Home Assistant **2026.3.0 oder
   neuer**.
3. **Erreichbarkeit prüfen:** Hat deine Instanz Nabu Casa (Home Assistant Cloud) oder
   eine externe HTTPS-URL? Ohne eines von beiden erreicht FF Agent den Webhook nicht.
   Notiere, welche Variante du nutzt (Rückmeldeliste, Punkt 1).
4. **Testalarm klären:** Als Admin weißt du, wen ein Testalarm in eurer Einheit erreicht.
   Empfehlung: Testalarm nur an eine Testgruppe, in der du allein bist. Sonst die
   Kameradinnen und Kameraden vorher informieren.
5. **Keine Automationen mit Folgen:** Für den Test **keine** Automation an „Alarm“
   hängen, die Tore, Türen oder Sirenen steuert. Ein Licht oder eine Benachrichtigung
   reicht.

## 1. Installation über HACS (Repo ist seit 2026-10-17 öffentlich)

Voraussetzung: HACS ist in deiner Instanz installiert.

1. In Home Assistant: **HACS** öffnen, oben rechts **⋮ → Benutzerdefinierte
   Repositories**.
2. Repository `https://github.com/rauchstefan/ha-ff-agent`, Typ **Integration**,
   hinzufügen.
3. In HACS nach **FF Agent** suchen und öffnen.
4. Es gibt nur Vorabversionen (v0.1.0 und v0.2.0); wir testen **v0.2.0**. Damit HACS sie anbietet, beim Repository die
   Anzeige von Beta- bzw. Vorabversionen aktivieren (Menü ⋮ des Repositorys oder dessen
   Einstellungen). Ohne diese Einstellung bietet HACS den Stand von `main` mit einem
   Commit-Kürzel als Version an. Das ginge auch, aber für den Test wollen wir v0.2.0.
   - Wie der Schalter in deiner HACS-Version heißt und wo er liegt, bitte notieren
     (Rückmeldeliste, Punkt 12). Damit verbessern wir das README.
5. **Herunterladen**, Version **v0.2.0** wählen.
6. Home Assistant **neu starten** (Einstellungen → System → Neu starten).
7. Im Log steht danach eine Warnung, dass eine Custom-Integration geladen wurde, die
   nicht von Home Assistant getestet ist. Das ist normal.

Ohne HACS: `custom_components/ff_agent` aus dem Release-ZIP von v0.2.0 nach
`/config/custom_components/ff_agent` kopieren und neu starten.

## 2. Einrichtung in Home Assistant

1. In der FF-Agent-Web-UI: *Personen → (dein Name) → Bereich „Übung/Einsatz“ →
   „Weblinks für Einsatzmeldung“* (Seite „URLs für Einsatzmeldung“), die **Zusage-URL**
   kopieren. Die URLs gelten nur für diese Person und den jeweils aktiven Einsatz.
2. In Home Assistant: *Einstellungen → Geräte & Dienste → Integration hinzufügen →
   „FF Agent“*.
3. „Name“: z. B. dein Vorname. Bei „Rückmelde-URL (Zusage)“ die kopierte URL einfügen.
   Es wird dabei nichts an FF Agent gesendet.
4. Der Abschlussdialog zeigt die **Webhook-URL** und eine Kurzanleitung. URL kopieren.
   - Steht dort „Achtung … interne Adresse“ oder „nur den Pfad“, erreicht FF Agent sie
     nicht. Dann abbrechen und erst eine externe URL oder Nabu Casa einrichten (siehe
     README, „Neu konfigurieren“).
   - Die URL siehst du später jederzeit wieder unter *FF Agent → Konfigurieren*.

## 3. Webhook in FF Agent anlegen

*Web-UI → Automatisierung → Persönliche Webhooks → Webhook hinzufügen*:

| Feld | Wert für den Test |
|---|---|
| Type | Alarm |
| Webhooktyp | Generischer Webhook |
| Name | z. B. „Home Assistant Test“ |
| Aktiv | an |
| auch für Testalarme | **an** |
| auch für Infoalarme | aus |
| auch für stille Einsätze | an |
| Zeitplan aktiviert | aus |
| Versand/Daten | **POST** |
| URL | die Webhook-URL aus Schritt 2 (Schema `https://` wählen, Rest ins Feld) |
| Basis-Authentifizierung | leer |
| Header | **Name** `X-FF-Agent-Token`, **Wert** `test` (absichtlich ein Dummy, siehe unten) |
| Inhalt / Query-Parameter | leer |

Den Dummy-Header brauchen wir nur für die Messung, ob eigene Header bei Home Assistant
ankommen (A12). In Home Assistant bleibt „Zusatz-Token verlangen“ dabei **aus**, der Wert
wird also nicht geprüft.

Speichern. Gibt es im Dialog oder in der Liste eine Schaltfläche wie „Testen“, ein
Aufrufprotokoll oder ein Info-Symbol zu Platzhaltern? Dann notieren (Rückmeldeliste,
Punkt 9).

## 4. Messung A: Kommt der Alarm an?

1. **Vorher:** In Home Assistant *FF Agent → Gerät* öffnen. Notieren:
   - „Alarm“: vermutlich „Unbekannt“
   - „Alarm aktiv“: Aus
   - „Letzter Alarm“
2. **Testalarm** in FF Agent auslösen.
3. **Innerhalb weniger Sekunden** sollten in Home Assistant:
   - „Alarm“ einen neuen Zeitstempel zeigen,
   - „Alarm aktiv“ auf **An** springen,
   - „Letzter Alarm“ die Uhrzeit zeigen.
4. **Diagnose herunterladen:** *Einstellungen → Geräte & Dienste → FF Agent → beim
   Eintrag ⋮ → Diagnose herunterladen*. Die Datei als `diagnose-1.json` aufheben.
5. Falls nichts passiert: README → „Fehlerbehebung“. Steigt in der Diagnose weder
   `stats.calls_total` noch `stats.rejected_total`, kommt der Aufruf nicht bei Home
   Assistant an. Dann Webhook „Aktiv“, URL, Testalarm-Haken und Erreichbarkeit prüfen.

## 5. Messung B: Zusage und Absage (nur solange der Testalarm aktiv ist)

1. In FF Agent prüfen, dass der Testalarm noch **aktiv** ist und dass **du selbst** dafür
   alarmiert wurdest. Zu- und Absage gehen nur für den aktiven Einsatz und nur, wenn die
   Person alarmiert wurde.
2. In Home Assistant den Button **„Absagen“** einmal drücken.
   - „Letzte Rückmeldung“ zeigt „Abgesagt“ oder „Fehlgeschlagen“.
   - In FF Agent (App oder Web-UI) prüfen, ob deine Absage beim Testalarm erscheint.
3. **15 Sekunden warten**, dann **„Zusagen“** drücken.
   - „Letzte Rückmeldung“ zeigt „Zugesagt“ oder „Fehlgeschlagen“.
   - In FF Agent prüfen: Zusage sichtbar? Wird ein Verkehrsmittel („Auto“) angezeigt?
4. Diagnose erneut herunterladen → `diagnose-2.json`.
5. Testalarm in FF Agent beenden.

## 6. Messung C (optional): Alarmarten

Nur, wenn es ohne Aufwand geht. Je einen **Infoalarm** und einen **stillen Einsatz** als
Test auslösen und jeweils notieren, ob „Alarm“ in Home Assistant neu auslöst. Erwartet:
Infoalarm nein (Haken aus), stiller Einsatz ja (Haken an).

## 7. Aufräumen nach dem Test

- Den Header `X-FF-Agent-Token = test` in FF Agent **löschen** oder später durch das
  echte Token ersetzen (siehe README, „Optionale Token-Absicherung“).
- Soll die Integration weiterlaufen: „auch für Testalarme“ nach Wunsch ausschalten.
- Soll sie nicht weiterlaufen: Webhook in FF Agent deaktivieren und die Integration in
  Home Assistant löschen.

## Rückmeldeliste (an den Projektleiter)

Bitte ohne URLs, Token oder Einsatzinhalte. Die Werte stehen in den Diagnose-Dateien
unter den genannten Schlüsseln.

| Nr. | Frage | Wo ablesen | Annahme |
|---|---|---|---|
| 1 | Erreichbarkeit: Nabu Casa, externe URL oder nichts? Was steht unter `webhook.url_kind`? | Schritt 0 bzw. diagnose-1 | A4, A12 |
| 2 | Kam der Testalarm an? Wie viele Sekunden zwischen Auslösen und „Alarm aktiv“? | Schritt 4 | A1, A3 |
| 3 | `stats.calls_total`, `alarm.alarms_total`, `alarm.deduplicated_total` nach **einem** Testalarm | diagnose-1 | A3 (Wiederholungen) |
| 4 | `stats.last_call.method` und `.user_agent` | diagnose-1 | A1 |
| 5 | `stats.last_call.body_kind`, `.body_length`, `.content_type`, `.query_keys` (bei `json` auch `.body_shape`) | diagnose-1 | A2, A13 |
| 6 | Steht `x-ff-agent-token` in `stats.last_call.header_names`? | diagnose-1 | A12 |
| 7 | Absage: „Letzte Rückmeldung“, Anzeige in FF Agent; `reply.last_result.status`, `.content_type`, `.error_type` | Schritt 5 / diagnose-2 | A6, A7 |
| 8 | Zusage: dasselbe; wird in FF Agent „Auto“ angezeigt? | Schritt 5 / diagnose-2 | A6, A7, A9 |
| 9 | Gibt es im Webhook-Dialog „Testen“, ein Protokoll, eine Platzhalter-Hilfe? | Schritt 3 | A13 |
| 10 | Optional: Infoalarm / stiller Einsatz ausgelöst? | Schritt 6 | A5 |
| 11 | Alles, was überrascht hat (Fehlermeldungen in HA, Repair-Hinweise, Verzögerungen) | | |
| 12 | HACS: Ließ sich das Repository hinzufügen? Wie heißt der Schalter für Vorabversionen, wo liegt er, und welche Version zeigt HACS nach der Installation? | Schritt 1 | HACS-Doku |

Alternativ zu den Einzelwerten kannst du die beiden Diagnose-Dateien weitergeben, nachdem
du kurz hineingesehen hast. Sie enthalten keine URLs, Tokens oder Einsatzinhalte.
