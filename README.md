# Sähkökulut (`ha-sahkokulut`)

HACS-yhteensopiva Home Assistant -integraatio sähkön kokonaiskustannusten (sähkönsiirto + sähkövero + sähköenergia - aurinkotuoton myyntihyvitys) laskentaan ja seurantaan Suomessa.

## Ominaisuudet

- **Automaattinen tunnistus:** Etsii asennuksessa olemassa olevat kulutus-, siirto-, aurinkotuotto- ja pörssisähkösensorit (esim. *Oma Helen* ml. Nimikkopaneeli, *Elenia*, *Caruna*, *Fortum*, *Fingrid Datahub*, *Nord Pool*, *Entso-E*, *Sähkön hinta nyt*).
- **Aurinkopaneelin tuotto ja myyntihyvitys:** Vähentää verkkoon myydyn ylijäämäsähkön tai Helenin Nimikkopaneelin tuoton (ALV 0 % spot-hinta - välityspalkkio - tuotannon siirtomaksu) suoraan kertyneistä kuluista ja tuottaa erillisen `sensor.sahkokulut_myyntihyvitys` -sensorin Energy Dashboardin *Return to grid* -seurantaan.
- **Siirtohinnastojen esitäyttö & päivitys:** Sisältää yleisimmät verkkoyhtiöt (`tariffs.json`) ja tukee yleissiirtoa, aikasiirtoa (päivä/yö) sekä kausisiirtoa (talviarkipäivä/muu aika).
- **Reaaliaikainen ja viiveellä päivittyvä data:** Toimii sekä paikallisten mittarien (HAN / Shelly) että 1–2 vrk viiveellä päivittyvien tilastointegraatioiden kanssa suoraan Energy Dashboardissa.
- **Välkkysähkön jälkilaskenta:** Palvelukutsu `sahkokulut.recalculate_period` päivittää valitun aikavälin tilastot toteutuneella kulutusvaikutuksella (snt/kWh).

## Asennus (HACS)

1. Avaa Home Assistantissa **HACS → Integraatiot**.
2. Valitse oikeasta yläkulmasta **Mukautetut tietovarastot (Custom repositories)**.
3. Lisää URL `https://github.com/SnowyCrunchybar/ha-sahkokulut` ja valitse kategoriaksi **Integration**.
4. Asenna **Sähkökulut** ja käynnistä Home Assistant uudelleen.
5. Lisää integraatio: **Asetukset → Laitteet ja palvelut → Lisää integraatio → Sähkökulut**.
