"""Sensor platform for Sähkökulut."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .calculator import (
    get_daily_fixed_fee_eur,
    get_solar_credit_eur_per_kwh,
    get_total_price_eur_per_kwh,
    get_transfer_price_cents,
)
from .const import (
    CONF_DSO_NAME,
    CONF_ENERGY_SENSOR,
    CONF_INCLUDE_MONTHLY_FEES,
    CONF_SOLAR_DEDUCT_FROM_TOTAL,
    CONF_SOLAR_SENSOR,
    CONF_SOLAR_SOURCE_TYPE,
    CONF_SOURCE_TYPE,
    CONF_SPOT_SENSOR,
    CONF_TARIFF_NAME,
    CONF_TRANSFER_MONTHLY,
    CONF_TRANSFER_SENSOR,
    SOURCE_REALTIME,
)

_LOGGER = logging.getLogger(__name__)


def _read_price_sensor_cents(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Lue hintasensorin tila ja muunna tarvittaessa €/kWh -> snt/kWh."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    try:
        val = float(state.state)
        unit = str(state.attributes.get("unit_of_measurement", ""))
        return val * 100.0 if ("EUR" in unit or "€" in unit) else val
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sähkökulut sensors from a config entry."""
    config = {**entry.data, **entry.options}
    entities: list[SensorEntity] = [
        SahkokulutCurrentPriceSensor(entry, config),
        SahkokulutTransferPriceSensor(entry, config),
        SahkokulutTotalCostSensor(hass, entry, config),
    ]
    if config.get(CONF_SOLAR_SENSOR):
        entities.append(SahkokulutSolarPriceSensor(entry, config))
        entities.append(SahkokulutSolarCreditSensor(hass, entry, config))

    async_add_entities(entities)


class SahkokulutCurrentPriceSensor(SensorEntity):
    """Reaaliaikainen ostosähkön kokonaishinta (€/kWh) – suoraan Energy Dashboardiin."""

    _attr_has_entity_name = True
    _attr_name = "Hinta nyt"
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._entry = entry
        self._config = config
        self._attr_unique_id = f"{entry.entry_id}_current_price"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "dso_name": self._config.get(CONF_DSO_NAME, ""),
            "tariff_name": self._config.get(CONF_TARIFF_NAME, ""),
        }

    @property
    def native_value(self) -> float:
        spot_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_SPOT_SENSOR))
        transfer_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_TRANSFER_SENSOR))
        return get_total_price_eur_per_kwh(
            dt_util.now(),
            self._config,
            spot_price_cents=spot_cents,
            external_transfer_cents=transfer_cents,
        )


class SahkokulutTransferPriceSensor(SensorEntity):
    """Pelkkä siirtohinta + vero (snt/kWh) informatiiviseen seurantaan."""

    _attr_has_entity_name = True
    _attr_name = "Siirtohinta nyt"
    _attr_native_unit_of_measurement = "snt/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._attr_unique_id = f"{entry.entry_id}_transfer_price"
        self._config = config

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "dso_name": self._config.get(CONF_DSO_NAME, ""),
            "tariff_name": self._config.get(CONF_TARIFF_NAME, ""),
        }

    @property
    def native_value(self) -> float:
        transfer_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_TRANSFER_SENSOR))
        return round(get_transfer_price_cents(dt_util.now(), self._config, transfer_cents), 3)


class SahkokulutSolarPriceSensor(SensorEntity):
    """Aurinkosähkön myynti- / hyvityshinta nyt (€/kWh) Energy Dashboardin Return to grid -kohtaan."""

    _attr_has_entity_name = True
    _attr_name = "Myyntihinta nyt"
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4

    def __init__(self, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self._attr_unique_id = f"{entry.entry_id}_solar_price"
        self._config = config

    @property
    def native_value(self) -> float:
        spot_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_SPOT_SENSOR))
        return get_solar_credit_eur_per_kwh(self._config, spot_price_cents=spot_cents)


