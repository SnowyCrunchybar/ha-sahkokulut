"""Config flow for Sähkökulut integration with manual DSO & tariff entry."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant, callback
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
    CONF_INCLUDE_MONTHLY_FEES,
    CONF_MARGIN,
    CONF_SATURDAY_WINTER,
    CONF_SOLAR_DEDUCT_FROM_TOTAL,
    CONF_SOLAR_MARGIN,
    CONF_SOLAR_MODE,
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
    MODE_TOTAL,
    MODE_TRANSFER_ONLY,
    SOLAR_MODE_RENTED,
    SOLAR_MODE_SURPLUS,
    SOURCE_DELAYED_STATS,
    SOURCE_REALTIME,
    TARIFF_GENERAL,
    TARIFF_SEASONAL,
    TARIFF_TIME,
)

KNOWN_DELAYED_PLATFORMS = ("elenia", "caruna", "helen", "alva", "fortum", "fingrid", "datahub")
KNOWN_SPOT_KEYWORDS = ("nordpool", "entsoe", "sahkon_hinta_nyt", "spot", "porssi")
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
    """Skannaa asennetut kulutus-, siirto-, aurinko- ja pörssisähkösensorit."""
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
        friendly_name = state.attributes.get("friendly_name", entry.entity_id)

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
            elif any(k in platform or k in eid_lower for k in KNOWN_SPOT_KEYWORDS) or "price" in eid_lower or "hinta" in eid_lower:
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
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SahkokulutOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Aloitus: skannaa olemassa olevat anturit."""
        self._discovered = discover_electricity_entities(self.hass)

        has_known_energy = any(
            e["source_type"] == SOURCE_DELAYED_STATS for e in self._discovered["energy"]
        )
        if (
            has_known_energy
            or self._discovered["solar"]
            or self._discovered["transfer"]
            or self._discovered["spot"]
        ):
            return await self.async_step_discover()

        return await self.async_step_manual_setup()

    async def async_step_discover(self, user_input: dict[str, Any] | None = None):
        """Vaihe 1A: Ehdotetaan tunnistettuja antureita."""
        if user_input is not None:
            if user_input.get("use_discovered"):
                selected_energy = user_input.get("discovered_energy")
                selected_solar = user_input.get("discovered_solar")
                selected_transfer = user_input.get("discovered_transfer")
                selected_spot = user_input.get("discovered_spot")

                if selected_energy:
                    self._data[CONF_ENERGY_SENSOR] = selected_energy
                    match = next(
                        (e for e in self._discovered["energy"] if e["entity_id"] == selected_energy),
                        None,
                    )
                    self._data[CONF_SOURCE_TYPE] = (
                        match["source_type"] if match else SOURCE_DELAYED_STATS
                    )

                if selected_solar:
                    self._data[CONF_SOLAR_SENSOR] = selected_solar
                    smatch = next(
                        (s for s in self._discovered["solar"] if s["entity_id"] == selected_solar),
                        None,
                    )
                    self._data[CONF_SOLAR_SOURCE_TYPE] = (
                        smatch["source_type"] if smatch else SOURCE_REALTIME
                    )
                    self._data[CONF_SOLAR_MODE] = (
                        SOLAR_MODE_RENTED
                        if (smatch and smatch.get("is_rented_solar"))
                        else SOLAR_MODE_SURPLUS
                    )

                if selected_transfer:
                    self._data[CONF_TRANSFER_SENSOR] = selected_transfer

                if selected_spot:
                    self._data[CONF_SPOT_SENSOR] = selected_spot
                    self._data[CONF_CONTRACT_TYPE] = CONTRACT_SPOT

                self._data[CONF_CALC_MODE] = user_input[CONF_CALC_MODE]
                return await self.async_step_transfer()

            return await self.async_step_manual_setup()

        energy_options = [
            {"value": e["entity_id"], "label": e["label"]}
            for e in self._discovered["energy"]
        ]
        solar_options = [{"value": "", "label": "Ei aurinkopaneelia / ei käytössä"}] + [
            {"value": s["entity_id"], "label": s["label"]}
            for s in self._discovered["solar"]
        ]
        transfer_options = [{"value": "", "label": "Ei erillistä siirtosensoria (syötän siirtohinnat)"}] + [
            {"value": t["entity_id"], "label": t["label"]}
            for t in self._discovered["transfer"]
        ]
        spot_options = [{"value": "", "label": "Ei käytössä / syötän myöhemmin"}] + [
            {"value": s["entity_id"], "label": s["label"]}
            for s in self._discovered["spot"]
        ]

        default_energy = next(
            (e["entity_id"] for e in self._discovered["energy"] if e["source_type"] == SOURCE_DELAYED_STATS),
            energy_options[0]["value"] if energy_options else "",
        )
        default_solar = self._discovered["solar"][0]["entity_id"] if self._discovered["solar"] else ""
        default_transfer = self._discovered["transfer"][0]["entity_id"] if self._discovered["transfer"] else ""
        default_spot = self._discovered["spot"][0]["entity_id"] if self._discovered["spot"] else ""

        fields: dict[Any, Any] = {
            vol.Required("use_discovered", default=True): bool,
        }
        if energy_options:
            fields[vol.Optional("discovered_energy", default=default_energy)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=energy_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        if len(solar_options) > 1:
            fields[vol.Optional("discovered_solar", default=default_solar)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=solar_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        if len(transfer_options) > 1:
            fields[vol.Optional("discovered_transfer", default=default_transfer)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=transfer_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        if len(spot_options) > 1:
            fields[vol.Optional("discovered_spot", default=default_spot)] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=spot_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )

        fields[vol.Required(CONF_CALC_MODE, default=MODE_TOTAL)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": MODE_TOTAL, "label": "Siirto + Sähköenergia (kokonaiskustannus)"},
                    {"value": MODE_TRANSFER_ONLY, "label": "Pelkkä sähkönsiirto ja sähkövero"},
                ],
                mode=selector.SelectSelectorMode.LIST,
            )
        )

        return self.async_show_form(step_id="discover", data_schema=vol.Schema(fields))

    async def async_step_manual_setup(self, user_input: dict[str, Any] | None = None):
        """Vaihe 1B: Manuaalinen mittarivalinta."""
        if user_input is not None:
            self._data.update(user_input)
            if self._data.get(CONF_SOLAR_SENSOR):
                self._data.setdefault(
                    CONF_SOLAR_SOURCE_TYPE, self._data.get(CONF_SOURCE_TYPE, SOURCE_REALTIME)
                )
            return await self.async_step_transfer()

        schema = vol.Schema(
            {
                vol.Required(CONF_ENERGY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="energy")
                ),
                vol.Required(CONF_SOURCE_TYPE, default=SOURCE_REALTIME): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": SOURCE_REALTIME, "label": "Reaaliaikainen (HAN / Shelly / paikallinen mittari)"},
                            {"value": SOURCE_DELAYED_STATS, "label": "Viiveellä päivittyvä tilasto (Oma Helen / Elenia / Fortum / Datahub)"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_SOLAR_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="energy")
                ),
                vol.Required(CONF_CALC_MODE, default=MODE_TOTAL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": MODE_TOTAL, "label": "Siirto + Sähköenergia (kokonaiskustannus)"},
                            {"value": MODE_TRANSFER_ONLY, "label": "Pelkkä sähkönsiirto ja sähkövero"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="manual_setup", data_schema=schema)

    async def async_step_transfer(self, user_input: dict[str, Any] | None = None):
        """Vaihe 2: Syötä sähkönsiirtoyhtiö, siirtotuote ja maksut."""
        if user_input is not None:
            self._data.update(user_input)
            if self._data[CONF_CALC_MODE] == MODE_TOTAL:
                return await self.async_step_energy()
            if self._data.get(CONF_SOLAR_SENSOR):
                return await self.async_step_solar()
            return self.async_create_entry(title=_build_entry_title(self._data), data=self._data)

        fields: dict[Any, Any] = {
            vol.Required(CONF_DSO_NAME, default=""): str,
            vol.Required(CONF_TARIFF_NAME, default="Yleissiirto"): str,
        }

        if self._data.get(CONF_TRANSFER_SENSOR):
            fields[vol.Required(CONF_ELECTRICITY_TAX, default=DEFAULT_TAX)] = vol.Coerce(float)
            fields[vol.Optional(CONF_TRANSFER_MONTHLY, default=0.0)] = vol.Coerce(float)
            fields[vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=True)] = bool
            return self.async_show_form(step_id="transfer", data_schema=vol.Schema(fields))

        fields.update(
            {
                vol.Required(CONF_TARIFF_TYPE, default=TARIFF_GENERAL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": TARIFF_GENERAL, "label": "Yleissiirto (yksi energiamaksu, esim. Yleissiirto / Yleissiirto 5)"},
                            {"value": TARIFF_TIME, "label": "Aikasiirto (päivä / yö)"},
                            {"value": TARIFF_SEASONAL, "label": "Kausisiirto (talviarkipäivä / muu aika)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_TRANSFER_DAY, default=2.26): vol.Coerce(float),
                vol.Optional(CONF_TRANSFER_NIGHT, default=0.0): vol.Coerce(float),
                vol.Optional(CONF_DAY_START, default=DEFAULT_DAY_START): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=23)
                ),
                vol.Optional(CONF_DAY_END, default=DEFAULT_DAY_END): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=24)
                ),
                vol.Optional(CONF_SATURDAY_WINTER, default=True): bool,
                vol.Required(CONF_ELECTRICITY_TAX, default=DEFAULT_TAX): vol.Coerce(float),
                vol.Optional(CONF_TRANSFER_MONTHLY, default=0.0): vol.Coerce(float),
                vol.Optional(CONF_INCLUDE_MONTHLY_FEES, default=True): bool,
            }
        )
        return self.async_show_form(step_id="transfer", data_schema=vol.Schema(fields))

    async def async_step_energy(self, user_input: dict[str, Any] | None = None):
        """Vaihe 3: Energiasopimuksen tiedot."""
        if user_input is not None:
            self._data.update(user_input)
            if self._data.get(CONF_SOLAR_SENSOR):
                return await self.async_step_solar()
            return self.async_create_entry(title=_build_entry_title(self._data), data=self._data)

        default_contract = self._data.get(CONF_CONTRACT_TYPE, CONTRACT_SPOT)
        default_spot = self._data.get(CONF_SPOT_SENSOR)

        energy_fields: dict[Any, Any] = {
            vol.Required(CONF_CONTRACT_TYPE, default=default_contract): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": CONTRACT_FIXED, "label": "Kiinteähintainen sopimus"},
                        {"value": CONTRACT_SPOT, "label": "Pörssisähkö (Spot + marginaali)"},
                        {"value": CONTRACT_HYBRID, "label": "Välkkysähkö (Kiinteä perushinta + kulutusvaikutus)"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_FIXED_PRICE, default=8.50): vol.Coerce(float),
        }

        if default_spot:
            energy_fields[vol.Optional(CONF_SPOT_SENSOR, default=default_spot)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
        else:
            energy_fields[vol.Optional(CONF_SPOT_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        energy_fields[vol.Optional(CONF_MARGIN, default=0.45)] = vol.Coerce(float)
        energy_fields[vol.Optional(CONF_ENERGY_MONTHLY, default=0.0)] = vol.Coerce(float)

        return self.async_show_form(step_id="energy", data_schema=vol.Schema(energy_fields))

    async def async_step_solar(self, user_input: dict[str, Any] | None = None):
        """Vaihe 4: Aurinkopaneelin tuoton ja myyntihyvityksen asetukset."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=_build_entry_title(self._data), data=self._data)

        default_mode = self._data.get(CONF_SOLAR_MODE, SOLAR_MODE_SURPLUS)
        default_source = self._data.get(CONF_SOLAR_SOURCE_TYPE, SOURCE_REALTIME)

        schema = vol.Schema(
            {
                vol.Required(CONF_SOLAR_MODE, default=default_mode): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": SOLAR_MODE_SURPLUS, "label": "Oma aurinkopaneeli (ylijäämäsähkön myynti verkkoon)"},
                            {"value": SOLAR_MODE_RENTED, "label": "Nimikkopaneeli (esim. Helen Nimikkopaneeli -hyvitys)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_SOLAR_SOURCE_TYPE, default=default_source): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": SOURCE_REALTIME, "label": "Reaaliaikainen (HAN-vienti / invertteri)"},
                            {"value": SOURCE_DELAYED_STATS, "label": "Viiveellä päivittyvä tilasto (Oma Helen / Datahub)"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(CONF_SOLAR_DEDUCT_FROM_TOTAL, default=True): bool,
                vol.Optional(CONF_SOLAR_MARGIN, default=0.30): vol.Coerce(float),
                vol.Optional(CONF_SOLAR_TRANSFER_FEE, default=0.0): vol.Coerce(float),
                vol.Required(CONF_SOLAR_SPOT_VAT_INCLUDED, default=True): bool,
            }
        )
        return self.async_show_form(step_id="solar", data_schema=schema)


class SahkokulutOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow siirtotuotteen ja hintojen muokkaamiseen."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        fields: dict[Any, Any] = {
            vol.Optional(
                CONF_DSO_NAME, default=current.get(CONF_DSO_NAME, "")
            ): str,
            vol.Optional(
                CONF_TARIFF_NAME, default=current.get(CONF_TARIFF_NAME, "Yleissiirto")
            ): str,
            vol.Required(
                CONF_TRANSFER_DAY, default=current.get(CONF_TRANSFER_DAY, 2.26)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_TRANSFER_NIGHT, default=current.get(CONF_TRANSFER_NIGHT, 0.0)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_TRANSFER_MONTHLY, default=current.get(CONF_TRANSFER_MONTHLY, 0.0)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_ENERGY_MONTHLY, default=current.get(CONF_ENERGY_MONTHLY, 0.0)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_INCLUDE_MONTHLY_FEES, default=current.get(CONF_INCLUDE_MONTHLY_FEES, True)
            ): bool,
            vol.Required(
                CONF_ELECTRICITY_TAX, default=current.get(CONF_ELECTRICITY_TAX, DEFAULT_TAX)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_FIXED_PRICE, default=current.get(CONF_FIXED_PRICE, 8.50)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_MARGIN, default=current.get(CONF_MARGIN, 0.45)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_SOLAR_MARGIN, default=current.get(CONF_SOLAR_MARGIN, 0.30)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_SOLAR_TRANSFER_FEE, default=current.get(CONF_SOLAR_TRANSFER_FEE, 0.0)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_SOLAR_DEDUCT_FROM_TOTAL,
                default=current.get(CONF_SOLAR_DEDUCT_FROM_TOTAL, True),
            ): bool,
        }
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
