"""Config flow and options flow for Sähkökulut integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    CONF_CALC_MODE,
    CONF_CONTRACT_TYPE,
    CONF_DAY_END,
    CONF_DAY_START,
    CONF_DSO_NAME,
    CONF_ELECTRICITY_TAX,
    CONF_ENERGY_MONTHLY,
    CONF_ENERGY_SENSOR,
    CONF_FIXED_PRICE,
    CONF_FOLLOW_MODE,
    CONF_INCLUDE_MONTHLY_FEES,
    CONF_MARGIN,
    CONF_OPEN_SOLAR_OPTIONS,
    CONF_SATURDAY_WINTER,
    CONF_SOLAR_DEDUCT_FROM_TOTAL,
    CONF_SOLAR_MARGIN,
    CONF_SOLAR_MODE,
    CONF_SOLAR_MONTHLY_FEE,
    CONF_SOLAR_OPTION,
    CONF_SOLAR_SENSOR,
    CONF_SOLAR_SOURCE_TYPE,
    CONF_SOLAR_SPOT_VAT_INCLUDED,
    CONF_SOLAR_TRANSFER_FEE,
    CONF_SOURCE_TYPE,
    CONF_SPOT_SENSOR,
    CONF_TARIFF_NAME,
    CONF_TARIFF_TYPE,
    CONF_TRANSFER_DAY,
    CONF_TRANSFER_MONTHLY,
    CONF_TRANSFER_NIGHT,
    CONF_TRANSFER_SENSOR,
    CONTRACT_FIXED,
    CONTRACT_HYBRID,
    CONTRACT_SPOT,
    DEFAULT_DAY_END,
    DEFAULT_DAY_START,
    DEFAULT_TAX,
    DOMAIN,
    FOLLOW_FIXED_TRANSFER,
    FOLLOW_HYBRID_TRANSFER,
    FOLLOW_SPOT_TRANSFER,
    FOLLOW_TRANSFER_ONLY,
    MODE_TOTAL,
    MODE_TRANSFER_ONLY,
    SOLAR_MODE_RENTED,
    SOLAR_MODE_SURPLUS,
    SOLAR_OPT_NONE,
    SOLAR_OPT_OWN_NO_SELL,
    SOLAR_OPT_OWN_SELL,
    SOLAR_OPT_RENTED,
    SOURCE_DELAYED_STATS,
    SOURCE_REALTIME,
    TARIFF_GENERAL,
    TARIFF_OTHER,
    TARIFF_SEASONAL,
    TARIFF_TIME,
)

KNOWN_DELAYED_PLATFORMS = ("elenia", "caruna", "helen", "alva", "fortum", "fingrid", "datahub")
KNOWN_SPOT_KEYWORDS = ("nordpool", "entsoe", "sahkon_hinta_nyt", "spot", "porssi", "hinta")
TRANSFER_KEYWORDS = ("siirto", "transfer", "distribution", "verkko")
SOLAR_KEYWORDS = ("solar", "aurinko", "tuotto", "export", "myynti", "return", "nimikkopaneeli")


def _build_entry_title(data: dict[str, Any]) -> str:
    """Muodosta selkeä otsikko syötetystä siirtoyhtiöstä ja tuotteesta."""
    dso_name = str(data.get(CONF_DSO_NAME, "")).strip()
    tariff_name = str(data.get(CONF_TARIFF_NAME, "")).strip()
    parts = [p for p in (dso_name, tariff_name) if p]
    if parts:
        return f"Sähkökulut ({' – '.join(parts)})"
    if data.get(CONF_CALC_MODE) == MODE_TRANSFER_ONLY:
        return "Sähkökulut (Siirto)"
    return "Sähkökulut"


def discover_electricity_entities(hass: HomeAssistant) -> dict[str, Any]:
    """Skannaa asennetut kulutus-, siirto-, aurinko- ja hintasensorit."""
    ent_reg = er.async_get(hass)
    discovered_energy: list[dict[str, Any]] = []
    discovered_solar: list[dict[str, Any]] = []
    discovered_transfer: list[dict[str, str]] = []
    discovered_spot: list[dict[str, str]] = []

    for entry in ent_reg.entities.values():
        if entry.domain != "sensor" or entry.disabled:
            continue

        state = hass.states.get(entry.entity_id)
        if not state:
            continue

        device_class = state.attributes.get("device_class")
        unit = str(state.attributes.get("unit_of_measurement", "")).lower()
        platform = (entry.platform or "").lower()
        eid_lower = entry.entity_id.lower()
        friendly_name = str(state.attributes.get("friendly_name", entry.entity_id))

        is_delayed = any(k in platform or k in eid_lower for k in KNOWN_DELAYED_PLATFORMS)

        if device_class == SensorDeviceClass.ENERGY or unit == "kwh":
            is_solar = any(k in eid_lower or k in friendly_name.lower() for k in SOLAR_KEYWORDS)
            item = {
                "entity_id": entry.entity_id,
                "label": f"{friendly_name} ({entry.entity_id})",
                "source_type": SOURCE_DELAYED_STATS if is_delayed else SOURCE_REALTIME,
                "is_rented_solar": "rented_solar" in eid_lower or "nimikkopaneeli" in friendly_name.lower(),
            }
            if is_solar:
                discovered_solar.append(item)
            else:
                discovered_energy.append(item)

        is_price_unit = any(u in unit for u in ("snt/kwh", "c/kwh", "eur/kwh", "€/kwh"))
        if is_price_unit:
            is_transfer = any(k in eid_lower or k in friendly_name.lower() for k in TRANSFER_KEYWORDS)
            if is_transfer:
                discovered_transfer.append(
                    {
                        "entity_id": entry.entity_id,
                        "label": f"{friendly_name} ({entry.entity_id})",
                    }
                )
            elif any(k in platform or k in eid_lower for k in KNOWN_SPOT_KEYWORDS) or "price" in eid_lower:
                discovered_spot.append(
                    {
                        "entity_id": entry.entity_id,
                        "label": f"{friendly_name} ({entry.entity_id})",
                    }
                )

    return {
        "energy": discovered_energy,
        "solar": discovered_solar,
        "transfer": discovered_transfer,
        "spot": discovered_spot,
    }


class SahkokulutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sähkökulut."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._discovered: dict[str, Any] = {}

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return SahkokulutOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Vaihe 1: Mitä haluat seurata + täppi lisävalinnoille (aurinkopaneelit)."""
        self._discovered = discover_electricity_entities(self.hass)

        if user_input is not None:
            follow_mode = user_input[CONF_FOLLOW_MODE]
            open_solar = bool(user_input.get(CONF_OPEN_SOLAR_OPTIONS, False))

            self._data[CONF_FOLLOW_MODE] = follow_mode
            self._data[CONF_OPEN_SOLAR_OPTIONS] = open_solar

            if follow_mode == FOLLOW_TRANSFER_ONLY:
                self._data[CONF_CALC_MODE] = MODE_TRANSFER_ONLY
                self._data[CONF_CONTRACT_TYPE] = CONTRACT_FIXED
                self._data[CONF_SPOT_SENSOR] = None
            elif follow_mode == FOLLOW_SPOT_TRANSFER:
                self._data[CONF_CALC_MODE] = MODE_TOTAL
                self._data[CONF_CONTRACT_TYPE] = CONTRACT_SPOT
            elif follow_mode == FOLLOW_HYBRID_TRANSFER:
                self._data[CONF_CALC_MODE] = MODE_TOTAL
                self._data[CONF_CONTRACT_TYPE] = CONTRACT_HYBRID
            else:
                self._data[CONF_CALC_MODE] = MODE_TOTAL
                self._data[CONF_CONTRACT_TYPE] = CONTRACT_FIXED
                self._data[CONF_SPOT_SENSOR] = None

            if not open_solar:
                self._data[CONF_SOLAR_OPTION] = SOLAR_OPT_NONE
                self._data[CONF_SOLAR_SENSOR] = None
                self._data[CONF_SOLAR_MONTHLY_FEE] = 0.0
                self._data[CONF_SOLAR_DEDUCT_FROM_TOTAL] = False

            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required(CONF_FOLLOW_MODE, default=FOLLOW_SPOT_TRANSFER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": FOLLOW_SPOT_TRANSFER, "label": "Pörssisähkö + siirto"},
                            {"value": FOLLOW_FIXED_TRANSFER, "label": "Kiinteähintainen sopimus + siirto"},
                            {"value": FOLLOW_HYBRID_TRANSFER, "label": "Hybridisopimus (Välkkysähkö) + siirto"},
                            {"value": FOLLOW_TRANSFER_ONLY, "label": "Pelkkä sähkönsiirto ja sähkövero"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_OPEN_SOLAR_OPTIONS, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None):
        """Vaihe 2: Kulutusmittari ja mahdollinen hintasensori."""
        follow_mode = self._data.get(CONF_FOLLOW_MODE, FOLLOW_SPOT_TRANSFER)
        open_solar = bool(self._data.get(CONF_OPEN_SOLAR_OPTIONS, False))
        needs_price_sensor = follow_mode in (FOLLOW_SPOT_TRANSFER, FOLLOW_HYBRID_TRANSFER)

        if user_input is not None:
            energy_sensor = user_input.get("discovered_energy") or user_input.get(CONF_ENERGY_SENSOR)
            if energy_sensor:
                self._data[CONF_ENERGY_SENSOR] = energy_sensor
                match = next(
                    (e for e in self._discovered["energy"] if e["entity_id"] == energy_sensor),
                    None,
                )
                self._data[CONF_SOURCE_TYPE] = (
                    user_input.get(CONF_SOURCE_TYPE)
                    or (match["source_type"] if match else SOURCE_DELAYED_STATS)
                )

            if needs_price_sensor:
                spot_sensor = user_input.get("discovered_spot") or user_input.get(CONF_SPOT_SENSOR)
                self._data[CONF_SPOT_SENSOR] = spot_sensor or None

            transfer_sensor = user_input.get("discovered_transfer")
            if transfer_sensor:
                self._data[CONF_TRANSFER_SENSOR] = transfer_sensor

            if open_solar:
                return await self.async_step_solar()
            return await self.async_step_transfer_type()

        energy_options = [
            {"value": e["entity_id"], "label": e["label"]}
            for e in self._discovered["energy"]
        ]
        spot_options = [{"value": "", "label": "Valitse hintasensori itse tai jätä tyhjäksi"}] + [
            {"value": s["entity_id"], "label": s["label"]}
            for s in self._discovered["spot"]
        ]
        transfer_options = [{"value": "", "label": "Ei erillistä siirtosensoria (syötän siirtohinnat)"}] + [
            {"value": t["entity_id"], "label": t["label"]}
            for t in self._discovered["transfer"]
        ]

        default_energy = next(
            (e["entity_id"] for e in self._discovered["energy"] if e["source_type"] == SOURCE_DELAYED_STATS),
            energy_options[0]["value"] if energy_options else "",
        )
        default_spot = self._discovered["spot"][0]["entity_id"] if self._discovered["spot"] else ""
        default_transfer = self._discovered["transfer"][0]["entity_id"] if self._discovered["transfer"] else ""

        fields: dict[Any, Any] = {}
        if energy_options:
            fields[vol.Required("discovered_energy", default=default_energy)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=energy_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        else:
            fields[vol.Required(CONF_ENERGY_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )

        fields[vol.Required(CONF_SOURCE_TYPE, default=SOURCE_DELAYED_STATS)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": SOURCE_DELAYED_STATS, "label": "Viiveellä päivittyvä tilasto (Oma Helen / Elenia / Fortum / Datahub)"},
                    {"value": SOURCE_REALTIME, "label": "Reaaliaikainen (HAN / Shelly / paikallinen mittari)"},
                ],
                mode=selector.SelectSelectorMode.LIST,
            )
        )

        if needs_price_sensor:
            if len(spot_options) > 1:
                fields[vol.Optional("discovered_spot", default=default_spot)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(options=spot_options, mode=selector.SelectSelectorMode.DROPDOWN)
                )
            fields[vol.Optional(CONF_SPOT_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        if len(transfer_options) > 1:
            fields[vol.Optional("discovered_transfer", default=default_transfer)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=transfer_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )

        return self.async_show_form(step_id="sensors", data_schema=vol.Schema(fields))

    async def async_step_solar(self, user_input: dict[str, Any] | None = None):
        """Vaihe 3: Aurinkopaneeli / tuottotapa."""
        if user_input is not None:
            solar_option = user_input[CONF_SOLAR_OPTION]
            self._data[CONF_SOLAR_OPTION] = solar_option

            if solar_option == SOLAR_OPT_NONE:
                self._data[CONF_SOLAR_SENSOR] = None
                self._data[CONF_SOLAR_MONTHLY_FEE] = 0.0
                self._data[CONF_SOLAR_DEDUCT_FROM_TOTAL] = False
                return await self.async_step_transfer_type()

            if solar_option == SOLAR_OPT_RENTED:
                self._data[CONF_SOLAR_MODE] = SOLAR_MODE_RENTED
                self._data[CONF_SOLAR_SOURCE_TYPE] = SOURCE_DELAYED_STATS
                self._data[CONF_SOLAR_DEDUCT_FROM_TOTAL] = False
                default_rented_sensor = (
                    self._discovered["solar"][0]["entity_id"] if self._discovered["solar"] else None
                )
                self._data[CONF_SOLAR_SENSOR] = default_rented_sensor
                return await self.async_step_solar_rented()

            solar_sensor = user_input.get("discovered_solar") or user_input.get(CONF_SOLAR_SENSOR)
            self._data[CONF_SOLAR_SENSOR] = solar_sensor or None
            self._data[CONF_SOLAR_MONTHLY_FEE] = 0.0
            self._data[CONF_SOLAR_SOURCE_TYPE] = SOURCE_REALTIME

            if solar_option == SOLAR_OPT_OWN_SELL:
                self._data[CONF_SOLAR_MODE] = SOLAR_MODE_SURPLUS
                self._data[CONF_SOLAR_DEDUCT_FROM_TOTAL] = True
            elif solar_option == SOLAR_OPT_OWN_NO_SELL:
                self._data[CONF_SOLAR_MODE] = SOLAR_MODE_SURPLUS
                self._data[CONF_SOLAR_DEDUCT_FROM_TOTAL] = False

            return await self.async_step_transfer_type()

        solar_options = [{"value": "", "label": "Valitse aurinkosensori itse tai jätä tyhjäksi"}] + [
            {"value": s["entity_id"], "label": s["label"]}
            for s in self._discovered["solar"]
        ]
        default_solar = self._discovered["solar"][0]["entity_id"] if self._discovered["solar"] else ""

        fields: dict[Any, Any] = {
            vol.Required(CONF_SOLAR_OPTION, default=SOLAR_OPT_RENTED): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": SOLAR_OPT_OWN_SELL, "label": "Oma aurinkopaneeli + myynti verkkoon"},
                        {"value": SOLAR_OPT_OWN_NO_SELL, "label": "Oma paneeli – ei myyntiä (esim. oma inventteri / HAN / Epever tms.)"},
                        {"value": SOLAR_OPT_RENTED, "label": "Nimikkopaneeli / vuokrapaneeli (esim. Helen Nimikkopaneeli)"},
                        {"value": SOLAR_OPT_NONE, "label": "Ei aurinkopaneelia"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        }
        if len(solar_options) > 1:
            fields[vol.Optional("discovered_solar", default=default_solar)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=solar_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        fields[vol.Optional(CONF_SOLAR_SENSOR)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        return self.async_show_form(step_id="solar", data_schema=vol.Schema(fields))

    async def async_step_solar_rented(self, user_input: dict[str, Any] | None = None):
        """Vaihe 3B: Vuokrapaneelin / nimikkopaneelin kuukausihinta."""
        if user_input is not None:
            self._data[CONF_SOLAR_MONTHLY_FEE] = float(user_input.get(CONF_SOLAR_MONTHLY_FEE, 0.0))
            self._data[CONF_SOLAR_DEDUCT_FROM_TOTAL] = False
            return await self.async_step_transfer_type()

        schema = vol.Schema(
            {
                vol.Optional(CONF_SOLAR_MONTHLY_FEE, default=0.0): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="solar_rented", data_schema=schema)

    async def async_step_transfer_type(self, user_input: dict[str, Any] | None = None):
        """Vaihe 4A: Sähkönsiirtoyhtiö, siirtotuotteen nimi ja tariffityyppi."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_transfer()

        schema = vol.Schema(
            {
                vol.Required(CONF_DSO_NAME, default=""): str,
                vol.Required(CONF_TARIFF_NAME, default="Yleissiirto"): str,
                vol.Required(CONF_TARIFF_TYPE, default=TARIFF_GENERAL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": TARIFF_GENERAL, "label": "Yleis"},
                            {"value": TARIFF_TIME, "label": "Aika"},
                            {"value": TARIFF_SEASONAL, "label": "Kausi"},
                            {"value": TARIFF_OTHER, "label": "Muu"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="transfer_type", data_schema=schema)

    async def async_step_transfer(self, user_input: dict[str, Any] | None = None):
        """Vaihe 4B: Valittuun siirtotariffiin liittyvät maksut ja ehdot."""
        if user_input is not None:
            self._data.update(user_input)
            if self._data.get(CONF_CALC_MODE) == MODE_TOTAL:
                return await self.async_step_energy()
            return self.async_create_entry(title=_build_entry_title(self._data), data=self._data)

        tariff_type = self._data.get(CONF_TARIFF_TYPE, TARIFF_GENERAL)
        fields: dict[Any, Any] = {}

        if tariff_type == TARIFF_GENERAL:
            fields[vol.Required(CONF_TRANSFER_DAY, default=2.26)] = vol.Coerce(float)
            fields[vol.Optional(CONF_TRANSFER_MONTHLY, default=0.0)] = vol.Coerce(float)
            fields[vol.Required(CONF_ELECTRICITY_TAX, default=DEFAULT_TAX)] = vol.Coerce(float)
            fields[vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=True)] = bool
        elif tariff_type == TARIFF_TIME:
            fields[vol.Required(CONF_TRANSFER_DAY, default=2.26)] = vol.Coerce(float)
            fields[vol.Required(CONF_TRANSFER_NIGHT, default=0.0)] = vol.Coerce(float)
            fields[vol.Optional(CONF_DAY_START, default=DEFAULT_DAY_START)] = vol.All(
                vol.Coerce(int), vol.Range(min=0, max=23)
            )
            fields[vol.Optional(CONF_DAY_END, default=DEFAULT_DAY_END)] = vol.All(
                vol.Coerce(int), vol.Range(min=1, max=24)
            )
            fields[vol.Optional(CONF_TRANSFER_MONTHLY, default=0.0)] = vol.Coerce(float)
            fields[vol.Required(CONF_ELECTRICITY_TAX, default=DEFAULT_TAX)] = vol.Coerce(float)
            fields[vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=True)] = bool
        elif tariff_type == TARIFF_SEASONAL:
            fields[vol.Required(CONF_TRANSFER_DAY, default=3.16)] = vol.Coerce(float)
            fields[vol.Required(CONF_TRANSFER_NIGHT, default=1.92)] = vol.Coerce(float)
            fields[vol.Optional(CONF_DAY_START, default=DEFAULT_DAY_START)] = vol.All(
                vol.Coerce(int), vol.Range(min=0, max=23)
            )
            fields[vol.Optional(CONF_DAY_END, default=DEFAULT_DAY_END)] = vol.All(
                vol.Coerce(int), vol.Range(min=1, max=24)
            )
            fields[vol.Optional(CONF_SATURDAY_WINTER, default=True)] = bool
            fields[vol.Optional(CONF_TRANSFER_MONTHLY, default=0.0)] = vol.Coerce(float)
            fields[vol.Required(CONF_ELECTRICITY_TAX, default=DEFAULT_TAX)] = vol.Coerce(float)
            fields[vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=True)] = bool
        else:
            fields[vol.Required(CONF_TRANSFER_DAY, default=0.0)] = vol.Coerce(float)
            fields[vol.Optional(CONF_TRANSFER_MONTHLY, default=0.0)] = vol.Coerce(float)
            fields[vol.Required(CONF_ELECTRICITY_TAX, default=DEFAULT_TAX)] = vol.Coerce(float)
            fields[vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=True)] = bool

        return self.async_show_form(step_id="transfer", data_schema=vol.Schema(fields))

    async def async_step_energy(self, user_input: dict[str, Any] | None = None):
        """Vaihe 5: Energiasopimuksen tiedot valitun seurattavan kokonaisuuden mukaan."""
        follow_mode = self._data.get(CONF_FOLLOW_MODE, FOLLOW_SPOT_TRANSFER)

        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=_build_entry_title(self._data), data=self._data)

        fields: dict[Any, Any] = {}
        default_spot = self._data.get(CONF_SPOT_SENSOR)

        if follow_mode == FOLLOW_FIXED_TRANSFER:
            fields[vol.Required(CONF_FIXED_PRICE, default=8.50)] = vol.Coerce(float)
            fields[vol.Optional(CONF_MARGIN, default=0.0)] = vol.Coerce(float)
            fields[vol.Optional(CONF_ENERGY_MONTHLY, default=0.0)] = vol.Coerce(float)
        elif follow_mode == FOLLOW_HYBRID_TRANSFER:
            fields[vol.Required(CONF_FIXED_PRICE, default=8.50)] = vol.Coerce(float)
            if default_spot:
                fields[vol.Optional(CONF_SPOT_SENSOR, default=default_spot)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )
            else:
                fields[vol.Optional(CONF_SPOT_SENSOR)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )
            fields[vol.Optional(CONF_MARGIN, default=0.0)] = vol.Coerce(float)
            fields[vol.Optional(CONF_ENERGY_MONTHLY, default=0.0)] = vol.Coerce(float)
        else:
            if default_spot:
                fields[vol.Optional(CONF_SPOT_SENSOR, default=default_spot)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )
            else:
                fields[vol.Optional(CONF_SPOT_SENSOR)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )
            fields[vol.Optional(CONF_MARGIN, default=0.45)] = vol.Coerce(float)
            fields[vol.Optional(CONF_ENERGY_MONTHLY, default=0.0)] = vol.Coerce(float)

        return self.async_show_form(step_id="energy", data_schema=vol.Schema(fields))


class SahkokulutOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow hintojen, perusmaksujen ja antureiden muokkaamiseen."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Näytä ja tallenna hinnat, perusmaksut ja anturit."""
        current: dict[str, Any] = {}
        if self._config_entry.data:
            current.update(self._config_entry.data)
        if self._config_entry.options:
            current.update(self._config_entry.options)

        if user_input is not None:
            cleaned: dict[str, Any] = dict(user_input)
            for key in (CONF_ENERGY_SENSOR, CONF_SPOT_SENSOR, CONF_TRANSFER_SENSOR, CONF_SOLAR_SENSOR):
                if key in cleaned and not cleaned[key]:
                    cleaned[key] = None
            return self.async_create_entry(title="", data=cleaned)

        default_energy = str(current.get(CONF_ENERGY_SENSOR) or "")
        default_spot = str(current.get(CONF_SPOT_SENSOR) or "")
        default_transfer = str(current.get(CONF_TRANSFER_SENSOR) or "")
        default_solar = str(current.get(CONF_SOLAR_SENSOR) or "")

        fields: dict[Any, Any] = {
            vol.Optional(CONF_DSO_NAME, default=str(current.get(CONF_DSO_NAME) or "")): str,
            vol.Optional(CONF_TARIFF_NAME, default=str(current.get(CONF_TARIFF_NAME) or "Yleissiirto")): str,
            vol.Required(CONF_TRANSFER_DAY, default=float(current.get(CONF_TRANSFER_DAY) or 2.26)): vol.Coerce(float),
            vol.Optional(CONF_TRANSFER_NIGHT, default=float(current.get(CONF_TRANSFER_NIGHT) or 0.0)): vol.Coerce(float),
            vol.Optional(CONF_TRANSFER_MONTHLY, default=float(current.get(CONF_TRANSFER_MONTHLY) or 0.0)): vol.Coerce(float),
            vol.Optional(CONF_ENERGY_MONTHLY, default=float(current.get(CONF_ENERGY_MONTHLY) or 0.0)): vol.Coerce(float),
            vol.Optional(CONF_SOLAR_MONTHLY_FEE, default=float(current.get(CONF_SOLAR_MONTHLY_FEE) or 0.0)): vol.Coerce(float),
            vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=bool(current.get(CONF_INCLUDE_MONTHLY_FEES, True))): bool,
            vol.Required(CONF_ELECTRICITY_TAX, default=float(current.get(CONF_ELECTRICITY_TAX) or DEFAULT_TAX)): vol.Coerce(float),
            vol.Optional(CONF_FIXED_PRICE, default=float(current.get(CONF_FIXED_PRICE) or 8.50)): vol.Coerce(float),
            vol.Optional(CONF_MARGIN, default=float(current.get(CONF_MARGIN) or 0.0)): vol.Coerce(float),
            vol.Optional(CONF_SOLAR_MARGIN, default=float(current.get(CONF_SOLAR_MARGIN) or 0.30)): vol.Coerce(float),
            vol.Optional(CONF_SOLAR_TRANSFER_FEE, default=float(current.get(CONF_SOLAR_TRANSFER_FEE) or 0.0)): vol.Coerce(float),
            vol.Optional(
                CONF_SOLAR_DEDUCT_FROM_TOTAL,
                default=bool(current.get(CONF_SOLAR_DEDUCT_FROM_TOTAL, True)),
            ): bool,
        }

        if default_energy:
            fields[vol.Required(CONF_ENERGY_SENSOR, default=default_energy)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )
        else:
            fields[vol.Required(CONF_ENERGY_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )

        if default_spot:
            fields[vol.Optional(CONF_SPOT_SENSOR, default=default_spot)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
        else:
            fields[vol.Optional(CONF_SPOT_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        if default_transfer:
            fields[vol.Optional(CONF_TRANSFER_SENSOR, default=default_transfer)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
        else:
            fields[vol.Optional(CONF_TRANSFER_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        if default_solar:
            fields[vol.Optional(CONF_SOLAR_SENSOR, default=default_solar)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )
        else:
            fields[vol.Optional(CONF_SOLAR_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            )

        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
