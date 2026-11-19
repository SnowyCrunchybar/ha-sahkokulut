"""Automaattinen tarkistus- ja päivitysskripti tariffs.json-tiedostolle."""
from __future__ import annotations

import json
from pathlib import Path
import re
import httpx
from bs4 import BeautifulSoup

TARIFFS_PATH = Path(__file__).resolve().parent.parent / "tariffs.json"

# Esimerkkilähteet, joista siirtohintoja voidaan tarkistaa automaattisesti
SCRAPE_TARGETS = {
    "helen_yleis": {
        "url": "https://www.helensahkoverkko.fi/palvelut-ja-hinnat/sahkonsiirron-hinnat/siirtotuotteet-ja-hinnastot",
        "pattern": r"Yleissiirto.*?([0-9]+,[0-9]{2})\s*snt/kWh",
    },
}


def fetch_updated_prices(tariffs: dict) -> bool:
    """Tarkista verkkosivuilta mahdolliset uudet snt/kWh-hinnat ja päivitä sanakirja."""
    changed = False
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for key, cfg in SCRAPE_TARGETS.items():
            if key not in tariffs:
                continue
            try:
                resp = client.get(cfg["url"])
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                text = " ".join(soup.get_text(" ").split())
                match = re.search(cfg["pattern"], text, re.IGNORECASE)
                if match:
                    new_price = float(match.group(1).replace(",", "."))
                    old_price = float(tariffs[key]["transfer_day"])
                    # Hyväksy vain järkevät hinnat (1.0 - 20.0 snt/kWh)
                    if 1.0 <= new_price <= 20.0 and abs(new_price - old_price) > 0.001:
                        print(f"Päivitetään {key}: {old_price} -> {new_price} snt/kWh")
                        tariffs[key]["transfer_day"] = new_price
                        changed = True
            except Exception as err:
                print(f"Virhe haettaessa {key}: {err}")
    return changed


def main() -> None:
    with TARIFFS_PATH.open("r", encoding="utf-8") as f:
        tariffs = json.load(f)

    # Varmistetaan rakenteen eheys ja päivitetään mahdolliset muutokset
    changed = fetch_updated_prices(tariffs)
    if changed:
        with TARIFFS_PATH.open("w", encoding="utf-8") as f:
            json.dump(tariffs, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("tariffs.json päivitetty.")
    else:
        print("Ei muutoksia hinnastoihin.")


if __name__ == "__main__":
    main()
