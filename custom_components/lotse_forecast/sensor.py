from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE

_EntityBases = [SensorEntity]
_HAS_RESTORE = False
try:
    from homeassistant.helpers.restore_state import RestoreEntity
    _EntityBases.append(RestoreEntity)
    _HAS_RESTORE = True
except ImportError:
    pass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
try:
    from homeassistant.helpers.entity import EntityCategory
except ImportError:
    from enum import Enum
    class EntityCategory(str, Enum):
        DIAGNOSTIC = "diagnostic"
        CONFIG = "config"
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import MeshData
from .calibration import CalibrationModel
from .const import COMBINED_KEY_META, DOMAIN, NODE_KEY_META

_LOGGER = logging.getLogger(__name__)


def _sum(mesh: MeshData, key: str) -> float | None:
    """Sum all node values for a key. Returns None if no data available.
    
    Args:
        mesh: Mesh data instance.
        key: Data key to sum.
        
    Returns:
        Sum rounded to 2 decimals, or None if no nodes report this key.
    """
    vals = mesh.get_all_values(key)
    return round(sum(vals), 2) if vals else None


def _avg(mesh: MeshData, key: str) -> float | None:
    """Average all node values for a key. Returns None if no data available.
    
    Args:
        mesh: Mesh data instance.
        key: Data key to average.
        
    Returns:
        Average rounded to 1 decimal, or None if no nodes report this key.
    """
    vals = mesh.get_all_values(key)
    return round(sum(vals) / len(vals), 1) if vals else None


def _max(mesh: MeshData, key: str) -> float | None:
    """Get maximum value for a key. Returns None if no data available.
    
    Args:
        mesh: Mesh data instance.
        key: Data key.
        
    Returns:
        Maximum value rounded to 1 decimal, or None if no nodes report this key.
    """
    vals = mesh.get_all_values(key)
    return round(max(vals), 1) if vals else None


def _min(mesh: MeshData, key: str) -> float | None:
    """Get minimum value for a key. Returns None if no data available.
    
    Args:
        mesh: Mesh data instance.
        key: Data key.
        
    Returns:
        Minimum value rounded to 1 decimal, or None if no nodes report this key.
    """
    vals = mesh.get_all_values(key)
    return round(min(vals), 1) if vals else None


def _se_clean(mesh: MeshData) -> float | None:
    """Solar energy (clean) — excludes exports.
    
    Returns None if no solar data available.
    """
    vals = mesh.get_all_values("se")
    return round(sum(vals), 2) if vals else None


def _weighted_soc(mesh: MeshData) -> float | None:
    """Weighted average SOC by battery capacity.
    
    Returns None if no battery data available.
    """
    bs_vals = mesh.get_all_values("bs")  # State of charge %
    bc_vals = mesh.get_all_values("bc")  # Battery capacity kWh
    
    if not bs_vals or not bc_vals:
        return None
    
    weighted_sum = sum(s * b for s, b in zip(bs_vals, bc_vals))
    total_cap = sum(bc_vals)
    
    return round(weighted_sum / total_cap, 1) if total_cap > 0 else None


