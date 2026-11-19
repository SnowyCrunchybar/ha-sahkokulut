"""Suomalaisten sähkönsiirtoyhtiöiden hinnastot ja automaattinen haku."""
from __future__ import annotations

import logging
from typing import Any
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import TARIFF_GENERAL, TARIFF_SEASONAL, TARIFF_TIME

_LOGGER = logging.getLogger(__name__)

REMOTE_TARIFFS_URL = (
    "https://raw.githubusercontent.com/SnowyCrunchybar/ha-sahkokulut/main/tariffs.json"
)

BUILTIN_TARIFFS: dict[str, dict[str, Any]] = {
    "helen_yleis": {
        "name": "Helen Sähköverkko – Yleissiirto",
        "provider": "helen",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 4.08,
        "transfer_night": 0.0,
        "transfer_monthly": 5.51,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "helen_aika": {
        "name": "Helen Sähköverkko – Aikasiirto",
        "provider": "helen",
        "tariff_type": TARIFF_TIME,
        "transfer_day": 4.82,
        "transfer_night": 2.46,
        "transfer_monthly": 16.53,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "caruna_yleis": {
        "name": "Caruna – Yleissiirto",
        "provider": "caruna",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 5.29,
        "transfer_night": 0.0,
        "transfer_monthly": 19.90,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "caruna_aika": {
        "name": "Caruna – Yösiirto",
        "provider": "caruna",
        "tariff_type": TARIFF_TIME,
        "transfer_day": 5.95,
        "transfer_night": 3.12,
        "transfer_monthly": 28.50,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "caruna_kausi": {
        "name": "Caruna – Kausisiirto",
        "provider": "caruna",
        "tariff_type": TARIFF_SEASONAL,
        "transfer_day": 6.85,
        "transfer_night": 2.95,
        "transfer_monthly": 28.50,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": True,
    },
    "caruna_espoo_yleis": {
        "name": "Caruna Espoo – Yleissiirto",
        "provider": "caruna_espoo",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 3.92,
        "transfer_night": 0.0,
        "transfer_monthly": 7.90,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "elenia_yleis": {
        "name": "Elenia – Yleissiirto",
        "provider": "elenia",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 5.45,
        "transfer_night": 0.0,
        "transfer_monthly": 18.60,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "elenia_aika": {
        "name": "Elenia – Aikasiirto",
        "provider": "elenia",
        "tariff_type": TARIFF_TIME,
        "transfer_day": 6.10,
        "transfer_night": 3.05,
        "transfer_monthly": 25.40,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "alva_yleis": {
        "name": "Alva Sähköverkko – Yleissiirto",
        "provider": "alva",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 4.35,
        "transfer_night": 0.0,
        "transfer_monthly": 12.90,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "alva_aika": {
        "name": "Alva Sähköverkko – Aikasiirto",
        "provider": "alva",
        "tariff_type": TARIFF_TIME,
        "transfer_day": 4.95,
        "transfer_night": 2.55,
        "transfer_monthly": 19.50,
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
}


async def async_fetch_tariffs(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Hae ajantasaiset verkkoyhtiöiden hinnastot verkosta tai käytä paikallista varmuuskopiota."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(REMOTE_TARIFFS_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                if isinstance(data, dict) and data:
                    return {**BUILTIN_TARIFFS, **data}
    except Exception as err:
        _LOGGER.debug("Etähinnaston haku epäonnistui, käytetään sisäänrakennettua: %s", err)

    return BUILTIN_TARIFFS