class SahkokulutSolarCreditSensor(RestoreEntity, SensorEntity):
    """Kertynyt aurinkopaneelin myynti- / tuotantohyvitys (€)."""

    _attr_has_entity_name = True
    _attr_name = "Myyntihyvitys"
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self.hass = hass
        self._entry = entry
        self._config = config
        self._attr_unique_id = f"{entry.entry_id}_solar_credit"
        self._total_credit: float = 0.0
        self._last_solar_kwh: float | None = None

    @property
    def native_value(self) -> float:
        return round(self._total_credit, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"last_solar_kwh": self._last_solar_kwh}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._total_credit = float(last_state.state)
            except ValueError:
                self._total_credit = 0.0
            if "last_solar_kwh" in last_state.attributes and last_state.attributes["last_solar_kwh"] is not None:
                self._last_solar_kwh = float(last_state.attributes["last_solar_kwh"])

        solar_entity = self._config.get(CONF_SOLAR_SENSOR)
        if not solar_entity:
            return

        solar_source = self._config.get(CONF_SOLAR_SOURCE_TYPE, SOURCE_REALTIME)
        if solar_source == SOURCE_REALTIME:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [solar_entity], self._handle_realtime_solar_change
                )
            )
        else:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._sync_delayed_solar_statistics, timedelta(hours=1)
                )
            )
            self.hass.async_create_task(self._sync_delayed_solar_statistics(dt_util.now()))

    @callback
    def _handle_realtime_solar_change(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            current_kwh = float(new_state.state)
        except ValueError:
            return

        if self._last_solar_kwh is None:
            self._last_solar_kwh = current_kwh
            self.async_write_ha_state()
            return

        delta_kwh = current_kwh - self._last_solar_kwh
        if delta_kwh > 0:
            spot_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_SPOT_SENSOR))
            credit_price = get_solar_credit_eur_per_kwh(self._config, spot_price_cents=spot_cents)
            self._total_credit += delta_kwh * credit_price
            self._last_solar_kwh = current_kwh
            self.async_write_ha_state()
        elif delta_kwh < 0:
            self._last_solar_kwh = current_kwh
            self.async_write_ha_state()

    async def _sync_delayed_solar_statistics(self, _now: datetime) -> None:
        solar_entity = self._config.get(CONF_SOLAR_SENSOR)
        spot_entity = self._config.get(CONF_SPOT_SENSOR)
        if not solar_entity:
            return

        start_time = dt_util.utcnow() - timedelta(days=7)
        end_time = dt_util.utcnow()
        stats_entities = {solar_entity}
        if spot_entity:
            stats_entities.add(spot_entity)

        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            stats_entities,
            "hour",
            None,
            {"change", "mean", "sum"},
        )

        solar_rows = stats.get(solar_entity, [])
        if not solar_rows:
            return

        spot_by_ts: dict[float, float] = {}
        if spot_entity and spot_entity in stats:
            for row in stats[spot_entity]:
                if row.get("mean") is not None:
                    spot_by_ts[row["start"]] = float(row["mean"])

        last_own = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, self.entity_id, True, {"sum"}
        )
        running_sum = 0.0
        last_ts = 0.0
        if self.entity_id in last_own and last_own[self.entity_id]:
            running_sum = float(last_own[self.entity_id][0].get("sum") or 0.0)
            last_ts = float(last_own[self.entity_id][0]["start"])

        new_points: list[StatisticData] = []
        for row in solar_rows:
            ts = float(row["start"])
            if ts <= last_ts:
                continue
            delta_kwh = max(0.0, float(row.get("change") or 0.0))
            dt_point = dt_util.utc_from_timestamp(ts)
            credit_eur = get_solar_credit_eur_per_kwh(self._config, spot_price_cents=spot_by_ts.get(ts))
            running_sum += delta_kwh * credit_eur
            new_points.append(
                StatisticData(start=dt_point, state=running_sum, sum=running_sum)
            )

        if new_points:
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=self.name,
                source="recorder",
                statistic_id=self.entity_id,
                unit_of_measurement=CURRENCY_EURO,
            )
            async_import_statistics(self.hass, metadata, new_points)
            self._total_credit = running_sum
            self.async_write_ha_state()


