# Batterij Planner voor Home Assistant

**Versie: 5.3.0** · [Versiegeschiedenis](#versiegeschiedenis) · [Releases](https://github.com/Fripistack/Fripi-Battery-Planner-V1/releases)

Batterij Planner is een custom integration die je thuisbatterij stuurt op de dynamische kwartierprijzen van Frank Energie. Je stelt alles in via het scherm, zonder YAML.

Bij elke berekening worden **alle bekende kwartieren tegelijk** doorgerekend: vandaag en morgen, tot ongeveer 35 uur vooruit. Per kwartier kiest de planner wat het meest oplevert:

| modus | wat de omvormer doet |
|---|---|
| zelfverbruik | normaal: PV-overschot naar de accu, tekort uit de accu |
| vasthouden | accu staat stil, het huis draait op net en PV (accu sparen voor een duurder moment) |
| laden | accu laden op max vermogen, uit PV en/of net |
| ontladen | accu ontladen op max vermogen, naar huis en net |

Daardoor benut de planner een dure **ochtendpiek** net zo goed als de avondpiek.

Bij elke beslissing telt mee:

- afname- en terugleverprijs per kwartier, met saldering t/m 2026 en daarna marktprijs + opslag;
- de PV-verwachting;
- een zelf geleerd verbruiksprofiel per uur, apart voor werkdag en weekend;
- laad- en ontlaadverlies;
- slijtage;
- min/max SOC en max vermogen;
- de waarde van de lading die aan het einde van de planning nog in de accu zit.

Elke 5 minuten wordt opnieuw gerekend met de actuele SOC, en direct zodra de prijzen van morgen binnen zijn.

Gemaakt voor en getest met: Solis RHI-3.6K-48ES-5G (Solis Modbus), Dyness 16 kWh, Frank Quarter Prices en Forecast.Solar. Solcast werkt ook.

---

## Installatie

### 1. Oude sturing opruimen

Heb je eerder de YAML-versie (v5 package) of v4.x gebruikt?

- Haal `packages/batterij_planner.yaml` of je oude batterijpackage weg.
- Haal `python_scripts/batterij_planner.py` weg.
- De regel `python_script:` in `configuration.yaml` mag blijven staan als je andere scripts hebt. Anders mag die ook weg.
- Zet in de Frank-app **Slim Terugleveren** en **Slim Handelen** uit.

### 2. Integratie neerzetten

Kies een van de twee manieren.

**Handmatig (Samba, File editor of Studio Code Server):**

1. Maak in je configmap, waar `configuration.yaml` staat, een map `custom_components` als die er nog niet is.
2. Kopieer de map `batterij_planner` daarin, zodat je dit krijgt:

```
config/
├── configuration.yaml
└── custom_components/
    └── batterij_planner/
        ├── __init__.py
        ├── manifest.json
        ├── optimizer.py
        └── ... (overige bestanden + map translations)
```

**Via HACS (aanbevolen, dan krijg je updates in Home Assistant):**
1. HACS → ⋮ rechtsboven → **Aangepaste repositories**.
2. URL `https://github.com/Fripistack/Fripi-Battery-Planner-V1`, type **Integratie** → Toevoegen.
3. Zoek **Batterij Planner** → **Downloaden**.

Nieuwe versies verschijnen daarna onder **Instellingen → Updates**. Klik op Installeren en herstart Home Assistant.

### 3. Herstarten

Instellingen → ⋮ rechtsboven → **Home Assistant herstarten** → *Herstarten*.

### 4. Integratie toevoegen

Instellingen → **Apparaten & diensten** → **+ Integratie toevoegen** → zoek **Batterij Planner**.

De schermen van de integratie zijn in het Engels, met de namen uit Solis Modbus. Elk veld heeft een uitleg onder het invoerveld.

**Scherm 1: Battery Planner – data sources.** Bestaande standaardnamen zijn al ingevuld; controleer ze.

| veld | jouw entiteit (waarschijnlijk) |
|---|---|
| Battery SOC | `sensor.pv_omvormer_battery_soc` |
| Household load power | `sensor.pv_omvormer_household_load_power` |
| Frank prices – today / tomorrow | `sensor.frank_prices_today` / `sensor.frank_prices_tomorrow` |
| Solar forecast – remaining today / tomorrow | `sensor.energy_production_today_remaining` / `sensor.energy_production_tomorrow` |
| Solcast forecast (optional) | leeg laten, tenzij je Solcast gebruikt |

**Scherm 2: Battery Planner – inverter (Solis Time-Charging).**

| veld | Solis Modbus-entiteit |
|---|---|
| Time-Charging Charge Start / End (Slot 1) | `time.pv_omvormer_time_charging_charge_start_slot_1` / `..._charge_end_slot_1` |
| Time-Charging Discharge Start / End (Slot 1) | `time.pv_omvormer_time_charging_discharge_start_slot_1` / `..._discharge_end_slot_1` |
| Time-Charging Charge / Discharge Current | `number.pv_omvormer_time_charging_charge_current` / `..._discharge_current` |
| Storage Mode (optional) | `select.pv_omvormer_work_mode` |

### 5. Instellingen controleren

Bij de integratie: **Configureren → Settings**. De instellingen staan in vijf groepen; alles heeft een verstandige standaardwaarde.

| groep | wat je instelt |
|---|---|
| **Battery** | capaciteit, min/max SOC, max laad-/ontlaadvermogen, vermogensstappen 33/66 %, rendement, slijtagekosten per ontladen kWh |
| **Prices and feed-in** | saldering (automatisch t/m 2026), terugleveropslag na saldering, waarde van de restlading aan het einde van de planning |
| **Forecasts** | correctiefactor zonverwachting, verbruik zolang het profiel nog niet geleerd is |
| **Inverter control** | accuspanning (W → A), laadstroom bij *Hold* (0 A), Storage Mode tijdens laden/ontladen |
| **Notifications** | telefoon voor het dagelijkse plan van morgen |

Controleer vooral:
- **Storage Mode to use while charging/discharging.** Kies **Self-Use + TOU** als de planner de Storage Mode zelf mag zetten. Staat je omvormer al vast in een TOU-modus, laat dan *Don't change* staan. Laden uit het net werkt alleen met **Allow Grid to Charge the Battery** aan.
- **Send tomorrow's plan to.** Kies je telefoon (`notify.mobile_app_...`).

Wijzigingen gelden direct; de integratie herlaadt zichzelf.

### 6. Een dag meekijken, daarna aanzetten

Het apparaat **Batterij Planner** heeft een schakelaar **Control inverter**, die standaard uit staat. Zolang die uit staat, rekent de planner wel, maar raakt hij de omvormer niet aan.

1. Kijk een dag mee met de sensor **Mode**. Het attribuut `blokken` toont het hele plan; de dashboardkaart hieronder maakt het overzichtelijk.
2. Klopt het, zet dan **Control inverter** aan.
3. Kijk bij de eerstvolgende wissel in de Solis-entiteiten of de tijden veranderen. Het attribuut `laatste_schrijfacties` van de Mode-sensor laat zien wat er is geschreven.

Zet je de schakelaar uit, dan worden beide Time-Charging-slots leeggemaakt en draait de omvormer gewoon op zelfverbruik.

---

## Entiteiten

Sinds 5.1.0 hebben de entiteiten Engelse namen. Entity-ID's van een bestaande installatie veranderen niet. Een nieuwe installatie krijgt Engelse ID's (tweede kolom).

| naam | entity-ID (bestaand / nieuw) | betekenis |
|---|---|---|
| Mode | `sensor.batterij_planner_modus` / `sensor.batterij_planner_mode` | huidige modus (Self-consumption, Hold, Charge, Discharge); attributen: volledig plan (`blokken`, `slots`), kosten, PV-bron, fout |
| Expected saving | `..._verwachte_besparing` / `..._expected_saving` | € beter dan alleen zelfverbruik, over de hele bekende horizon |
| Next action | `..._volgende_actie` / `..._next_action` | bijv. `Discharge Tue 06:45–09:00` |
| Target SOC end of block | `..._doel_soc_einde_blok` / `..._target_soc_end_of_block` | verwachte SOC aan het eind van het huidige blok |
| Learned consumption last quarter | `..._geleerd_verbruik_laatste_kwartier` / `..._learned_consumption_last_quarter` | geleerd verbruik; attributen: profiel per uur |
| Control inverter | `switch.batterij_planner_sturing_actief` / `switch.batterij_planner_control_inverter` | omvormer wel/niet aansturen |
| Heat pump target temperature | `sensor.batterij_planner_heat_pump_target_temperature` | gewenste streeftemperatuur buffervat + waarom |
| Control heat pump | `switch.batterij_planner_control_heat_pump` | buffervat wel/niet aansturen |
| Thermostat target temperature | `sensor.batterij_planner_thermostat_target_temperature` | gewenst setpoint kamerthermostaat; attributen: jouw setpoint (`basis`), stand, kamertemperatuur |
| Control thermostat | `switch.batterij_planner_control_thermostat` | kamerthermostaat wel/niet verschuiven |
| Recalculate plan | `button.batterij_planner_plan_herberekenen` / `button.batterij_planner_recalculate_plan` | direct opnieuw rekenen |

De ruwe status van Mode blijft `zelfverbruik` / `vasthouden` / `laden` / `ontladen`, zodat bestaande automations en dashboards blijven werken. Home Assistant toont die als Self-consumption / Hold / Charge / Discharge.

## Hoe de omvormer wordt aangestuurd

De planner gebruikt alleen TOU-slot 1 en schrijft alleen als een waarde echt verandert:

| modus | laadslot 1 | ontlaadslot 1 |
|---|---|---|
| zelfverbruik | 00:00–00:00 (uit) | 00:00–00:00 (uit) |
| laden | nu → einde blok, stroom volgens stap | uit |
| vasthouden | nu → einde blok, 0 A | uit |
| ontladen | uit | nu → einde blok, stroom volgens stap |

Stroom = vermogen ÷ accuspanning (3000 W ÷ 51,2 V = 58 A).

**Vermogensstappen (sinds 5.3.0).** Met *Power steps 33 % / 66 %* aan (standaard) mag het plan ook laden of ontladen op 33 % of 66 % van het maximale vermogen: bij 3000 W is dat 990 W (19 A) of 1980 W (38 A). Het plan kiest per kwartier wat het goedkoopst uitkomt; in de praktijk vooral om een laad- of ontlaadblok precies af te maken in plaats van een kwartier vol vermogen. De stap staat in de blokken (`vermogen_pct`), in *Next action* (bijv. `Charge 66% Tue 02:00–02:30`) en in de melding. Zet je de optie uit, dan is het altijd vol vermogen zoals voorheen. Een blok dat over middernacht loopt, wordt tot 23:59 gezet en na middernacht opnieuw. Ontbreken gegevens (SOC onbekend, geen prijzen), dan valt de planner terug op zelfverbruik.

Twee dingen moet je één keer zelf testen:

- **Vasthouden:** controleer op een zonnig uur dat de accu met een laadslot op 0 A echt stilstaat.
- **Laden uit het net:** dat werkt alleen als *Allow grid charging* aan staat op de omvormer.

## Warmtepomp

Optioneel stuurt de integratie ook de **streeftemperatuur van het buffervat** van de warmtepomp (Tuya / Tuya Local), op basis van dezelfde Frank-prijzen. K (kelvin) is een temperatuurverschil: +3 K betekent 3 °C hoger dan normaal.

| situatie | streeftemperatuur (standaard) |
|---|---|
| kwartier hoort bij de goedkoopste 25 % van de komende 24 uur | normaal + 3 K → **28 °C** |
| zonne-overschot ≥ 1500 W én thuisaccu ≥ 90 % | normaal + 3 K → **28 °C** |
| kwartier hoort bij de duurste 25 % | normaal − 3 K, maar nooit onder het minimum → met normaal 25 °C blijft het **25 °C** |
| anders | normaal: **25 °C** (optioneel met stooklijn) |

Altijd binnen min/max (25–35 °C) en hooguit één wijziging per 30 minuten (beschermt tegen pendelen). Stem *Normal setpoint* af op de temperatuur waarop je warmtepomp nu staat.

**Instellen:** Configureren → **Heat pump**. Kies de entiteit voor de buffervat-streeftemperatuur (climate, water_heater of number) en optioneel de buffertemperatuur, buitentemperatuur, de thermostaat (bijv. Resideo T6) en het zonvermogen. De sensor **Heat pump target temperature** laat zien wat de planner zou doen en waarom. Pas met de schakelaar **Control heat pump** wordt er echt geschreven. Zet je die uit, dan gaat de streeftemperatuur terug naar normaal.

> **Let op, weersafhankelijke regeling:** staat *Weather compensation* aan in de warmtepomp, dan rekent de pomp zelf zijn doeltemperatuur uit en negeert hij de streeftemperatuur van het buffervat. Gebruik dan de kamerthermostaat-sturing hieronder (of laat de buffervat-entiteit leeg).

### Kamerthermostaat (sinds 5.3.0, optioneel)

Het huis is een veel grotere warmtebuffer dan 100 L. Daarom kan de planner ook het setpoint van de kamerthermostaat (Resideo T6) een klein beetje verschuiven, met dezelfde regels voor goedkoop, duur en zonne-overschot als hierboven:

| situatie | setpoint (standaard) |
|---|---|
| goedkoop of zonne-overschot | jouw setpoint + 0,5 K (voorverwarmen), nooit boven 22 °C |
| duur | jouw setpoint − 0,5 K, nooit onder 17 °C (ook bij warmtevraag) |
| anders | jouw setpoint |

- De verschuiving is altijd ten opzichte van het setpoint dat jij of het thermostaatprogramma heeft ingesteld. Zet jij het setpoint zelf anders terwijl de planner het verschoven heeft, dan wordt jouw waarde de nieuwe basis en wacht de planner tot de prijsstand verandert.
- Een setpoint boven het maximum of onder het minimum (bijv. nachtverlaging naar 15 °C) laat de planner staan.
- Hooguit één wijziging per *Minimum time between changes* (standaard 30 min).
- Zet je **Control thermostat** uit, dan zet de planner jouw setpoint terug.
- Dit werkt ook met weersafhankelijke regeling aan: de T6 schakelt de circulatiepomp, de warmtepomp volgt vanzelf.

**Instellen:** Configureren → **Heat pump**: kies bij *Room thermostat* de T6 (`climate.thermostaat_t6_thermostat`) en stel in de groep *Room thermostat* de stappen en grenzen in. Een buffervat-entiteit is niet nodig. De sensor **Thermostat target temperature** laat zien wat de planner zou doen; pas met de schakelaar **Control thermostat** wordt er geschreven. De entiteiten uit het package `warmtepomp.yaml` (`sensor.wp_buffer_temperatuur`, `sensor.wp_buiten_temperatuur`, `number.warmtepomp_temperatuur`) worden automatisch voorgesteld.

## Saldering

- **Automatisch** (standaard): t/m 31-12-2026 is terugleveren evenveel waard als de afnameprijs van dat kwartier, vanaf 1-1-2027 marktprijs + opslag (€ 0,0182). Dit wordt per kwartier bepaald, dus ook de jaarwissel gaat goed.
- Saldering geldt alleen tot je jaarafname. Lever je over het jaar netto méér terug dan je afneemt, kies dan *Geen saldering*.

## Dashboard

In [`dashboard/battery_planner_dashboard.yaml`](dashboard/battery_planner_dashboard.yaml) staat een kant-en-klaar dashboard met drie tabbladen:

| tabblad | inhoud |
|---|---|
| **Overview** | huidige modus, volgende actie, SOC en doel-SOC, verwachte besparing, schakelaar *Control inverter* en knop *Recalculate plan*; vermogens nu (zon, huis, accu, net) en de actuele afname- en terugleverprijs; grafiek met prijzen per kwartier, gekleurd per geplande actie (laden, ontladen, vasthouden), plus de geplande SOC; tabel met de geplande blokken; plandetails (kosten met en zonder plan, verwachte zon en verbruik, laatste opdrachten naar de omvormer) |
| **Frank prices** | actuele prijzen; *optimal cheap* en *optimal expensive period* (aan/uit, sinds wanneer en het tijdvak); goedkoopste en duurste kwartier van vandaag en morgen; gemiddelde prijs; staafgrafiek van vandaag en morgen |
| **Inverter** | informatielijsten (geen grafieken): status, omvormertemperatuur, Storage Mode, netladen, netspanning en -frequentie, alarmcode; accu: SOC, SOH, temperatuur (BMS), spanning, stroom, vermogen, BMS-laad-/ontlaadlimieten, overdischarge- en force-charge-SOC; PV-strings; de Time-Charging-instellingen die de planner schrijft; energie vandaag |

**Installeren**

1. Installeer via HACS → Frontend de kaart **apexcharts-card** (als je die nog niet hebt).
2. Ga naar Instellingen → Dashboards → **+ Dashboard toevoegen** → *Nieuw dashboard vanaf nul*. Noem het *Battery Planner* en open het.
3. Klik op ✏️ (bewerken) → ⋮ → **Ruwe configuratie-editor**, vervang alles door de inhoud van het bestand en klik op **Opslaan**.

De entity-ID's gaan uit van een installatie vanaf 5.0.x, Solis Modbus met apparaatnaam *PV omvormer* en Frank Quarter Prices. Toont een kaart een gele waarschuwing, dan heet die entiteit bij jou anders. Zoek de juiste naam op in Ontwikkelaarshulpmiddelen → Statussen en pas hem aan in de ruwe configuratie-editor. De Frank *optimal cheap/expensive period*-sensoren heten `binary_sensor.frank_optimal_cheap_period` en `binary_sensor.frank_optimal_expensive_period`.

Elk item in het attribuut `slots` van de Mode-sensor is `[tijd_ms, modus (Z/V/L/O), soc%, afnameprijs, terugleverprijs, pv_kW, verbruik_kW]`. Gebruik dat als je zelf grafieken wilt maken.

## Problemen oplossen

| symptoom | oplossing |
|---|---|
| *Batterij Planner* niet te vinden bij Integratie toevoegen | map staat niet in `config/custom_components/batterij_planner`, of je hebt niet herstart; browsercache legen |
| "Deze sensor heeft geen 'prices'-attribuut" | kies de Frank Quarter Prices-sensor `..._prices_today`, niet de huidige prijs |
| Modus-sensor heeft attribuut `fout` | daarin staat wat ontbreekt (SOC onbekend / geen prijzen) |
| Omvormer reageert niet | Configureren → Omvormer: entiteiten controleren; logboek bekijken |

Extra logging aanzetten:

```yaml
logger:
  logs:
    custom_components.batterij_planner: debug
```

## Versiegeschiedenis

### 5.3.0
- Nieuw: vermogensstappen. Laden en ontladen kan nu ook op 33 % of 66 % van het maximale vermogen (in plaats van alleen vol vermogen). Aan/uit via *Settings → Battery → Power steps 33 % / 66 %* (standaard aan). De stap staat in de blokken (`vermogen_pct`), *Next action* en de melding; de laad-/ontlaadstroom volgt de stap.
- Nieuw: sturing van de kamerthermostaat (Resideo T6), optioneel met eigen schakelaar *Control thermostat* en sensor *Thermostat target temperature*. Voorverwarmen (+0,5 K) in goedkope of zonnige kwartieren, −0,5 K in dure kwartieren, altijd ten opzichte van jouw eigen setpoint; uitzetten zet jouw setpoint terug. Werkt ook als de warmtepomp op weersafhankelijke regeling staat.
- Warmtepomp: de buffervat-entiteit is nu optioneel, zodat je alleen de thermostaat kunt laten sturen. Uitleg over weersafhankelijke regeling toegevoegd.
- Entiteiten uit het package `warmtepomp.yaml` en de T6 worden voorgesteld bij het instellen.
- Dashboard: thermostaatkaart in de sectie Heat pump.
- Tests (`tests/`) staan nu in de repository.

### 5.2.2
- Warmtepomp: minimum streeftemperatuur standaard 25 °C (was 20 °C), maximum 35 °C. Met normaal 25 °C wordt er in dure uren dus niet verlaagd, alleen in goedkope of zonnige uren verhoogd naar 28 °C.

### 5.2.1
- Warmtepomp: standaardwaarden afgestemd op lagetemperatuurverwarming: normaal 25 °C, +3 K / −3 K, grenzen 20–35 °C (was 45 °C, ±5 K, 35–55 °C). Een al opgeslagen instelling blijft staan.
- Uitleg wat K (kelvin) betekent bij verhogen en verlagen.

### 5.2.0
- Nieuw: warmtepompsturing (eerste versie). Verschuift de streeftemperatuur van het buffervat naar goedkope en zonnige uren en verlaagt hem in dure uren; respecteert de warmtevraag van de thermostaat, min/max-temperatuur en een minimale tijd tussen wijzigingen. Eigen schakelaar *Control heat pump* en sensor *Heat pump target temperature*.
- Dashboard: sectie Heat pump op het tabblad Overview.

### 5.1.1
- Kant-en-klaar dashboard (`dashboard/battery_planner_dashboard.yaml`) met de tabbladen Overview, Frank prices (met optimal cheap/expensive periods) en Inverter (temperaturen, accu-, net- en PV-gegevens als informatielijst).

### 5.1.0
- Alle schermen in het Engels, met de namen uit Solis Modbus (Battery SOC, Household load power, Time-Charging Charge Start (Slot 1), Storage Mode, …).
- Elk veld heeft een uitgebreide uitleg: wat het doet, welke entiteit je kiest en wat een hogere of lagere waarde betekent.
- Instellingen zijn opgedeeld in vijf groepen: Battery, Prices and feed-in, Forecasts, Inverter control, Notifications.
- Entiteiten hebben Engelse namen (Mode, Expected saving, Next action, Control inverter, …). Bestaande entity-ID's blijven gelijk.
- Melding met het plan van morgen en foutmeldingen in het Engels, beter leesbaar (tijden, SOC en gemiddelde prijs per blok).

### 5.0.2
- Instellingenscherm opent nu echt. Velden zonder eenheid (zoals de PV-correctiefactor) gaven een lege eenheid mee, die Home Assistant weigert. Daardoor kwam er nog steeds een lege foutmelding.

### 5.0.1
- Instellingenscherm (Configureren → Instellingen) opent weer. Twee velden hadden een stapgrootte die Home Assistant weigert, waardoor je een lege foutmelding kreeg.
- Links naar deze repository in het manifest.
- Releases worden automatisch aangemaakt, zodat HACS versienummers toont in plaats van commitcodes.

### 5.0.0
- Eerste versie als integratie, in te stellen via het scherm. Volgt de YAML-/python_script-versie op.
