# ZKTeco C3 Access Control Panel

Integrace pro Home Assistant pro přístupové panely ZKAccess C3-100, C3-200, C3-400 a inBio 160/260/460.
Vychází z [vwout/hass-zkaccess_c3](https://github.com/vwout/hass-zkaccess_c3), licence GPL-3.0.

## Entity

- zámek pro každé dveře
- přepínač alarmu pro každé dveře (vypnutí zruší všechny alarmy panelu)
- binární senzor pro každý pomocný vstup
- přepínač pro každý pomocný výstup

## Instalace přes HACS

1. HACS → tři tečky → Custom repositories
2. Repository: `https://github.com/DJjohn07/ZTKTecoC3-400`, Type: `Integration`
3. Stáhnout a restartovat Home Assistant
4. Nastavení → Zařízení a služby → Přidat integraci → „C3/inBio Door Access Control Panel“
5. Zadat IP adresu panelu, port `4370` a komunikační heslo

## Volby

| Volba | Výchozí | Rozsah |
|---|---|---|
| Interval dotazování | 15 s | 2–3600 s |
| Doba odemčení | 3 s | 1–254 s |
| Doba sepnutí AUX výstupu | 33 s | 1–254 s |

## Bezpečnost

- Protokol panelu není šifrovaný. Panel umístěte do oddělené sítě a port 4370 povolte jen z IP adresy Home Assistantu.
- Heslo panelu smí obsahovat pouze znaky ASCII.

## Ladění

```yaml
logger:
  logs:
    custom_components.zkaccess_c3: debug
    C3: debug
```
