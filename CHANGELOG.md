# Changelog

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/), verze podle [Semantic Versioning](https://semver.org/lang/cs/).

## [0.2.1] - 2026-10-21

### Opraveno
- Prázdná odpověď realtime logu (firmware 4.x) se už nepovažuje za chybu; spojení se neukončuje a entity nepřecházejí do stavu „nedostupné“.
- Po potichu ukončené relaci panelu se dotaz zopakuje po novém připojení v rámci stejného cyklu.
- Entity přejdou do stavu „nedostupné“ až po 3 neúspěšných dotazech za sebou.

## [0.2.0] - 2026-10-21

### Přidáno
- Tlačítko impulsu pro každé dveře a každý pomocný výstup.
- Nastavitelná doba impulsu 1–10 s pro každé tlačítko, uchovaná po restartu.

### Opraveno
- Příkaz na relé se po spadlé relaci znovu odešle po novém připojení.

## [0.1.0] - 2026-10-19

### Změněno
- Úprava pro aktuální Home Assistant (runtime_data, OptionsFlow, ConfigFlowResult, asyncio.timeout).
- Knihovna zkaccess_c3 0.0.15.

### Bezpečnost
- Doba odemčení a sepnutí výstupu omezena na 1–254 s (255 = trvale otevřeno).
- Heslo se nezapisuje do ladicího logu.
- Komunikace s panelem serializovaná a mimo hlavní smyčku HA.
- Heslo v konfiguraci maskované, testovací spojení se uzavírá.

[0.2.1]: https://github.com/DJjohn07/ZTKTecoC3-400/releases/tag/v0.2.1
[0.2.0]: https://github.com/DJjohn07/ZTKTecoC3-400/releases/tag/v0.2.0
[0.1.0]: https://github.com/DJjohn07/ZTKTecoC3-400/releases/tag/v0.1.0
