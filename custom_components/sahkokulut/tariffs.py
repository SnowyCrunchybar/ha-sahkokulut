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
        "monthly_fees": {
            "1x25A (kerrostalo)": 5.51,
            "3x25A": 17.85,
            "3x35A": 25.10,
            "3x50A": 35.80,
            "3x63A": 45.20,
        },
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
        "monthly_fees": {
            "1x25A (kerrostalo)": 16.53,
            "3x25A": 22.90,
            "3x35A": 32.40,
            "3x50A": 46.10,
            "3x63A": 58.00,
        },
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
        "monthly_fees": {
            "1x25A (kerrostalo)": 6.95,
            "3x25A": 19.90,
            "3x35A": 29.50,
            "3x50A": 41.90,
            "3x63A": 52.80,
        },
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
        "monthly_fees": {
            "3x25A": 28.50,
            "3x35A": 39.90,
            "3x50A": 56.50,
            "3x63A": 71.20,
        },
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
        "monthly_fees": {
            "3x25A": 28.50,
            "3x35A": 39.90,
            "3x50A": 56.50,
            "3x63A": 71.20,
        },
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
        "monthly_fees": {
            "1x25A (kerrostalo)": 4.90,
            "3x25A": 7.90,
            "3x35A": 12.50,
            "3x50A": 18.20,
            "3x63A": 23.40,
        },
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
        "monthly_fees": {
            "1x25A (kerrostalo)": 7.20,
            "3x25A": 18.60,
            "3x35A": 27.90,
            "3x50A": 39.80,
            "3x63A": 50.20,
        },
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
        "monthly_fees": {
            "3x25A": 25.40,
            "3x35A": 36.80,
            "3x50A": 52.10,
            "3x63A": 65.40,
        },
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "alva_yleis": {
        "name": "Alva Sähköverkko (Jyväskylä) – Yleissiirto",
        "provider": "alva",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 4.35,
        "transfer_night": 0.0,
        "transfer_monthly": 12.90,
        "monthly_fees": {
            "1x25A (kerrostalo)": 5.20,
            "3x25A": 12.90,
            "3x35A": 19.40,
            "3x50A": 27.80,
            "3x63A": 35.10,
        },
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "alva_aika": {
        "name": "Alva Sähköverkko (Jyväskylä) – Aikasiirto",
        "provider": "alva",
        "tariff_type": TARIFF_TIME,
        "transfer_day": 4.95,
        "transfer_night": 2.55,
        "transfer_monthly": 19.50,
        "monthly_fees": {
            "3x25A": 19.50,
            "3x35A": 28.20,
            "3x50A": 39.90,
            "3x63A": 50.40,
        },
        "day_start": 7,
        "day_end": 22,
        "saturday_winter": False,
    },
    "vantaan_energia_yleis": {
        "name": "Vantaan Energia Sähköverkot – Yleissiirto",
        "provider": "vantaan_energia",
        "tariff_type": TARIFF_GENERAL,
        "transfer_day": 3.85,
        "transfer_night": 0.0,
        "transfer_monthly": 5.90,
        "monthly_fees": {