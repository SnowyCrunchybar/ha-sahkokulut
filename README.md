# Sähkökulut

> **Work in Progress (WIP):** Tämä integraatio on aktiivisessa kehitysvaiheessa. Laskentaa ja ominaisuuksia parannetaan jatkuvasti – testaa ja raportoi mahdolliset havainnot [Issues-sivulla](https://github.com/SnowyCrunchybar/ha-sahkokulut/issues).

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SnowyCrunchybar&repository=ha-sahkokulut&category=integration)

HACS-yhteensopiva Home Assistant -integraatio sähkön kokonaiskustannusten (sähkönsiirto + sähkövero + sähköenergia + kuukausimaksut - aurinkotuoton myyntihyvitys) laskentaan ja seurantaan Suomessa.

## Käyttöönotto ja ominaisuudet

1. **Ensimmäinen sivu – seurattava kokonaisuus ja lisävalinnat:**
   - **Pörssisähkö + siirto**
   - **Kiinteähintainen sopimus + siirto**
   - **Hybridisopimus (Välkkysähkö) + siirto**
   - **Pelkkä sähkönsiirto ja sähkövero**
   - **Avaa lisävalinnat (aurinkopaneelit)** – avaa aurinkopaneeli-/tuottovaiheen (*Vaihe 3*). Vuokrapaneeli-/nimikkopaneelivaihtoehdossa kysytään vain kuukausimaksu (`€/kk`) ja kerrotaan, että sen tuottama sähkö hyvitetään automaattisesti sähkömyyjän päässä.
2. **Sähkönsiirtoyhtiö ja siirtotariffit:** Syötät vapaasti siirtoyhtiön nimen (esim. *Alva Sähköverkko*), siirtotuotteen nimen (esim. *Yleissiirto*, *Yleissiirto 5*, *Kausisiirto*) ja valitset tariffityypin (**Yleis**, **Aika**, **Kausi** tai **Muu**), jolloin näytetään vain kyseiseen tariffiin liittyvät hinta- ja aikakentät.
3. **Välkkysähkön jälkilaskenta:** Palvelukutsu `sahkokulut.recalculate_period` päivittää valitun aikavälin tilastot toteutuneella kulutusvaikutuksella (`snt/kWh`).

## Asennus (HACS)

Klikkaa yllä olevaa **Add to HACS** -painiketta tai tee asennus käsin:

1. Avaa Home Assistantissa **HACS → Integraatiot**.
2. Valitse oikeasta yläkulmasta **Mukautetut tietovarastot (Custom repositories)**.
3. Lisää URL `https://github.com/SnowyCrunchybar/ha-sahkokulut` ja valitse kategoriaksi **Integration**.
4. Asenna **Sähkökulut** ja käynnistä Home Assistant uudelleen.
5. Lisää integraatio: **Asetukset → Laitteet ja palvelut → Lisää integraatio → Sähkökulut**.
