# SNMP Printer Canon Enhanced  
Home Assistant integration for **Canon MF754cdw / MF750C Series** printers using SNMP v2c.

![maintenance](https://img.shields.io/maintenance/yes/2026.svg)
![hacs](https://img.shields.io/badge/hacs-default-green.svg)
![ha_version](https://img.shields.io/badge/home%20assistant-2024.10%2B-green.svg)
![version](https://img.shields.io/badge/version-1.2.0-green.svg)
![stability](https://img.shields.io/badge/stability-stable-green.svg)
![license](https://img.shields.io/badge/License-MIT-blue.svg)

---

## 📌 About This Integration

This is a **specialized SNMP integration for Canon MF754cdw / MF750C Series printers**.  
It is **not a generic SNMP printer integration** — all logic, OIDs, sensors and flows are optimized specifically for Canon MF7xx devices.

The integration provides:

- Reliable SNMP v2c communication using `pysnmp-lextudio`
- Accurate Canon‑specific page counters (total / color / mono)
- Canon alert messages (prtAlertDescription)
- Supply levels (toner, waste toner, drum)
- Paper tray status (Tray 1–4)
- Automatic Zeroconf discovery of Canon printers
- Cached values when the printer is offline
- Clean and simple configuration flow

---

## 🖨 Supported Devices

| Model | Status |
|-------|--------|
| **Canon MF754cdw** | ✔ Fully supported |
| **Canon MF750C Series** | ✔ Fully supported |
| Other Canon models | ❓ Not tested |
| HP / Epson / Brother / Lexmark / Samsung | ❌ Not supported |
| SNMPv3 printers | ❌ Not supported |

This integration is intentionally **Canon‑only** for maximum reliability.

---

## 🚀 Features

### ✔ Canon‑specific SNMP monitoring
- Printer status (running / warning / down / offline)
- Page counters (total, color, mono)
- Canon alert messages
- Supply levels:
  - Black toner
  - Cyan toner
  - Magenta toner
  - Yellow toner
  - Waste toner
  - Drum life
- Paper trays:
  - Tray 1
  - Tray 2
  - Tray 3
  - Tray 4

### ✔ Automatic discovery
The integration detects Canon printers via Zeroconf/mDNS.

### ✔ Cached values
If the printer is offline, the integration continues to show the last known values.

### ✔ Clean configuration
Only SNMP v2c is used — no SNMPv3 complexity.

---

## 📦 Installation

### 🔹 HACS (Recommended)
1. Open **HACS → Integrations**
2. Click **Custom repositories**
3. Add repository:  
   `https://github.com/DavidPik/snmp_printer_canon_enhanced`
4. Category: **Integration**
5. Install the integration
6. Restart Home Assistant

### 🔹 Manual Installation
Copy the folder: custom_components/snmp_printer_canon_enhanced into: config/custom_components/


Restart Home Assistant.

---

## ⚙️ Configuration

### Automatic Discovery
If your Canon printer broadcasts via Zeroconf, Home Assistant will show a discovery card.

Click **Configure** → Confirm → Done.

### Manual Configuration
Go to:

**Settings → Devices & Services → Add Integration → SNMP Printer Canon Enhanced**

You will be asked for:

| Field | Description |
|-------|-------------|
| **IP Address** | Printer IP (e.g., 192.168.1.50) |
| **Port** | SNMP port (default: 161) |
| **Community** | SNMP community (default: `public`) |
| **Update Interval** | Polling interval in seconds |

SNMP Version is fixed to **v2c**.

---

## 📊 Sensors Created

### Printer Status
- running  
- warning  
- down  
- offline  
- unknown  

### Page Counts
- total pages  
- color pages  
- mono pages  

### Alerts
- Canon alert description (prtAlertDescription)

### Supplies
- Toner (Black, Cyan, Magenta, Yellow)
- Waste toner
- Drum life

### Paper Trays
- Tray 1
- Tray 2
- Tray 3
- Tray 4

---

## 🔧 Troubleshooting

### Printer shows “offline”
- Check SNMP is enabled in the printer web interface  
- Check firewall rules  
- Check correct IP address  
- Check community string (`public` by default)

### Some sensors show “unknown”
Canon printers sometimes return empty SNMP values when waking from sleep.  
Values will update automatically on next polling cycle.

### Zeroconf discovery does not work
You can always configure the printer manually.

---

## 📝 Changelog

See:  
[CHANGELOG.md](CHANGELOG.md)

---

## 📄 License

MIT License  
© 2026 DavidPik

---

## 🤝 Contributing

Pull requests are welcome.  
If you encounter issues, please report them here:

https://github.com/DavidPik/snmp_printer_canon_enhanced/issues


