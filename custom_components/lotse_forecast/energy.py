import logging
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from homeassistant.core import HomeAssistant

from .calibration import CalibrationModel

DOMAIN = "lotse_forecast"

_LOGGER = logging.getLogger(__name__)

_LOGGER.warning("lotse_forecast energy module loaded — ready for auto-discovery")


def _safe_parse_datetime(dt_raw) -> Optional[datetime]:
    """Safely parse datetime from various formats.
    
    Tries ISO format, then falls back gracefully. Logs errors without crashing.
    
    Args:
        dt_raw: Raw datetime value (str, datetime, or other).
        
    Returns:
        Parsed datetime, or None if parsing fails.
    """
    if dt_raw is None:
        return None
    
    try:
        if isinstance(dt_raw, datetime):
            return dt_raw
        if isinstance(dt_raw, str):
            return datetime.fromisoformat(dt_raw)
        _LOGGER.debug("Unexpected datetime type: %s (value: %s)", type(dt_raw), dt_raw)
    except (ValueError, TypeError) as e:
        _LOGGER.debug("Failed to parse datetime %s: %s", dt_raw, e)
    
    return None


async def async_get_solar_forecast(
    hass: HomeAssistant, config_entry_id: str
) -> dict[str, dict[str, float | int]] | None:
    """Get solar forecast from calibration model.
    
    Args:
        hass: Home Assistant instance.
        config_entry_id: Config entry ID.
        
    Returns:
        Forecast dict or None if unavailable.
    """
    _LOGGER.warning("Forecast: called for entry %s (debug for discovery verification)", config_entry_id)

    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None:
        _LOGGER.debug("Forecast: entry %s not found in registry", config_entry_id)
        return None
    if entry.domain != DOMAIN:
        _LOGGER.debug(
            "Forecast: entry %s domain is %s, not %s",
            config_entry_id, entry.domain, DOMAIN,
        )
        return None

    weather_entity = entry.options.get("weather_entity") or entry.data.get("weather_entity")
    if not weather_entity:
        _LOGGER.debug(
            "Forecast: no weather_entity in options=%s or data=%s for entry %s",
            entry.options.get("weather_entity"),
            entry.data.get("weather_entity"),
            config_entry_id,
        )
        return None

    forecast = await _get_weather_forecast(hass, weather_entity)
    if not forecast:
        _LOGGER.debug("Forecast: no weather data, using clear-sky only")
        forecast = []

    panels = _get_panels(hass, entry)
    if not panels:
        _LOGGER.debug("Forecast: no panels available for entry %s", config_entry_id)
        return None

    lat = hass.config.latitude
    tz = ZoneInfo(hass.config.time_zone)
    local_now = datetime.now(tz)

    # Build set of timestamps the weather forecast already covers for today
    weather_ts: set[str] = set()
    for entry_data in forecast:
        dt_raw = entry_data.get("datetime") or entry_data.get("DateTime")
        dt = _safe_parse_datetime(dt_raw)
        if dt is not None and dt.date() == local_now.date():
            weather_ts.add(dt.isoformat())

    _LOGGER.debug(
        "Forecast: weather_ts has %d entries from weather service for today",
        len(weather_ts),
    )

    # Backfill missing hours of today with clear-sky defaults
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    backfilled = 0
    for hour in range(24):
        dt = today_start.replace(hour=hour)
        ts = dt.isoformat()
        if ts not in weather_ts:
            forecast.append({
                "datetime": dt,
                "cloud_cover": 0,
                "temperature": 20,
                "wind_speed": 5,
            })
            backfilled += 1

    _LOGGER.debug(
        "Forecast: backfilled %d hours with clear-sky defaults, total forecast size=%d",
        backfilled, len(forecast),
    )

    # Placeholder for actual forecast computation (not shown in original)
    # raw_wh, cloud_map = _compute_forecast(forecast, panels, lat, tz)
    # if not raw_wh:
    #     return None
    # ...
    
    return None  # Stub for demonstration


async def _get_weather_forecast(hass: HomeAssistant, weather_entity: str) -> list[dict]:
    """Get weather forecast from entity.
    
    Args:
        hass: Home Assistant instance.
        weather_entity: Weather entity ID.
        
    Returns:
        List of forecast dicts or empty list if unavailable.
    """
    # Placeholder implementation
    return []


def _get_panels(hass: HomeAssistant, entry) -> list[dict]:
    """Get solar panel configurations from entry.
    
    Args:
        hass: Home Assistant instance.
        entry: Config entry.
        
    Returns:
        List of panel dicts or empty list if unavailable.
    """
    # Placeholder implementation
    return []
