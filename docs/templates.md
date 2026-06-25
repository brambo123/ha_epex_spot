# Ready-to-Use Energy Provider Price Templates

Below is a list of pre-configured templates for popular dynamic energy providers. You can copy and paste these directly into the **Custom Import Template** and/or **Custom Export Template** field in the integration options.

---

## 🇳🇱 Netherlands (Nederland)

### 1. Zonneplan
Zonneplan applies a fixed surcharge per kWh including procurement costs. For export (feeding back to the grid), they offer a **Zonnebonus** (10% extra yield on top of the total price including tax, between sunrise and sunset).
* **Import Template:**
```jinja2
{# Energy tax #}
{% if now().strftime('%Y-%m-%d') >= '2027-01-01' %}
  {# Replace 0.1234 with the actual government energy tax rate for 2027, including VAT #}
  {% set energy_tax = 0.1234 %}
{% else %}
  {# Current 2026 energy tax #}
  {% set energy_tax = 0.110848 %}
{% endif %}

{{ (market_price * 1.21) + 0.02 + energy_tax }}
```

* **Export Template:**
```jinja2
{# Energy tax #}
{% if now().strftime('%Y-%m-%d') >= '2027-01-01' %}
  {# Energy tax return stops from January 1st, 2027 onwards #}
  {% set energy_tax = 0 %}
{% else %}
  {# Current 2026 energy tax #}
  {% set energy_tax = 0.110848 %}
{% endif %}

{% set export_base = (market_price * 1.21) + 0.02 %}
{# Check if the calculated hour falls between sunrise and sunset #}
{% if export_base > 0 and
      now() > today_at(state_attr('sun.sun', 'next_rising') | as_timestamp | timestamp_custom('%H:%M', true)) and 
      now() < today_at(state_attr('sun.sun', 'next_setting') | as_timestamp | timestamp_custom('%H:%M', true)) %}
  {{ (export_base * 1.10) + energy_tax }}
{% else %}
  {{ export_base + energy_tax }}
{% endif %}
```
  
### 2. NextEnergie
Zonneplan applies a fixed surcharge per kWh including procurement costs for import only. For export NextEnergie offers a massive **Zonnebonus** (50% extra yield on top of your export price including tax, between 06:00 and 22:00).
* **Import Template:**
```jinja2
{# Energy tax #}
{% if now().strftime('%Y-%m-%d') >= '2027-01-01' %}
  {# Replace 0.1234 with the actual government energy tax rate for 2027, including VAT #}
  {% set energy_tax = 0.1234 %}
{% else %}
  {# Current 2026 energy tax #}
  {% set energy_tax = 0.110848 %}
{% endif %}

{{ (market_price * 1.21) + 0.0219 + energy_tax }}
```

* **Export Template:**
```jinja2
{# Energy tax #}
{% if now().strftime('%Y-%m-%d') >= '2027-01-01' %}
  {# Energy tax return stops from January 1st, 2027 onwards #}
  {% set energy_tax = 0 %}
{% else %}
  {# Current 2026 energy tax #}
  {% set energy_tax = 0.110848 %}
{% endif %}

{% set export_base = market_price * 1.21 %}
{# Check if the calculated hour is between 06:00 and 22:00 #}
{% if export_base > 0 and now().hour >= 6 and now().hour < 22 %}
  {{ (export_base * 1.50) + energy_tax }}
{% else %}
  {{ export_base + energy_tax }}
{% endif %}
```
  
---

## 🌍 Other Countries
*Templates for other countries will be added here. Feel free to open a Pull Request to submit yours!*