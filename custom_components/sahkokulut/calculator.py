"""Tariff and price calculation helpers for Sähkökulut."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_CALC_MODE,
    CONF_CONTRACT_TYPE,
    CONF_DAY_END,
    CONF_DAY_START,
    CONF_ELECTRICITY_TAX,
    CONF_FIXED_PRICE,
    CONF_MARGIN,
    CONF_SATURDAY_WINTER,
    CONF_TARIFF_TYPE,
    CONF_TRANSFER_DAY,
    CONF_TRANSFER_NIGHT,
    CONTRACT_FIXED,
    CONTRACT_HYBRID,
    CONTRACT_SPOT,
    DEFAULT_DAY_END,
    DEFAULT_DAY_START,
    DEFAULT_TAX,
    MODE_TRANSFER_ONLY,
    TARIFF_GENERAL,
    TARIFF_SEASONAL,
    TARIFF_TIME,
)


def is_day_or_winter_weekday(dt_obj: datetime, config: dict[str, Any]) -> bool:
    """Tarkista kuuluuko annettu paikallinen aikaleima kalliimpaan siirtoaikaan."""
    local_dt = dt_util.as_local(dt_obj)
    tariff = config.get(CONF_TARIFF_TYPE, TARIFF_GENERAL)

    if tariff == TARIFF_GENERAL:
        return True

    day_start = int(config.get(CONF_DAY_START, DEFAULT_DAY_START))
    day_end = int(config.get(CONF_DAY_END, DEFAULT_DAY_END))
    in_day_hours = day_start <= local_dt.hour < day_end

    if tariff == TARIFF_TIME:
        return in_day_hours

    if tariff == TARIFF_SEASONAL:
        is_winter_month = local_dt.month in (11, 12, 1, 2, 3)
        if not is_winter_month:
            return False
        max_weekday = 5 if config.get(CONF_SATURDAY_WINTER, True) else 4
        return local_dt.weekday() <= max_weekday and in_day_hours

    return True


def get_transfer_price_cents(
    dt_obj: datetime,
    config: dict[str, Any],
    external_transfer_cents: float | None = None,
) -> float:
    """Palauta siirtohinta + sähkövero yksikössä snt/kWh."""
    if external_transfer_cents is not None:
        tax = float(config.get(CONF_ELECTRICITY_TAX, 0.0))
        return external_transfer_cents + tax

    tax = float(config.get(CONF_ELECTRICITY_TAX, DEFAULT_TAX))
    if is_day_or_winter_weekday(dt_obj, config):
        transfer = float(config.get(CONF_TRANSFER_DAY, 0.0))
    else:
        transfer = float(config.get(CONF_TRANSFER_NIGHT, 0.0))
    return transfer + tax


def get_total_price_eur_per_kwh(
    dt_obj: datetime,
    config: dict[str, Any],
    spot_price_cents: float | None = None,
    custom_consumption_effect_cents: float | None = None,
    external_transfer_cents: float | None = None,
) -> float:
    """Laske kokonaishinta yksikössä €/kWh."""
    total_cents = get_transfer_price_cents(dt_obj, config, external_transfer_cents)

    if config.get(CONF_CALC_MODE) == MODE_TRANSFER_ONLY:
        return round(total_cents / 100.0, 6)

    contract = config.get(CONF_CONTRACT_TYPE, CONTRACT_FIXED)
    margin = float(config.get(CONF_MARGIN, 0.0))
    fixed = float(config.get(CONF_FIXED_PRICE, 0.0))

    if contract == CONTRACT_FIXED:
        total_cents += fixed
    elif contract == CONTRACT_SPOT:
        spot = spot_price_cents if spot_price_cents is not None else 0.0
        total_cents += spot + margin
    elif contract == CONTRACT_HYBRID:
        if custom_consumption_effect_cents is not None:
            total_cents += fixed + margin + custom_consumption_effect_cents
        else:
            spot = spot_price_cents if spot_price_cents is not None else 0.0
            total_cents += fixed + margin + (spot - fixed)

    return round(total_cents / 100.0, 6)
