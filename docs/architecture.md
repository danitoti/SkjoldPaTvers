# Arkitektur

## Oversikt

Datamodellen består av følgende hovedobjekter:

Race
├── Settings
├── Athletes
├── Controls
├── RawScans
├── ScanPunches
└── Results


---

# races

Representerer ett arrangement.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| name | F.eks. "Skjold på tvers 2026" |
| start_time | Felles starttid |
| created_at | Opprettet |
| updated_at | Sist endret |


---

# athletes

Importeres fra EQ Timing.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| race_id | Referanse til løp |
| start_number | Startnummer |
| chip_number | EMIT-brikkenummer |
| first_name | Fornavn |
| last_name | Etternavn |
| club | Klubb |
| gender | Kjønn |
| class_name | Klasse |
| distance | Løype |
| country | Land |
| birth_year | Fødselsår |
| eqtiming_participant_uid | EQ Timing ID |
| eqtiming_athlete_uid | EQ Timing Athlete ID |

Kommentar:

- chip_number brukes ved automatisk matching
- start_number brukes ved manuell matching


---

# controls

Dynamisk løype.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| race_id | Referanse til løp |
| sort_order | Rekkefølge |
| name | Navn på kontroll |
| emit_code | EMIT-kode |
| is_finish | True dersom mål |

Eksempel:

| Nr | Navn | Emit |
|----|------|------|
|1|Hodnafjell|100|
|2|Varden|111|
|3|Naustdalsfjell|113|
|4|Kikafjell|117|
|5|Haraldseidfjell|119|
|6|Haukaberg|120|
|7|Ravnafjell|121|
|8|Mål Vikaneset|150|


---

# raw_scans

Originaldata fra EMIT-skanneren.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| race_id | Referanse til løp |
| chip_number | Brikkenummer |
| athlete_id | Kan være tom |
| raw_text | Hele EMIT-strengen |
| scanner_time | Tidspunkt skannet |
| finish_to_scan_time | Tid fra mål til skanning |
| received_at | Når systemet mottok data |
| parse_status | ok / unknown_chip / error |
| error_message | Eventuell feil |

Kommentar:

Alle skanninger lagres.

Ny skanning av samme brikke overskriver resultatet, men ikke historikken.


---

# scan_punches

Alle gyldige poster fra én skanning.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| raw_scan_id | Referanse til raw_scans |
| control_id | Kan være tom |
| emit_code | EMIT-kode |
| sequence_code | 01, 02, ..., F |
| split_time_raw | Strekktid fra EMIT |
| accumulated_time_raw | Akkumulert EMIT-tid |
| calculated_time | Beregnet tid |
| ignored | True dersom ignoreres |
| ignore_reason | duplicate / too_short / unknown_control |


---

# results

Sluttresultat for en løper.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| race_id | Referanse til løp |
| athlete_id | Referanse til løper |
| finish_time | Offisiell målgang |
| total_seconds | Totaltid |
| rank_overall | Total plassering |
| rank_gender | Plassering i kjønn |
| missing_controls | Antall manglende poster |
| updated_at | Sist beregnet |


---

# result_splits

Beregnet tid ved hver kontroll.

| Felt | Beskrivelse |
|------|-------------|
| id | Primærnøkkel |
| result_id | Referanse til resultat |
| control_id | Referanse til kontroll |
| time_from_start | Tid fra fellesstart |
| split_time | Strekktid |
| has_punch | True/False |
| source_raw_scan_id | Hvilken skanning som ga data |


---

# Regler

## Tid

Offisiell tid beregnes alltid slik:

målgang = skannertid − tid_fra_mål_til_skanner

totaltid = målgang − fellesstart

EMITs interne totaltid brukes kun som kontroll.


---

## Manglende poster

Manglende poster gir:

- ingen diskvalifikasjon
- ingen tilleggstid

Resultatet rangeres normalt.


---

## Dobbeltstempling

Dersom samme EMIT-kode forekommer flere ganger:

- første gyldige stempling brukes
- senere stemplinger ignoreres

Ignorerte stemplinger lagres fortsatt i databasen.
