# Batterij Planner voor Home Assistant

**Versie: 5.1.1** · [Versiegeschiedenis](#versiegeschiedenis) · [Releases](https://github.com/Fripistack/Fripi-Battery-Planner-V1/releases)

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
| **Battery** | capaciteit, min/max SOC, max laad-/ontlaadvermogen, rendement, slijtagekosten per ontladen kWh |
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
| Recalculate plan | `button.batterij_planner_plan_herberekenen` / `button.batterij_planner_recalculate_plan` | direct opnieuw rekenen |

De ruwe status van Mode blijft `zelfverbruik` / `vasthouden` / `laden` / `ontladen`, zodat bestaande automations en dashboards blijven werken. Home Assistant toont die als Self-consumption / Hold / Charge / Discharge.

## Hoe de omvormer wordt aangestuurd

De planner gebruikt alleen TOU-slot 1 en schrijft alleen als een waarde echt verandert:

| modus | laadslot 1 | ontlaadslot 1 |
|---|---|---|
| zelfverbruik | 00:00–00:00 (uit) | 00:00–00:00 (uit) |
| laden | nu → einde blok, max stroom | uit |
| vasthouden | nu → einde blok, 0 A | uit |
| ontladen | uit | nu → einde blok, max stroom |

Stroom = vermogen ÷ accuspanning (3000 W ÷ 51,2 V = 58 A). Een blok dat over middernacht loopt, wordt tot 23:59 gezet en na middernacht opnieuw. Ontbreken gegevens (SOC onbekend, geen prijzen), dan valt de planner terug op zelfverbruik.

Twee dingen moet je één keer zelf testen:

- **Vasthouden:** controleer op een zonnig uur dat de accu met een laadslot op 0 A echt stilstaat.
- **Laden uit het net:** dat werkt alleen als *Allow grid charging* aan staat op de omvormer.

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
