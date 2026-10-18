# Mitmachen / Contributing

**Sprache / Language:** [Deutsch](#deutsch) · [English](#english)

# Deutsch

Danke für dein Interesse. Dies ist ein inoffizielles Community-Projekt.

## Fehler melden und Fragen stellen

- Fehler als [Issue](https://github.com/rauchstefan/ha-ff-agent/issues) melden, mit
  Beschreibung, erwartetem und tatsächlichem Verhalten und der Diagnose der Integration.
- Fragen und Erfahrungen in den
  [Diskussionen](https://github.com/rauchstefan/ha-ff-agent/discussions).
- Schwärze vor dem Posten Tokens, Webhook-URLs, ntfy-Themen, Namen, Adressen und echte
  Einsatzdaten in Logs und Screenshots.

## Pull Requests

- Gegen `main`, von einem Branch `feat/<thema>` bzw. `fix/<thema>`.
- Commit-Messages auf Englisch im Conventional-Commits-Stil (`feat:`, `fix:`, `docs:`,
  `test:`, `chore:`).
- Code-Bezeichner sind englisch, Doku und Kommentare deutsch.
- Die Prüfungen laufen in GitHub Actions: pytest, ruff, hassfest und HACS-Validierung.
  Ein PR wird erst bei grünem Lauf gemergt.
- Übersetzungen liegen unter `custom_components/ff_agent/translations/`.
- Committe keine Secrets (Zugangsdaten, Webhook-URLs, Tokens) und keine echten
  Einsatzdaten.

Mehr zur Arbeitsweise: [CLAUDE.md](CLAUDE.md) und [docs/architektur.md](docs/architektur.md).

# English

Thanks for your interest. This is an unofficial community project.

## Reporting bugs and asking questions

- Report bugs as an [issue](https://github.com/rauchstefan/ha-ff-agent/issues), with a
  description, expected and actual behaviour and the diagnostics of the integration.
- Questions and experiences go to the
  [discussions](https://github.com/rauchstefan/ha-ff-agent/discussions).
- Before posting, redact tokens, webhook URLs, ntfy topics, names, addresses and real
  mission data in logs and screenshots.

## Pull requests

- Against `main`, from a branch `feat/<topic>` or `fix/<topic>`.
- Commit messages in English, Conventional Commits style (`feat:`, `fix:`, `docs:`,
  `test:`, `chore:`).
- Code identifiers are English; documentation and comments are German.
- Checks run in GitHub Actions: pytest, ruff, hassfest and HACS validation. A PR is only
  merged when the run is green.
- Translations live under `custom_components/ff_agent/translations/`.
- Do not commit secrets (credentials, webhook URLs, tokens) or real mission data.

More on the way of working: [CLAUDE.md](CLAUDE.md) and
[docs/architektur.md](docs/architektur.md) (in German).
