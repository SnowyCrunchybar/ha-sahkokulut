"""The Sähkökulut integration."""
from __future__ import annotations

from datetime import datetime
import voluptuous as vol

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util

from .calculator import (
    get_daily_fixed_fee_eur,
    get_solar_credit_eur_per_kwh,
    get_total_price_eur_per_kwh,
)
from .const import (
    CONF_ENERGY_SENSOR,
    CONF_INCLUDE_MONTHLY_FEES,
    CONF_SOLAR_DEDUCT_FROM_TOTAL,
    CONF_SOLAR_SENSOR,
    CONF_SPOT_SENSOR,
    DOMAIN,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_RECALCULATE = "recalculate_period"
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("start_time"): cv.datetime,
        vol.Required("end_time"): cv.datetime,
        vol.Optional("consumption_effect_cents"): vol.Coerce(float),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sähkökulut from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_recalculate(call: ServiceCall) -> None:
        """Laske aikavälin tilastot uudelleen toteutuneella kulutusvaikutuksella ja aurinkohyvityksellä."""
        start_dt: datetime = dt_util.as_utc(call.data["start_time"])
        end_dt: datetime = dt_util.as_utc(call.data["end_time"])
        effect_cents: float | None = call.data.get("consumption_effect_cents")

        config = {**entry.data, **entry.options}
        energy_entity = config[CONF_ENERGY_SENSOR]
        solar_entity = config.get(CONF_SOLAR_SENSOR)
        spot_entity = config.get(CONF_SPOT_SENSOR)
        deduct_solar = bool(solar_entity and config.get(CONF_SOLAR_DEDUCT_FROM_TOTAL, True))
        include_fees = bool(config.get(CONF_INCLUDE_MONTHLY_FEES, True))
        cost_entity = f"sensor.{DOMAIN}_kertynyt_kustannus"

        query_entities = {energy_entity, cost_entity}
        if deduct_solar and solar_entity:
            query_entities.add(solar_entity)
        if spot_entity:
            query_entities.add(spot_entity)

        stats = await get_instance(hass).async_add_executor_job(
            statistics_during_period,
            hass,
            start_dt,
            end_dt,
            query_entities,
            "hour",
            None,
            {"change", "mean", "sum"},
        )

        energy_rows = stats.get(energy_entity, [])
        cost_rows = stats.get(cost_entity, [])
        if not energy_rows:
            return

        solar_by_ts: dict[float, float] = {}
        if deduct_solar and solar_entity and solar_entity in stats:
            for row in stats[solar_entity]:
                solar_by_ts[float(row["start"])] = max(0.0, float(row.get("change") or 0.0))

        spot_by_ts: dict[float, float] = {}
        if spot_entity and spot_entity in stats:
            for row in stats[spot_entity]:
                if row.get("mean") is not None:
                    spot_by_ts[float(row["start"])] = float(row["mean"])

        base_sum = 0.0
        if cost_rows:
            first_cost = cost_rows[0]
            base_sum = float(first_cost.get("sum") or 0.0) - float(first_cost.get("change") or 0.0)

        running_sum = base_sum
        updated_points: list[StatisticData] = []
        for row in energy_rows:
            ts = float(row["start"])
            dt_point = dt_util.utc_from_timestamp(ts)
            local_point = dt_util.as_local(dt_point)
            delta_kwh = max(0.0, float(row.get("change") or 0.0))
            delta_solar_kwh = solar_by_ts.get(ts, 0.0)
            spot_val = spot_by_ts.get(ts)

            price_eur = get_total_price_eur_per_kwh(
                dt_point,
                config,
                spot_price_cents=spot_val,
                custom_consumption_effect_cents=effect_cents,
            )
            credit_eur = (
                get_solar_credit_eur_per_kwh(config, spot_price_cents=spot_val)
                if delta_solar_kwh > 0
                else 0.0
            )
            fee_eur = (
                get_daily_fixed_fee_eur(dt_point, config)
                if (include_fees and local_point.hour == 0)
                else 0.0
            )
            running_sum = max(
                0.0, running_sum + (delta_kwh * price_eur) + fee_eur - (delta_solar_kwh * credit_eur)
            )
            updated_points.append(
                StatisticData(start=dt_point, state=running_sum, sum=running_sum)
            )

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Kertynyt kustannus",
            source="recorder",
            statistic_id=cost_entity,
            unit_of_measurement=CURRENCY_EURO,
        )
        async_import_statistics(hass, metadata, updated_points)

    hass.services.async_register(
        DOMAIN, SERVICE_RECALCULATE, handle_recalculate, schema=SERVICE_SCHEMA
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
