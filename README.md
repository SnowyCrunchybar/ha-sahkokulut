# Sähkökulut

> **Work in Progress (WIP):** Tämä integraatio on aktiivisessa kehitysvaiheessa. Hinnastojen tarkkuutta, laskentaa ja ominaisuuksia parannetaan jatkuvasti – testaa ja raportoi mahdolliset havainnot [Issues-sivulla](https://github.com/SnowyCrunchybar/ha-sahkokulut/issues).

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SnowyCrunchybar&repository=ha-sahkokulut&category=integration)

HACS-yhteensopiva Home Assistant -integraatio sähkön kokonaiskustannusten (sähkönsiirto + sähkövero + sähköenergia + kuukausimaksut - aurinkotuoton myyntihyvitys) laskentaan ja seurantaan Suomessa.

## Ominaisuudet

- **Automaattinen tunnistus:** Etsii asennuksessa olemassa olevat kulutus-, siirto-, aurinkotuotto- ja pörssisähkösensorit (esim. *Oma Helen* ml. Nimikkopaneeli, *Elenia*, *Caruna*, *Fortum*, *Fingrid Datahub*, *Nord Pool*, *Entso-E*, *Sähkön hinta nyt*).
- **Suomen verkkoyhtiöt ja sulakekoot (`tariffs.json`):** Sisältää valmiit hinnastot ja pääsulakekokojen (1x25A – 3x63A) mukaiset perusmaksut useille suomalaisille verkkoyhtiöille (mm. Helen, Caruna, Caruna Espoo, Elenia, Alva, Vantaan Energia, Turku Energia, Oulun Energia, Tampereen Energia, Savon Voima, Kymenlaakson Sähköverkko, PKS, Vaasan Sähköverkko).
- **Automaattinen hinnastopäivitys:** Integraatio tarkistaa kerran vuorokaudessa `tariffs.json`-päivitykset, ja mukana tuleva GitHub Actions -työnkulku valvoo yhtiöiden hinnastomuutoksia viikoittain.
- **Päivittäinen perusmaksujen jyvitys:** Lisää kuukausittaiset perusmaksut (`€/kk / kuukauden päivät`) automaattisesti vuorokauden vaihtuessa kokonaiskustannuksiin (valittavissa asetuksista).
- **Aurinkopaneelin tuotto ja myyntihyvitys:** Vähentää verkkoon myydyn ylijäämäsähkön tai Helenin Nimikkopaneelin tuoton (ALV 0 % spot-hinta - välityspalkkio - tuotannon siirtomaksu) suoraan kertyneistä kuluista ja tuottaa erillisen `sensor.sahkokulut_myyntihyvitys` -sensorin.
- **Välkkysähkön jälkilaskenta:** Palvelukutsu `sahkokulut.recalculate_period` päivittää valitun aikavälin tilastot toteutuneella kulutusvaikutuksella (snt/kWh).

## Asennus (HACS)

Klikkaa yllä olevaa **Add to HACS** -painiketta tai tee asennus käsin:

1. Avaa Home Assistantissa **HACS → Integraatiot**.
2. Valitse oikeasta yläkulmasta **Mukautetut tietovarastot (Custom repositories)**.
3. Lisää URL `https://github.com/SnowyCrunchybar/ha-sahkokulut` ja valitse kategoriaksi **Integration**.
4. Asenna **Sähkökulut** ja käynnistä Home Assistant uudelleen.
5. Lisää integraatio: **Asetukset → Laitteet ja palvelut → Lisää integraatio → Sähkökulut**.