class SahkokulutTotalCostSensor(RestoreEntity, SensorEntity):
    """Kertynyt nettosähkökustannus (€), sisältää haluttaessa päiväkohtaiset perusmaksut ja aurinkohyvityksen."""

    _attr_has_entity_name = True
    _attr_name = "Kertynyt kustannus"
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: dict[str, Any]) -> None:
        self.hass = hass
        self._entry = entry
        self._config = config
        self._attr_unique_id = f"{entry.entry_id}_total_cost"
        self._total_cost: float = 0.0
        self._last_kwh: float | None = None
        self._last_solar_kwh: float | None = None
        self._last_fee_date: str | None = None

    @property
    def native_value(self) -> float:
        return round(self._total_cost, 4)

    async def async_added_to_hass(self) -> None:
        """Palauta edellinen tila ja käynnistä seuranta."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._total_cost = float(last_state.state)
            except ValueError:
                self._total_cost = 0.0
            if "last_kwh" in last_state.attributes and last_state.attributes["last_kwh"] is not None:
                self._last_kwh = float(last_state.attributes["last_kwh"])
            if "last_solar_kwh" in last_state.attributes and last_state.attributes["last_solar_kwh"] is not None:
                self._last_solar_kwh = float(last_state.attributes["last_solar_kwh"])
            if "last_fee_date" in last_state.attributes and last_state.attributes["last_fee_date"] is not None:
                self._last_fee_date = str(last_state.attributes["last_fee_date"])

        if self._config.get(CONF_INCLUDE_MONTHLY_FEES, True):
            self.async_on_remove(
                async_track_time_change(
                    self.hass, self._handle_daily_fixed_fee, hour=0, minute=1, second=0
                )
            )

        source_type = self._config.get(CONF_SOURCE_TYPE, SOURCE_REALTIME)
        energy_entity = self._config[CONF_ENERGY_SENSOR]
        solar_entity = self._config.get(CONF_SOLAR_SENSOR)
        deduct_solar = bool(solar_entity and self._config.get(CONF_SOLAR_DEDUCT_FROM_TOTAL, True))
        solar_source = self._config.get(CONF_SOLAR_SOURCE_TYPE, SOURCE_REALTIME)

        if source_type == SOURCE_REALTIME:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [energy_entity], self._handle_realtime_change
                )
            )
        else:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._sync_delayed_statistics, timedelta(hours=1)
                )
            )
            self.hass.async_create_task(self._sync_delayed_statistics(dt_util.now()))

        if deduct_solar and solar_source == SOURCE_REALTIME:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [solar_entity], self._handle_realtime_solar_deduction
                )
            )

    @callback
    def _handle_daily_fixed_fee(self, now: datetime) -> None:
        """Lisää päiväkohtainen perusmaksu kerran vuorokaudessa."""
        today_str = dt_util.as_local(now).date().isoformat()
        if self._last_fee_date == today_str:
            return
        daily_fee = get_daily_fixed_fee_eur(now, self._config)
        if daily_fee > 0:
            self._total_cost += daily_fee
            self._last_fee_date = today_str
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "dso_name": self._config.get(CONF_DSO_NAME, ""),
            "tariff_name": self._config.get(CONF_TARIFF_NAME, ""),
            "transfer_monthly": self._config.get(CONF_TRANSFER_MONTHLY, 0.0),
            "last_kwh": self._last_kwh,
            "last_solar_kwh": self._last_solar_kwh,
            "last_fee_date": self._last_fee_date,
        }

    @callback
    def _handle_realtime_change(self, event: Event) -> None:
        """Lisää reaaliaikaisen ostosähkön kulutuskustannus."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            current_kwh = float(new_state.state)
        except ValueError:
            return

        if self._last_kwh is None:
            self._last_kwh = current_kwh
            self.async_write_ha_state()
            return

        delta_kwh = current_kwh - self._last_kwh
        if delta_kwh > 0:
            spot_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_SPOT_SENSOR))
            transfer_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_TRANSFER_SENSOR))
            price = get_total_price_eur_per_kwh(
                dt_util.now(),
                self._config,
                spot_price_cents=spot_cents,
                external_transfer_cents=transfer_cents,
            )
            self._total_cost += delta_kwh * price
            self._last_kwh = current_kwh
            self.async_write_ha_state()
        elif delta_kwh < 0:
            self._last_kwh = current_kwh
            self.async_write_ha_state()

    @callback
    def _handle_realtime_solar_deduction(self, event: Event) -> None:
        """Vähennä reaaliaikaisen aurinkotuoton myyntihyvitys kertyneestä kustannuksesta."""
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            current_solar_kwh = float(new_state.state)
        except ValueError:
            return

        if self._last_solar_kwh is None:
            self._last_solar_kwh = current_solar_kwh
            self.async_write_ha_state()
            return

        delta_solar_kwh = current_solar_kwh - self._last_solar_kwh
        if delta_solar_kwh > 0:
            spot_cents = _read_price_sensor_cents(self.hass, self._config.get(CONF_SPOT_SENSOR))
            credit_price = get_solar_credit_eur_per_kwh(self._config, spot_price_cents=spot_cents)
            self._total_cost = max(0.0, self._total_cost - (delta_solar_kwh * credit_price))
            self._last_solar_kwh = current_solar_kwh
            self.async_write_ha_state()
        elif delta_solar_kwh < 0:
            self._last_solar_kwh = current_solar_kwh
            self.async_write_ha_state()

    async def _sync_delayed_statistics(self, _now: datetime) -> None:
        """Synkronoi viiveellä saapuneet kulutus- ja aurinkotilastot."""
        energy_entity = self._config[CONF_ENERGY_SENSOR]
        spot_entity = self._config.get(CONF_SPOT_SENSOR)
        transfer_entity = self._config.get(CONF_TRANSFER_SENSOR)
        solar_entity = self._config.get(CONF_SOLAR_SENSOR)
        deduct_solar = bool(
            solar_entity
            and self._config.get(CONF_SOLAR_DEDUCT_FROM_TOTAL, True)
            and self._config.get(CONF_SOLAR_SOURCE_TYPE) != SOURCE_REALTIME
        )
        include_fees = bool(self._config.get(CONF_INCLUDE_MONTHLY_FEES, True))

        start_time = dt_util.utcnow() - timedelta(days=7)
        end_time = dt_util.utcnow()

        stats_entities = {energy_entity}
        if spot_entity:
            stats_entities.add(spot_entity)
        if transfer_entity:
            stats_entities.add(transfer_entity)
        if deduct_solar and solar_entity:
            stats_entities.add(solar_entity)

        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            stats_entities,
            "hour",
            None,
            {"change", "mean", "sum"},
        )

        energy_rows = stats.get(energy_entity, [])
        if not energy_rows:
            return

        spot_by_ts: dict[float, float] = {}
        if spot_entity and spot_entity in stats:
            for row in stats[spot_entity]:
                if row.get("mean") is not None:
                    spot_by_ts[row["start"]] = float(row["mean"])

        transfer_by_ts: dict[float, float] = {}
        if transfer_entity and transfer_entity in stats:
            for row in stats[transfer_entity]:
                if row.get("mean") is not None:
                    transfer_by_ts[row["start"]] = float(row["mean"])

        solar_by_ts: dict[float, float] = {}
        if deduct_solar and solar_entity and solar_entity in stats:
            for row in stats[solar_entity]:
                solar_by_ts[row["start"]] = max(0.0, float(row.get("change") or 0.0))

        last_own = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, self.entity_id, True, {"sum"}
        )
        running_sum = 0.0
        last_ts = 0.0
        if self.entity_id in last_own and last_own[self.entity_id]:
            running_sum = float(last_own[self.entity_id][0].get("sum") or 0.0)
            last_ts = float(last_own[self.entity_id][0]["start"])

        new_stat_points: list[StatisticData] = []
        for row in energy_rows:
            ts = float(row["start"])
            if ts <= last_ts:
                continue
            delta_kwh = max(0.0, float(row.get("change") or 0.0))
            delta_solar_kwh = solar_by_ts.get(ts, 0.0)

            dt_point = dt_util.utc_from_timestamp(ts)
            local_point = dt_util.as_local(dt_point)
            spot_val = spot_by_ts.get(ts)
            transfer_val = transfer_by_ts.get(ts)
            price_eur = get_total_price_eur_per_kwh(
                dt_point,
                self._config,
                spot_price_cents=spot_val,
                external_transfer_cents=transfer_val,
            )
            credit_eur = (
                get_solar_credit_eur_per_kwh(self._config, spot_price_cents=spot_val)
                if delta_solar_kwh > 0
                else 0.0
            )
            fee_eur = (
                get_daily_fixed_fee_eur(dt_point, self._config)
                if (include_fees and local_point.hour == 0)
                else 0.0
            )
            net_delta = (delta_kwh * price_eur) + fee_eur - (delta_solar_kwh * credit_eur)
            running_sum = max(0.0, running_sum + net_delta)

            new_stat_points.append(
                StatisticData(start=dt_point, state=running_sum, sum=running_sum)
            )

        if new_stat_points:
            metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=self.name,
                source="recorder",
                statistic_id=self.entity_id,
                unit_of_measurement=CURRENCY_EURO,
            )
            async_import_statistics(self.hass, metadata, new_stat_points)
            self._total_cost = running_sum
            self.async_write_ha_state()
