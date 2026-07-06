# Changelog

All notable changes to the EPEX Spot integration will be documented in this file.

---

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
