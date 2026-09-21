# Changelog

All notable changes to the EPEX Spot integration will be documented in this file.

> [!IMPORTANT]  
> From version 5.0.1 onwards, Tibber's price information is split into market price and total price. Please ensure you use the correct sensor.

---

## [5.0.1] [Unpublished]

### 📢 Important change
* The **Tibber API** now retrieves the bare market price, but still uses the tax information to calculate the total price.

### 🛠️ Improvements & Optimizations
* **Internal restructuring** - APIs are now loaded more dynamically, making it easier to add new ones later.
* **API token changeable** - Configured API tokens can now be modified; we also test the token before saving.
* **ENTSO-E** - The API may sometimes return duplicate time series; read only the first one.
* **Hofer Grünstrom** - Fix Daylight Saving Time handling and 60min price calculations.
* **Nordpool** - Accept only final prices for EUR (Nord Pool provides preliminary price information).
* **Fallback support** - Use data from failback source after 16:00 instead of after 21:00.

## [5.0.0] - 2026-07-06

### 📢 Project Continuation Notice
* This integration has been forked to accelerate development, improve stability, and swiftly address API updates. A huge thank you to the original author (@mampfes) for laying such a solid foundation!

### 🚀 New Features & APIs
* **Import & Export Price Templates** – Introduced flexible pricing templates, making it easier to handle separate import and export cost calculations.
* **Fallback support** – Improved reliability across the board. The integration can now automatically leverage fallback mechanisms if your primary data provider experiences downtime.
* **New Provider: Nordpool** – Added full support for Nordpool Day-Ahead electricity prices (Special thanks to @andypieters!).
* **New Providers: EnergyZero & Jeroen.nl** – Expanded regional data sources with native integration for EnergyZero and Jeroen.nl dynamic tariffs.

### 🛠️ Improvements & Optimizations
* **Smart Offline Caching** – Enhanced data fetching logic to include offline caching. This heavily reduces unnecessary API hits, protects rate limits, and ensures data remains available even during brief network interruptions.
* **Streamlined Config Flow** – Fixed several minor bugs and edge cases within the configuration setup, making adding or modifying providers much smoother.
* **API Stability Fixes** – Resolved multiple minor bugs, adjusted date/time calculations, and updated parameters across various background data fetchers (including SMARD, Awattar, and HoferGruenstrom).
