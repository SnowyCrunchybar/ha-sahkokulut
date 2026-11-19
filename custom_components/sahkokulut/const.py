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

# Verkkoyhtiö, sulakekoko ja siirtotariffit
CONF_DSO_PRODUCT = "dso_product"
CONF_FUSE_SIZE = "fuse_size"
CONF_AUTO_UPDATE_TARIFF = "auto_update_tariff"
CONF_INCLUDE_MONTHLY_FEES = "include_monthly_fees"
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
CONF_HAS_SPOT = "has_spot"                # Onko pörssisähkö / hintasensori käytössä
CONF_CONTRACT_TYPE = "contract_type"
CONTRACT_FIXED = "fixed"
CONTRACT_SPOT = "spot"
CONTRACT_HYBRID = "hybrid"  # Välkkysähkö

CONF_FIXED_PRICE = "fixed_price"          # snt/kWh (kiinteä tai välkyn perushinta)
CONF_SPOT_SENSOR = "spot_sensor"          # esim. sensor.nordpool tai muu hintasensori
CONF_MARGIN = "margin"                    # snt/kWh (marginaali)
CONF_ENERGY_MONTHLY = "energy_monthly"    # €/kk

# Aurinkopaneelin tuotto ja myyntihyvitys
<<<<<<< Updated upstream
CONF_SOLAR_SENSOR = "solar_sensor"                  # Myynti- tai tuotantosensori (kWh)
CONF_SOLAR_SOURCE_TYPE = "solar_source_type"        # realtime tai delayed_stats
CONF_SOLAR_MODE = "solar_mode"                      # surplus_spot tai rented_credit
SOLAR_MODE_SURPLUS = "surplus_spot"
SOLAR_MODE_RENTED = "rented_credit"
CONF_SOLAR_MARGIN = "solar_margin"                  # Myynnin välityspalkkio (snt/kWh)
CONF_SOLAR_TRANSFER_FEE = "solar_transfer_fee"      # Tuotannon siirtomaksu (snt/kWh)
CONF_SOLAR_SPOT_VAT_INCLUDED = "solar_spot_vat"     # Poistetaanko 25,5 % ALV spot-hinnasta myyntiin
CONF_SOLAR_DEDUCT_FROM_TOTAL = "solar_deduct_total" # Vähennetäänkö hyvitys kertyneestä kustannuksesta
=======
CONF_HAS_SOLAR = "has_solar"                         # Onko aurinkopaneeli / nimikkopaneeli käytössä
CONF_SOLAR_PANEL_OWNERSHIP = "solar_panel_ownership" # "own" (oma paneeli) tai "rented" (nimikkopaneeli / vuokra)
PANEL_OWN = "own"
PANEL_RENTED = "rented"

CONF_SOLAR_SENSOR = "solar_sensor"                   # Myynti- tai tuotantosensori (kWh)
CONF_SOLAR_SOURCE_TYPE = "solar_source_type"         # realtime tai delayed_stats
CONF_SOLAR_MODE = "solar_mode"                       # surplus_spot tai rented_credit
SOLAR_MODE_SURPLUS = "surplus_spot"
SOLAR_MODE_RENTED = "rented_credit"
CONF_SOLAR_MONTHLY_FEE = "solar_monthly_fee"         # Paneelin / sopimuksen kuukausimaksu (€/kk)
CONF_SOLAR_MARGIN = "solar_margin"                   # Myynnin välityspalkkio (snt/kWh)
CONF_SOLAR_TRANSFER_FEE = "solar_transfer_fee"       # Tuotannon siirtomaksu (snt/kWh)
CONF_SOLAR_SPOT_VAT_INCLUDED = "solar_spot_vat"      # Poistetaanko 25,5 % ALV spot-hinnasta myyntiin
CONF_SOLAR_DEDUCT_FROM_TOTAL = "solar_deduct_total"  # Vähennetäänkö hyvitys kertyneestä kustannuksesta
>>>>>>> Stashed changes

# Oletusarvot (Suomi, sis. ALV 25,5 %)
DEFAULT_TAX = 2.827515
DEFAULT_DAY_START = 7
DEFAULT_DAY_END = 22
