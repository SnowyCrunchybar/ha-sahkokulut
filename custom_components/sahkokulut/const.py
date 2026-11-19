"""Constants for the Sähkökulut integration."""

DOMAIN = "sahkokulut"

# Mittaus- ja laskentatavat
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_TRANSFER_SENSOR = "transfer_sensor"
CONF_SOURCE_TYPE = "source_type"
SOURCE_REALTIME = "realtime"
SOURCE_DELAYED_STATS = "delayed_stats"

CONF_CALC_MODE = "calc_mode"
MODE_TRANSFER_ONLY = "transfer_only"
MODE_TOTAL = "total"

# Verkkoyhtiö ja siirtotariffit
CONF_DSO_PRODUCT = "dso_product"
CONF_AUTO_UPDATE_TARIFF = "auto_update_tariff"
CONF_TARIFF_TYPE = "tariff_type"
TARIFF_GENERAL = "general"
TARIFF_TIME = "time"
TARIFF_SEASONAL = "seasonal"

CONF_TRANSFER_DAY = "transfer_day"        # snt/kWh (yleissiirto, päivä tai talviarkipäivä)
CONF_TRANSFER_NIGHT = "transfer_night"    # snt/kWh (yö tai muu aika)
CONF_ELECTRICITY_TAX = "electricity_tax"  # snt/kWh (sähkövero + huoltovarmuusmaksu)
CONF_DAY_START = "day_start"              # esim. 7
CONF_DAY_END = "day_end"                  # esim. 22
CONF_SATURDAY_WINTER = "saturday_winter"  # Lasketaanko lauantai talviarkipäiväksi
CONF_TRANSFER_MONTHLY = "transfer_monthly"

# Energiasopimus
CONF_CONTRACT_TYPE = "contract_type"
CONTRACT_FIXED = "fixed"
CONTRACT_SPOT = "spot"
CONTRACT_HYBRID = "hybrid"  # Välkkysähkö

CONF_FIXED_PRICE = "fixed_price"          # snt/kWh (kiinteä tai välkyn perushinta)
CONF_SPOT_SENSOR = "spot_sensor"          # esim. sensor.nordpool_kwh_fi_eur_3_10_0255
CONF_MARGIN = "margin"                    # snt/kWh (marginaali)
CONF_ENERGY_MONTHLY = "energy_monthly"    # €/kk

# Oletusarvot (Suomi, sis. ALV 25,5 %)
DEFAULT_TAX = 2.827515
DEFAULT_DAY_START = 7
DEFAULT_DAY_END = 22
