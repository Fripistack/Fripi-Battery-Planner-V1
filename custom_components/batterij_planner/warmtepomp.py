"""Warmtepomp-sturing: streeftemperatuur van het buffervat op prijs en zonne-overschot.

Geen Home Assistant-afhankelijkheden, zodat de logica los te testen is.

Principe
--------
* Basis-streeftemperatuur, eventueel met een eenvoudige stooklijn (warmer bij kou).
* Goedkoop kwartier (bij de goedkoopste X % van de komende 24 uur) of zonne-overschot:
  buffer hoger zetten ("boost") -> de warmtepomp draait nu, en later minder.
* Duur kwartier (bij de duurste Y %): buffer lager zetten ("verlaagd") -> de warmtepomp
  slaat over, het buffervat en het huis teren even op hun warmte.
  Optioneel niet verlagen zolang de thermostaat warmte vraagt (comfort).
* Grenzen: nooit onder de minimum- of boven de maximumtemperatuur.

Kamerthermostaat (optioneel)
----------------------------
Met weersafhankelijke regeling (WC) aan rekent de warmtepomp zelf het doel van het
buffervat uit en negeert hij de streeftemperatuur. Het huis is bovendien een veel
grotere buffer dan 100 L. Daarom kan de planner ook het setpoint van de
kamerthermostaat (T6) iets verschuiven: + in goedkope/zonnige kwartieren
(voorverwarmen), − in dure kwartieren, steeds ten opzichte van het setpoint dat
de gebruiker of het thermostaatprogramma heeft ingesteld.
"""
from __future__ import annotations

from dataclasses import dataclass

NORMAAL = "normaal"
BOOST = "boost"
VERLAAGD = "verlaagd"


@dataclass
class WpInstellingen:
    basis_temp: float = 25.0
    verhoging: float = 3.0
    verlaging: float = 3.0
    min_temp: float = 25.0
    max_temp: float = 35.0
    goedkoop_aandeel: float = 25.0  # % goedkoopste kwartieren komende 24 uur
    duur_aandeel: float = 25.0  # % duurste kwartieren komende 24 uur
    stooklijn: float = 0.0  # K extra per °C buitentemperatuur onder 15 °C (0 = uit)
    pv_overschot_w: float = 1500.0  # boost bij minstens zoveel zonne-overschot
    pv_min_soc: float = 90.0  # ...en alleen als de thuisaccu (bijna) vol is
    niet_verlagen_bij_vraag: bool = True
    t6_verhoging: float = 0.5  # K hoger (voorverwarmen) bij goedkoop/zon
    t6_verlaging: float = 0.5  # K lager bij duur
    t6_min_temp: float = 17.0
    t6_max_temp: float = 22.0


@dataclass
class WpBesluit:
    doel: float
    stand: str
    reden: str
    basis: float
    prijs_rang: float | None
    # stand op prijs/zon alleen, zonder de uitzondering bij warmtevraag
    # (die geldt voor het buffervat, niet voor de kamerthermostaat)
    prijs_stand: str = NORMAAL


def prijs_rang(huidig: float, komend: list[float]) -> float | None:
    """0 = goedkoopste kwartier van de komende 24 uur, 1 = duurste."""
    if not komend:
        return None
    goedkoper = sum(1 for p in komend if p < huidig - 1e-9)
    gelijk = sum(1 for p in komend if abs(p - huidig) <= 1e-9)
    return (goedkoper + 0.5 * max(0, gelijk - 1)) / max(1, len(komend) - 1)


def bepaal(
    inst: WpInstellingen,
    huidige_prijs: float | None,
    komende_prijzen: list[float],
    buiten_temp: float | None = None,
    pv_overschot_w: float | None = None,
    accu_soc: float | None = None,
    warmtevraag: bool | None = None,
) -> WpBesluit:
    basis = inst.basis_temp
    if inst.stooklijn > 0 and buiten_temp is not None:
        basis += inst.stooklijn * max(0.0, 15.0 - buiten_temp)
    basis = min(max(basis, inst.min_temp), inst.max_temp)

    rang = prijs_rang(huidige_prijs, komende_prijzen) if huidige_prijs is not None else None

    def klem(t: float) -> float:
        return round(min(max(t, inst.min_temp), inst.max_temp), 1)

    zon = (
        pv_overschot_w is not None
        and pv_overschot_w >= inst.pv_overschot_w
        and (accu_soc is None or accu_soc >= inst.pv_min_soc)
    )
    if zon:
        return WpBesluit(klem(basis + inst.verhoging), BOOST,
                         f"Solar surplus {pv_overschot_w:.0f} W and home battery full", basis, rang, BOOST)
    if rang is None:
        return WpBesluit(klem(basis), NORMAAL, "No price information – normal setpoint", basis, rang)
    if rang <= inst.goedkoop_aandeel / 100.0:
        return WpBesluit(klem(basis + inst.verhoging), BOOST,
                         f"Cheap: among the cheapest {inst.goedkoop_aandeel:.0f}% of the next 24 h", basis, rang, BOOST)
    if rang >= 1.0 - inst.duur_aandeel / 100.0:
        if inst.niet_verlagen_bij_vraag and warmtevraag:
            return WpBesluit(klem(basis), NORMAAL,
                             "Expensive, but the thermostat is calling for heat – not lowering", basis, rang, VERLAAGD)
        return WpBesluit(klem(basis - inst.verlaging), VERLAAGD,
                         f"Expensive: among the most expensive {inst.duur_aandeel:.0f}% of the next 24 h", basis, rang,
                         VERLAAGD)
    return WpBesluit(klem(basis), NORMAAL, "Average price – normal setpoint", basis, rang)


def thermostaat_doel(inst: WpInstellingen, basis: float, prijs_stand: str) -> float:
    """Setpoint kamerthermostaat: basis (van gebruiker/programma) ± verschuiving.

    Alleen de verschuiving wordt begrensd: een basis buiten min/max blijft staan.
    Een verschoven setpoint wordt afgerond op 0,5 °C (stapgrootte van de T6).
    """
    if prijs_stand == BOOST:
        doel = min(basis + inst.t6_verhoging, max(inst.t6_max_temp, basis))
    elif prijs_stand == VERLAAGD:
        doel = max(basis - inst.t6_verlaging, min(inst.t6_min_temp, basis))
    else:
        return basis
    return round(doel * 2) / 2
