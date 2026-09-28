# Høiax Connected for Home Assistant

Styr og overvåk **Høiax Connected**-varmtvannsberederen din (Connected 200/300) i Home Assistant. Installasjonen skjer via HACS, og du logger inn med den samme e-posten og det samme passordet som i myUplink-appen. Du trenger ingen YAML, ingen API-nøkler og ingen utviklerkonto.

[![Åpne i HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jrgenl&repository=hoiax-connected&category=integration)
[![Legg til integrasjon](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hoiax)

## Installasjon (ca. 2 minutter)

1. **Sjekk at berederen er i myUplink.** Den må vises i [myUplink-appen](https://myuplink.com). Hvis den ikke er der, følg Høiax sin veiledning for å koble til myUplink.
2. **Installer via HACS.** Trykk på knappen *Åpne i HACS* over, og velg **Last ned**.
   *Manuelt:* Gå til HACS → ⋮ → *Egendefinerte repositorier*, legg til `https://github.com/jrgenl/hoiax-connected` med typen *Integrasjon*, og last den ned.
3. **Start Home Assistant på nytt.**
4. **Legg til integrasjonen.** Trykk på knappen *Legg til integrasjon* over, eller gå til *Innstillinger → Enheter og tjenester → Legg til integrasjon → Høiax Connected*.
5. **Logg inn** med e-posten og passordet fra myUplink. Alle beredere på kontoen blir funnet automatisk.

## Dette får du

| Entitet | Hva |
|---|---|
| `water_heater` | Vanntemperatur, måltemperatur, program (Eco/Normal/Tidsplan/Ekstern/Ferie/Boost), av/på og bortemodus (Ferie) |
| Sensorer | Vanntemperatur, effekt (W), **energiforbruk (kWh, klar for Energi-dashbordet)**, lagret energi, varmtvannsnivå (%), aktivt program |
| Binærsensorer | Om varmeelement 1 og 2 er på |
| Valg | Program og maks effekt (Av / 700 W / 1300 W / 2000 W, avhengig av modell) |
| Innstillinger | Boost- og ferietemperatur/-varighet, hysterese og legionellaintervall. Romtemperatur, innløpstemperatur og maks vannstrøm er skjult som standard. |
| Diagnostikk | Tid til og siden legionellaprogram, tankvolum og driftstid |

Entitetene lages bare for verdiene berederen din faktisk rapporterer, så Connected 200 og 300 får hver sine riktige valg.

### Energi-dashbordet
Gå til *Innstillinger → Dashbord → Energi → Enkeltenheter* og legg til **Energiforbruk**-sensoren til berederen.

### Styring etter strømpris
Integrasjonen har med en blueprint som slår av oppvarmingen når strømmen er dyr, men som alltid varmer når vannet blir for kaldt:

[![Importer blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fjrgenl%2Fhoiax-connected%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhoiax%2Fstromprisstyring.yaml)

Blueprinten fungerer med alle strømpris-sensorer, for eksempel Nord Pool eller Tibber.

> **Tips:** Av/på og *Maks effekt* styrer varmeelementene direkte. Hvis berederens egne programmer (f.eks. *Tidsplan* eller *Smart*) overstyrer endringene dine, setter du programmet til **Ekstern styring**. Da er det Home Assistant som bestemmer.

## Innstillinger
Under *Innstillinger → Enheter og tjenester → Høiax Connected → Konfigurer* kan du endre hvor ofte data hentes. Standard er 60 sekunder. Minimum er 30 sekunder, slik at myUplink ikke blir overbelastet.

Hvis du bytter passord i myUplink, ber Home Assistant deg automatisk om å logge inn på nytt. Du kan også endre e-post eller passord via *⋮ → Rekonfigurer*.

## Feilsøking
- **«Feil e-post eller passord»:** Test innloggingen i myUplink-appen først.
- **«Ingen enheter funnet»:** Berederen er ikke lagt til på myUplink-kontoen din.
- **Verdier oppdateres ikke med en gang:** myUplink bruker noen sekunder på å bekrefte endringer. Integrasjonen oppdaterer seg selv automatisk etter 5 sekunder.
- **Debug-logg:** Legg dette i `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.hoiax: debug
  ```
- **Diagnostikk:** Gå til *Enheter og tjenester → Høiax Connected → ⋮ → Last ned diagnostikk*. Passord, e-post og serienummer blir fjernet automatisk, så filen kan trygt legges ved en feilrapport.

## Personvern
Passordet lagres lokalt i Home Assistant og sendes bare til myUplink (`myuplink.com`). Integrasjonen bruker den samme innloggingen som myUplink sin egen nettside.

## Utvikling
```bash
pip install -r requirements_test.txt ruff
ruff check custom_components tests && pytest
```

*Dette er ikke et offisielt produkt fra Høiax eller myUplink.*
