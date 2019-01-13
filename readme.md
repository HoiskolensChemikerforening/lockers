# Bokskap
Nettside for å holde styr på bokskap.
Krever NTNU konto for å registrere skap.

## Installasjon
`pip install -r requirements/dev.txt` er alt som skal til.
Prosjektet er så lite at man ikke trenger PostgreSQL.

Sett miljøvarabelen: `DJANGO_SETTINGS_MODULE=main.settings.dev`.

For å endre e-poster må du ha [MJML](https://mjml.io/download) + [GUI MJML App](https://mjmlio.github.io/mjml-app/).
Deretter må du kjøre `python manage.py import_emails` for å laste disse inn.