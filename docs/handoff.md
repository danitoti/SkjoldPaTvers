# Skjold på tvers - handoff

## Prosjekt
Webbasert resultatsystem for Skjold på tvers.

Stack:
- Python
- FastAPI
- SQLite
- SQLAlchemy
- Alembic
- Jinja2 templates
- pyserial senere for RS-232

## Viktige prinsipper

- Løypa er dynamisk.
- EMIT-koder/poster skal kunne endres fra år til år.
- Rå EMIT-tekst skal alltid lagres.
- Ukjente bukker skal ignoreres, men loggføres.
- Duplikatstemplinger skal ignoreres, men loggføres.
- Manglende poster gir ingen diskvalifikasjon eller straff.
- Ny skanning av samme brikke overskriver aktivt resultat, men historikk beholdes.
- Offisiell tid skal beregnes fra serverens klokke, ikke skannerens/EMIT sin klokke.

## Offisiell tidsberegning

Målgang:

server_received_at - finish_to_scan_seconds

Totaltid:

finish_datetime - race.start_time

## Ferdig

- Git/GitHub
- Prosjektstruktur
- FastAPI backend
- SQLite
- SQLAlchemy
- Alembic
- Database modeller:
  - races
  - athletes
  - controls
  - event_log
  - raw_scans
  - scan_punches
  - results
  - result_splits
- Adminside:
  - opprette/velge løp
  - sette fellesstart
  - importere EQ Timing CSV
  - legge inn dynamiske poster
  - søke løpere
  - endre brikkenummer
  - hendelseslogg
- EMIT parser:
  - brikkenummer
  - EMIT total
  - tid fra mål til skanner
  - alle stemplinger
  - antall ikke-tomme linjer
- EMIT-testside
- Manuell skanning til database
- Første resultatberegning basert på serverklokke

## Skal bli værende i programmet

- EMIT-testside
- Manuell skanning

Disse brukes som diagnose/backup hvis RS-232 feiler eller rare brikker må kontrolleres.

## Siste kjente commit

Calculate official results from server scan time

## Neste steg

1. Vise strekktider per løper.
2. Lage livevisning delt i damer/herrer.
3. Håndtere ukjent brikke med manuell kobling til startnummer.
4. Lage RS-232-leser.
5. Koble RS-232 til store_emit_scan().
6. Lage eksport til EQ Timing CSV.
7. Forbedre adminside for løpsdrift.
