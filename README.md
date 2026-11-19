# Sähkökulut

> **Kehitysvaiheessa:** Integraatiota kehitetään jatkuvasti – testaa ja raportoi havainnot [Issues-sivulla](https://github.com/SnowyCrunchybar/ha-sahkokulut/issues).

[![Lisää HACS:iin](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SnowyCrunchybar&repository=ha-sahkokulut&category=integration)

HACS-yhteensopiva Home Assistant -integraatio sähkön kokonaiskustannusten (sähkönsiirto, sähkövero, sähköenergia, kuukausimaksut ja aurinkotuoton hyvitys) laskentaan ja seurantaan Suomessa.

## Ominaisuudet

- Pörssisähkö-, kiinteähintainen, hybridisopimus- ja pelkän siirron laskenta
- Sähkönsiirtoyhtiön ja siirtotariffin vapaa määritys
- Kertyvä kustannus reaaliaikaisista mittareista ja viiveellä päivittyvistä tilastoista
- Erilliset sähkösopimuksen ja sähkönsiirron perusmaksusensorit
- Vuokra- tai nimikkopaneelien arvioitu energiamaksuhyvitys
- Asetusten, hintojen ja antureiden muokkaus integraation asetuksista
- Välkkysähkön jälkilaskenta `sahkokulut.recalculate_period` -palvelulla

## Asennus HACS:in kautta

1. Klikkaa yllä olevaa **Lisää HACS:iin** -painiketta.
2. Jos asennat käsin, avaa Home Assistantissa **HACS → Integraatiot**.
3. Valitse **Mukautetut tietovarastot** ja lisää `https://github.com/SnowyCrunchybar/ha-sahkokulut`.
4. Valitse kategoriaksi **Integration**, asenna Sähkökulut ja käynnistä Home Assistant uudelleen.
5. Lisää integraatio: **Asetukset → Laitteet ja palvelut → Lisää integraatio → Sähkökulut**.

---

# Electricity Costs

> **Work in progress:** This integration is under active development. Test it and report findings on the [Issues page](https://github.com/SnowyCrunchybar/ha-sahkokulut/issues).

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SnowyCrunchybar&repository=ha-sahkokulut&category=integration)

A HACS-compatible Home Assistant integration for calculating and tracking total electricity costs in Finland: grid charges, electricity tax, energy costs, monthly fees and solar credit.

## Features

- Spot-price, fixed-price, hybrid-contract and grid-only calculations
- Configurable electricity distributor and grid tariff
- Cumulative cost from real-time sensors and delayed recorder statistics
- Separate energy-contract and grid monthly-fee sensors
- Estimated energy-credit sensor for rented or named solar panels
- Editable settings, prices and consumption, spot-price, grid and solar sensors
- Hybrid-contract recalculation through the `sahkokulut.recalculate_period` service

## Installation via HACS

1. Click the **Add to HACS** button above.
2. For a manual setup, open **HACS → Integrations** in Home Assistant.
3. Open **Custom repositories**, add `https://github.com/SnowyCrunchybar/ha-sahkokulut`, and select **Integration**.
4. Install **Sähkökulut** and restart Home Assistant.
5. Add the integration under **Settings → Devices & services → Add integration → Sähkökulut**.
