"""Constants for the Sähkökulut integration."""

DOMAIN = "sahkokulut"

# Ensimmäisen sivun seurattava kokonaisuus
CONF_FOLLOW_MODE = "follow_mode"
FOLLOW_SPOT_TRANSFER = "spot_transfer"
FOLLOW_FIXED_TRANSFER = "fixed_transfer"
FOLLOW_HYBRID_TRANSFER = "hybrid_transfer"
FOLLOW_TRANSFER_ONLY = "transfer_only"

# Täppi ekalla sivulla: avaa lisävalinnat (aurinkopaneelit)
CONF_OPEN_SOLAR_OPTIONS = "open_solar_options"

# Aurinkopaneeli / tuottotapa
CONF_SOLAR_OPTION = "solar_option"
SOLAR_OPT_NONE = "none"
SOLAR_OPT_OWN_SELL = "own_sell"
SOLAR_OPT_OWN_NO_SELL = "own_no_sell"
SOLAR_OPT_RENTED = "rented"

# Mittaus- ja laskentatavat
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_TRANSFER_SENSOR = "transfer_sensor"
CONF_SOURCE_TYPE = "source_type"
SOURCE_REALTIME = "realtime"
SOURCE_DELAYED_STATS = "delayed_stats"

CONF_CALC_MODE = "calc_mode"
MODE_TRANSFER_ONLY = "transfer_only"
MODE_TOTAL = "total"

# Verkkoyhtiö, siirtotuote ja siirtotariffit
CONF_DSO_NAME = "dso_name"
CONF_TARIFF_NAME = "tariff_name"
CONF_INCLUDE_MONTHLY_FEES = "include_monthly_fees"
CONF_TARIFF_TYPE = "tariff_type"
TARIFF_GENERAL = "general"
TARIFF_TIME = "time"
TARIFF_SEASONAL = "seasonal"
TARIFF_OTHER = "other"

CONF_TRANSFER_DAY = "transfer_day"
CONF_TRANSFER_NIGHT = "transfer_night"
CONF_ELECTRICITY_TAX = "electricity_tax"
CONF_DAY_START = "day_start"
CONF_DAY_END = "day_end"
CONF_SATURDAY_WINTER = "saturday_winter"
CONF_TRANSFER_MONTHLY = "transfer_monthly"

# Energiasopimus
CONF_CONTRACT_TYPE = "contract_type"
CONTRACT_FIXED = "fixed"
CONTRACT_SPOT = "spot"
CONTRACT_HYBRID = "hybrid"

CONF_FIXED_PRICE = "fixed_price"
CONF_SPOT_SENSOR = "spot_sensor"
CONF_MARGIN = "margin"
CONF_ENERGY_MONTHLY = "energy_monthly"

# Aurinkopaneelin tuotto ja myyntihyvitys
CONF_SOLAR_SENSOR = "solar_sensor"
CONF_SOLAR_SOURCE_TYPE = "solar_source_type"
CONF_SOLAR_MODE = "solar_mode"
SOLAR_MODE_SURPLUS = "surplus_spot"
SOLAR_MODE_RENTED = "rented_credit"
CONF_SOLAR_MONTHLY_FEE = "solar_monthly_fee"
CONF_SOLAR_MARGIN = "solar_margin"
CONF_SOLAR_TRANSFER_FEE = "solar_transfer_fee"
CONF_SOLAR_SPOT_VAT_INCLUDED = "solar_spot_vat"
CONF_SOLAR_DEDUCT_FROM_TOTAL = "solar_deduct_total"

# Oletusarvot (Suomi, sis. ALV 25,5 %)
DEFAULT_TAX = 2.827515
DEFAULT_DAY_START = 7
DEFAULT_DAY_END = 22
