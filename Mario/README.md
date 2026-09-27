# AI / Incident Atlas

Due mappe globali statiche in Python, ispirate a Digital Violence di Forensic
Architecture, senza affiliazione. Solo titolo, mappa e legenda: nessuna timeline,
zoom o etichetta dei paesi. La seconda mappa colora i simboli per piattaforma;
geometria e simboli sono identici. Non sono presenti etichette numeriche.

## Esecuzione

```sh
conda run -n smt python Mario/mappa_incidenti.py
```

In alternativa, installare `Mario/requirements.txt` nel proprio ambiente Python.
Input: `dataset/incidents.csv`. Opzioni: `--csv`, `--output`, `--dpi`.
Il programma funziona senza rete, usando gli asset geografici locali.

## Risultati

- `output/mappa_globale.png` e `.svg`: mappa monocromatica.
- `output/mappa_globale_chatbot.png` e `.svg`: colori per piattaforma chatbot.
- I due `.html` mostrano soltanto le rispettive mappe.
- `output/localizzazioni.csv`: numeri, date originali, coordinate, precisione,
  piattaforma e decessi, per identificare ogni punto.

## Simboli e registro

23 incidenti mortali, 35 decessi. Nina, senza decessi, è esclusa.
I numeri #01–#23, presenti solo nel CSV di registro, identificano incidenti, non singole vittime. L'area del simbolo
è proporzionale ai decessi. Coordinate e colori coincidenti vengono aggregati
in un unico simbolo, senza etichette.

L'ordine usa l'inizio dell'intervallo di data disponibile, poi l'ID in caso di
pareggio. Joe Ceccanti ha solo l'anno 2025; Sophie Rottenberg solo febbraio 2025.
La loro posizione relativa non rappresenta una cronologia giornaliera accertata.
Le date nel registro conservano la precisione originale del CSV e, per gli
incidenti con più eventi, possono non coprire l'intero periodo degli eventi.

21 incidenti (33 decessi) sono localizzabili almeno a livello di Stato o paese.
Sophie Rottenberg (#06) e Alex Taylor (#11), un decesso ciascuno, sono in legenda
come località ignota, senza inventare punti. Tutte le posizioni usano cerchi pieni, senza distinzione grafica di precisione.
Alcune coordinate sono indicative: centro geometrico di Stato/paese o centro
cittadino per area urbana. La precisione resta documentata nel CSV di registro.
I punti rappresentano località o aree, non indirizzi esatti.

Il database documenta un possibile coinvolgimento dei chatbot, senza stabilire
causalità. Per nuove località occorre aggiornare gli asset delle coordinate;
località non riconosciute restano non localizzate.

## Fonti

- H. Karman, AI Companion Mortality Database, https://aimortality.org/, CC BY 4.0.
  CSV fornito non modificato. Attribuzione inclusa anche nei metadati PNG/SVG.
- Coordinate: Open-Meteo Geocoding API / GeoNames,
  https://open-meteo.com/en/docs/geocoding-api, consultato il 24 settembre 2026.
- Natural Earth tramite world-atlas 2:
  https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json.
- US Census tramite us-atlas 3, per i centri degli Stati:
  https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json.
- Proiezione Robinson; asset e coordinate salvati nella cartella `assets`.
