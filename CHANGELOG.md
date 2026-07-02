# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Changelog – SNMP Printer Canon Enhanced

## 1.2.0 – Canon MF754cdw Special Edition
### Kompletní refaktorizace komponenty
- Komponenta je nyní plně specializovaná pro tiskárny **Canon MF754cdw / MF750C Series**.
- Odstraněna podpora generických SNMP tiskáren (HP, Epson, Brother, Lexmark, Samsung…).
- Odstraněna podpora SNMPv3 – bude doplněno v některé z dalších verzí.

### Nový SNMP klient (pysnmp‑lextudio)
- Přechod na knihovnu **pysnmp‑lextudio 6.0.11** kompatibilní s Home Assistant Core 2024+.
- Kompletně přepsaná komunikace přes SNMP (GET, WALK).
- Používány pouze ověřené Canon OID:
  - systémové informace (sysDescr, sysName, sysLocation…)
  - stav zařízení (hrDeviceStatus)
  - upozornění tiskárny (prtAlertDescription)
  - počítadla stran (total / color / mono)
  - zásobníky papíru
  - spotřební materiál (toner, waste toner, drum)

### Nové datové struktury
- `page_counts` → total, color, mono
- `supplies` → description, level, max_capacity, percentage
- `input_trays` → description, level, max_capacity, percentage
- `errors` → Canon alert description

### Odstraněné nepodporované funkce
- `cover_status` (Canon SNMP neobsahuje)
- `display_text` (Canon SNMP neobsahuje)
- SNMP SET operace (Canon nepodporuje)
- Služba `display_text` byla odstraněna včetně `services.yaml`

### Nové senzory
- Stav tiskárny (running / warning / down / offline / unknown)
- Počet stran (total, color, mono)
- Upozornění tiskárny (Canon alerts)
- Zásobníky papíru (Tray 1–4)
- Spotřební materiál (toner, waste toner, drum)

### Nové jazykové soubory
- Aktualizované `en.json` a `cs.json` podle Canon‑specializované verze.
- Odstraněny nepoužívané překlady (barvy tonerů, cover, display, SNMPv3).

### Nový config flow
- Zjednodušený pouze na SNMPv2c.
- Automatická detekce Canon tiskárny přes Zeroconf.
- Zobrazení modelu a výrobce z Canon sysDescr.

### Nový manifest
- `requirements`: pysnmp-lextudio==6.0.11
- `domain`: snmp_printer_canon_enhanced
- `config_flow`: true
- `iot_class`: local_polling
- Odstraněny nepotřebné položky.

### Další změny
- Vyčištění celé codebase.
- Zjednodušení struktury komponenty.
- Zrychlení SNMP dotazů.
- Stabilnější chování při výpadku tiskárny.
