# SFML Stats Dashboard

[![Version](https://img.shields.io/badge/version-12.0.0-blue.svg)](https://github.com/Zara-Toorox/sfml_stats)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

Fuel my late-night ideas with a coffee? I'd really appreciate it!

<a href='https://ko-fi.com/Q5Q41NMZZY' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://ko-fi.com/img/githubbutton_sm.svg' border='0' alt='Buy Me a Coffee' /></a>

**Comprehensive Energy Monitoring Dashboard for Home Assistant**

A powerful dashboard that visualizes solar production, battery storage, grid consumption, and energy costs in real-time. Designed to work seamlessly with [Solar Forecast ML](https://github.com/Zara-Toorox/ha-solar-forecast-ml) and [Grid Price Monitor](https://github.com/Zara-Toorox/ha-solar-forecast-ml/tree/main/custom_components/solar_forecast_ml/extra_features/grid_price_monitor) for the ultimate energy management experience.

---

## What Makes This Dashboard Special?

SFML Stats Dashboard provides a unified view of your entire energy ecosystem:

- **Real-time Visualization:** See exactly where your energy is flowing - from solar panels to battery, house, and grid
- **Forecast Integration:** Compare actual production against Solar Forecast ML predictions
- **Cost Tracking:** Monitor energy costs with fixed or dynamic pricing support
- **Automated Reports:** Generate beautiful weekly and monthly charts automatically
- **Multi-String Support:** Track up to 4 separate panel groups individually
- **Weather Correlation:** Overlay weather data on your energy charts

---

## Important Compatibility Notes

> **Warning**
> This integration does NOT work on:
> - **Raspberry Pi** - Due to performance limitations with matplotlib chart generation
> - **Proxmox VE** - When Home Assistant runs directly on Proxmox (VMs/LXC containers on Proxmox are fine)

The integration requires sufficient CPU and memory resources for generating charts with matplotlib. Lightweight systems cannot handle this workload reliably.

**Recommended platforms:**
- Intel NUC or similar x86 hardware
- Virtual machines with adequate resources (4GB+ RAM)
- LXC containers on Proxmox with sufficient allocation
- Home Assistant OS on capable hardware

---

## Features

- Real-time energy flow visualization
- Solar production analytics with forecast comparison
- Battery state of charge and charge/discharge tracking
- Grid import/export monitoring
- Cost calculation with fixed or dynamic pricing
- Automated weekly and monthly report generation
- Support for up to 4 separate solar panel strings
- Weather integration for chart annotations
- Dark and light theme support
- **Monthly Tariff Management** - Track and manage monthly energy tariffs with EEG support
- **Clothing Recommendation** - Weather-based clothing suggestions for the day
- **Power Sources Chart** - Detailed stacked area visualization of energy sources
- **Improved Caching** - Better performance with intelligent data caching

---

## Screenshots

### Energy Flow Dashboard
Real-time visualization of your complete energy ecosystem — solar, battery, house, and grid with animated power flow lines.

![Energy Flow Dashboard](Pictures/energy-live.png)

### LCARS Theme
Star Trek-inspired LCARS interface with full energy monitoring — Solar Array, Warp Core (Battery), Habitat (House), and Power Matrix (Grid).

![LCARS Theme](Pictures/lcars.png)

### Developer Version — Energy Widgets
Full energy widget display with live power values, Starfleet billing overview, and financial summary (requires Developer PIN).

![Developer Energy Widgets](Pictures/developer_energy.png)

### Developer Version — AI & Forecast Display
Long-range forecast scanner, AI status, daily energy curve with forecast comparison, and per-panel group analytics (requires Developer PIN).

![Developer AI Display](Pictures/developer_ki.png)

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL and select "Integration" as category
5. Search for "SFML Stats" and install
6. Restart Home Assistant
7. Go to Settings > Devices & Services > Add Integration > SFML Stats

### Manual Installation

1. Download the latest release
2. Copy the `sfml_stats` folder to `custom_components/` in your Home Assistant config directory
3. Restart Home Assistant
4. Go to Settings > Devices & Services > Add Integration > SFML Stats

---

## Sensor Configuration Guide

### General Notes

All sensors are optional. The integration works with incomplete configuration but will only display available data.

Power sensors can be specified in Watts (W) or Kilowatts (kW). The integration detects the unit automatically.

Energy sensors should be in Kilowatt-hours (kWh).

---

## Step 1: Basic Settings

No sensors required. This step contains configuration options for automatic chart generation and color theme selection.

---

## Step 2: Energy Flow Sensors

### sensor_solar_power
Current total power output of the photovoltaic system.
- Unit: W
- Source: Inverter integration
- Example: `sensor.inverter_pv_power`

### sensor_solar_to_house
Portion of solar power consumed directly in the house.
- Unit: W
- Source: Inverter or energy management system
- Note: Not all inverters provide this value. If unavailable, it can often be calculated from other values.

### sensor_solar_to_battery
Solar power flowing into the battery.
- Unit: W
- Source: Battery management system or hybrid inverter
- Note: Only relevant for systems with battery storage.

### sensor_grid_to_house
Power currently drawn from the grid.
- Unit: W
- Source: Smart meter or inverter
- Note: Some systems only show total grid consumption without breakdown.

### sensor_grid_to_battery
Grid power used to charge the battery.
- Unit: W
- Source: Battery management system
- Note: Relevant for systems that allow grid charging.

### sensor_house_to_grid
Power fed into the grid.
- Unit: W
- Source: Smart meter or inverter
- Note: Shows current surplus being exported.

### sensor_smartmeter_import
Total grid consumption from smart meter.
- Unit: kWh
- Source: Smart meter integration
- Note: Can be a meter reading (continuously increasing) or a daily counter.

### sensor_smartmeter_export
Total export according to smart meter.
- Unit: kWh
- Source: Smart meter integration
- Note: Corresponds to the feed-in meter.

---

## Step 3: Battery Sensors

### sensor_battery_soc
Current battery state of charge in percent.
- Unit: Percent (0-100)
- Source: Battery management system
- Example: `sensor.battery_state_of_charge`

### sensor_battery_power
Current charging or discharging power of the battery.
- Unit: W
- Source: Battery management system
- Note: Positive values typically mean charging, negative values discharging. Some systems use reversed logic.

### sensor_battery_to_house
Discharge power flowing to the house.
- Unit: W
- Source: Battery management system or hybrid inverter

### sensor_battery_to_grid
Discharge power being fed into the grid.
- Unit: W
- Source: Battery management system
- Note: Only relevant if the system can export battery power.

### sensor_home_consumption
Total current power consumption of the household.
- Unit: W
- Source: Energy management system or custom calculation
- Note: Sum of all sources (solar, battery, grid).

---

## Step 4: Statistics Sensors

### sensor_solar_yield_daily
Daily yield of the photovoltaic system.
- Unit: kWh
- Source: Inverter or Home Assistant Utility Meter
- Note: Should reset to zero at midnight.

### sensor_grid_import_daily
Daily grid consumption.
- Unit: kWh
- Source: Smart meter or Home Assistant Utility Meter
- Note: Should reset to zero at midnight.

### sensor_grid_import_yearly
Yearly grid consumption.
- Unit: kWh
- Source: Smart meter or Home Assistant Utility Meter
- Note: Used for annual statistics.

### sensor_battery_charge_solar_daily
Daily battery charge from solar power.
- Unit: kWh
- Source: Battery management system or custom integration

### sensor_battery_charge_grid_daily
Daily battery charge from grid power.
- Unit: kWh
- Source: Battery management system

### sensor_price_total
Total cost for grid consumption.
- Unit: Currency (EUR, USD, etc.)
- Source: Custom calculation or energy cost integration

### weather_entity
Weather entity for weather display in charts.
- Type: Weather entity (not sensor)
- Source: Any Home Assistant weather integration
- Example: `weather.home`

---

## Step 5: Panel Sensors

The integration supports up to four separate strings or panel groups. Each group has three fields.

### panel_name (1-4)
Custom name for the string.
- Type: Text
- Examples: South, East, West, Garage, Carport
- Default: String 1, String 2, String 3, String 4

### sensor_panel_power (1-4)
Current power output of this string.
- Unit: W
- Source: Inverter with MPPT tracking
- Note: Not all inverters provide individual string values.

### sensor_panel_max_today (1-4)
Peak power reached by this string on the current day.
- Unit: W
- Source: Custom calculation or inverter
- Note: Can be created with a Home Assistant Statistics helper using maximum function.

---

## Step 6: Billing

No sensors required. This step configures parameters for cost calculation.

The billing period defines from which day and month the annual energy balance is calculated. This typically corresponds to the start of your electricity contract.

The price mode can be dynamic (via a separate integration like Grid Price Monitor) or set as a fixed value in cents per kilowatt-hour.

---

## Practical Tips

### Creating Missing Sensors

If a required sensor is not directly available, it can often be created in Home Assistant:

**For daily counters:** Use the Utility Meter helper with daily reset.

**For maximum values:** Use the Statistics helper with the Maximum function.

**For calculated values:** Create a Template sensor.

### Typical Sensor Sources by Manufacturer

| Manufacturer | Integration |
|--------------|-------------|
| Fronius | Native integration provides most values directly |
| SMA | Modbus or SMA Energy Meter integration |
| Huawei | FusionSolar integration or Modbus |
| Kostal | Piko or Plenticore integration |
| Growatt | Growatt Server integration |
| Sungrow | Modbus integration |
| Enphase | Envoy integration provides panel data |

### Smart Meter Connection Options

- **ISKRA or similar:** IR reading head with ESPHome
- **P1 Port:** For Dutch and Belgian meters
- **Shelly EM/3EM:** As intermediate solution
- **Direct Modbus:** For modern meters

### Setting Up Utility Meters

For daily counters in `configuration.yaml`:

```yaml
utility_meter:
  solar_daily:
    source: sensor.inverter_total_energy
    cycle: daily
  grid_import_daily:
    source: sensor.smartmeter_import_total
    cycle: daily
```

### Template Sensor for Home Consumption

If no direct sensor is available:

```yaml
template:
  - sensor:
      - name: "Home Consumption"
        unit_of_measurement: "W"
        state: >
          {{ states('sensor.solar_power')|float(0)
             + states('sensor.grid_import')|float(0)
             - states('sensor.grid_export')|float(0) }}
```

---

## Accessing the Dashboard

After installation and configuration, access the dashboard at:

```
http://YOUR_HOME_ASSISTANT:8123/api/sfml_stats/dashboard
```

Or add it to your sidebar via the Home Assistant configuration.

---

## Requirements

- Home Assistant 2024.1.0 or newer
- Sufficient system resources (not Raspberry Pi)
- Python packages: matplotlib, aiofiles (installed automatically)

---

## Code Protection

Parts of this integration are protected with [PyArmor](https://pyarmor.readthedocs.io/) obfuscation to safeguard proprietary algorithms and business logic.

**Protected modules (22 files):**
- `api/` — REST-API endpoints and WebSocket handlers
- `charts/` — All analytics chart generators (weekly reports, battery, grid, solar, weather, etc.)
- `readers/` — Data readers for solar, price, forecast, and weather data
- `services/` — Billing calculator, daily/hourly aggregation, forecast comparison
- Root-level — Central data reader, power sources collector, clothing recommendation

**Unprotected (cleartext):**
- `__init__.py`, `const.py`, `config_flow.py` — Integration setup and configuration
- `storage/`, `utils/` — Infrastructure and utilities
- `translations/`, `frontend/` — UI resources
- Base classes, types, and helper modules

The obfuscation targets Home Assistant OS (Alpine Linux / musl libc) on both x86_64 and aarch64 platforms.

### Developer Version

Starting with version 12.0.0, a **Developer Version** is available that provides full unobfuscated source code with complete AI display capabilities. This version is intended for development and debugging purposes.

To obtain the Developer PIN, please contact the author directly:
- **GitHub:** [@Zara-Toorox](https://github.com/Zara-Toorox)

---

## License

This software is licensed under a Proprietary Non-Commercial License.

- Personal and educational use only
- Commercial use and AI training are strictly prohibited
- Clear attribution to "Zara-Toorox" is required

Copyright (C) 2026 Zara-Toorox

See [LICENSE](LICENSE) for full terms.

---

## Support

- [GitHub Issues](https://github.com/Zara-Toorox/sfml_stats/issues)
- [Documentation](https://github.com/Zara-Toorox/sfml_stats)