COMBINED_FNS: dict[str, Callable[[MeshData], float | None]] = {
    # Power sums (useful for situational awareness despite async timing)
    "combined_mesh_gp": lambda m: _sum(m, "gp"),
    "combined_mesh_sp": lambda m: _sum(m, "sp"),
    "combined_mesh_bp": lambda m: _sum(m, "bp"),
    # Cumulative energy (valid — monotonically increasing)
    "combined_mesh_gei": lambda m: _sum(m, "gei"),
    "combined_mesh_geo": lambda m: _sum(m, "geo"),
    "combined_mesh_se": lambda m: _sum(m, "se"),
    "combined_mesh_se_clean": lambda m: _se_clean(m),
    "combined_mesh_bei": lambda m: _sum(m, "bei"),
    "combined_mesh_beo": lambda m: _sum(m, "beo"),
    # Static config (valid — doesn't change between reports)
    "combined_mesh_battery_capacity": lambda m: _sum(m, "bc"),
    "combined_mesh_solar_capacity": lambda m: _sum(m, "sk"),
    # Slow-changing averages (valid — SOC changes slowly)
    "combined_mesh_bs": lambda m: _avg(m, "bs"),
    "combined_mesh_soc_weighted": lambda m: _weighted_soc(m),
    # Counters (timeless)
    "combined_mesh_participants": lambda m: float(len([v for v in mesh.get_all_values("gip") if v])) or None,
    "combined_mesh_config_ready": lambda m: float(len(m.get_all_values("bc"))) or None,
    # Grid-coherent stats (valid — same physical grid, averages filter noise)
    "combined_mesh_gv1_max": lambda m: _max(m, "gv1"),
    "combined_mesh_gv1_min": lambda m: _min(m, "gv1"),
    "combined_mesh_gv2_max": lambda m: _max(m, "gv2"),
    "combined_mesh_gv2_min": lambda m: _min(m, "gv2"),
    "combined_mesh_gv3_max": lambda m: _max(m, "gv3"),
    "combined_mesh_gv3_min": lambda m: _min(m, "gv3"),
    "combined_mesh_gf_avg": lambda m: _avg(m, "gf"),
    "combined_mesh_gf_min": lambda m: _min(m, "gf"),
    "combined_mesh_gf_max": lambda m: _max(m, "gf"),
    "combined_mesh_ga1_sum": lambda m: _sum(m, "ga1"),
    "combined_mesh_ga2_sum": lambda m: _sum(m, "ga2"),
    "combined_mesh_ga3_sum": lambda m: _sum(m, "ga3"),
    "combined_mesh_gpf_avg": lambda m: _avg(m, "gpf"),
    "combined_mesh_gq_sum": lambda m: _sum(m, "gq"),
    "combined_mesh_gq1_sum": lambda m: _sum(m, "gq1"),
    "combined_mesh_gq2_sum": lambda m: _sum(m, "gq2"),
    "combined_mesh_gq3_sum": lambda m: _sum(m, "gq3"),
    "combined_mesh_gs_sum": lambda m: _sum(m, "gs"),
    "combined_mesh_gs1_sum": lambda m: _sum(m, "gs1"),
    "combined_mesh_gs2_sum": lambda m: _sum(m, "gs2"),
    "combined_mesh_gs3_sum": lambda m: _sum(m, "gs3"),
}


class MeshSensor(SensorEntity):
    """Base class for LOTSE mesh sensors."""

    def __init__(self, unique_id: str, name: str, unit: str | None = None,
                 device_class: str | None = None, state_class: str | None = None,
                 icon: str | None = None, entity_category: str | None = None) -> None:
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        if entity_category:
            self._attr_entity_category = entity_category

    @property
    def available(self) -> bool:
        """Sensor is available if it has a valid state."""
        return self._attr_native_value is not None


class PerNodeSensor(MeshSensor):
    """Sensor for per-node metrics."""

    def __init__(self, node_id: str, key: str, meta: dict, mesh: MeshData) -> None:
        super().__init__(
            unique_id=f"{DOMAIN}_{node_id}_{key}",
            name=f"Node {node_id} {meta.get('name', key)}",
            unit=meta.get("unit"),
            device_class=meta.get("device_class"),
            state_class=meta.get("state_class"),
        )
        self._node_id = node_id
        self._key = key
        self._mesh = mesh
        self._attr_native_value = None

    def update_value(self, value: float | None) -> None:
        """Update sensor value."""
        self._attr_native_value = value
        self.async_write_ha_state()


class CombinedSensor(MeshSensor):
    """Sensor for combined neighborhood metrics."""

    def __init__(self, unique_id: str, name: str, unit: str | None = None,
                 device_class: str | None = None, state_class: str | None = None,
                 compute_fn: Callable[[MeshData], float | None] | None = None,
                 mesh: MeshData | None = None) -> None:
        super().__init__(unique_id, name, unit, device_class, state_class)
        self._compute_fn = compute_fn
        self._mesh = mesh
        self._attr_native_value = None

    def update_combined(self) -> None:
        """Recompute combined value from mesh data."""
        if self._compute_fn and self._mesh:
            self._attr_native_value = self._compute_fn(self._mesh)
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor platforms."""
    # Implementation depends on integration architecture
    pass
