from __future__ import annotations

DOMAIN = "lotse_forecast"

PLATFORMS = ["sensor", "button"]

MSH_TOPIC = "msh/+/2/json/mqtt/+"

CONF_WEATHER_ENTITY = "weather_entity"

BAD_STATES = {"unknown", "unavailable", "none", "nan", "inf", "-inf"}

# Invariant: NODE_KEY_META length MUST equal MAX_MAPPINGS in config-hub/src/enum.h
# Update this assertion when adding new keys; keep in sync with C firmware.
_EXPECTED_KEY_COUNT = 37  # See config-hub/src/enum.h MAX_MAPPINGS

NODE_KEY_META: dict[str, dict] = {
    "gp":  {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "gP"},
    "gip": {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "gIP"},
    "gep": {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "gEP"},
    "gp1": {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "gP1"},
    "gp2": {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "gP2"},
    "gp3": {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "gP3"},
    "gv1": {"unit": "V",   "device_class": "voltage",   "state_class": "measurement",     "name": "gV1"},
    "gv2": {"unit": "V",   "device_class": "voltage",   "state_class": "measurement",     "name": "gV2"},
    "gv3": {"unit": "V",   "device_class": "voltage",   "state_class": "measurement",     "name": "gV3"},
    "ga1": {"unit": "A",   "device_class": "current",   "state_class": "measurement",     "name": "gA1"},
    "ga2": {"unit": "A",   "device_class": "current",   "state_class": "measurement",     "name": "gA2"},
    "ga3": {"unit": "A",   "device_class": "current",   "state_class": "measurement",     "name": "gA3"},
    "gf":  {"unit": "Hz",  "device_class": "frequency", "state_class": "measurement",     "name": "gF"},
    "gpf": {"unit": "%",   "device_class": "power_factor", "state_class": "measurement",  "name": "gPF"},
    "gq":  {"unit": "VAr", "device_class": "reactive_power", "state_class": "measurement", "name": "gQ"},
    "gq1": {"unit": "VAr", "device_class": "reactive_power", "state_class": "measurement", "name": "gQ1"},
    "gq2": {"unit": "VAr", "device_class": "reactive_power", "state_class": "measurement", "name": "gQ2"},
    "gq3": {"unit": "VAr", "device_class": "reactive_power", "state_class": "measurement", "name": "gQ3"},
    "gs":  {"unit": "VA",  "device_class": "apparent_power", "state_class": "measurement", "name": "gS"},
    "gs1": {"unit": "VA",  "device_class": "apparent_power", "state_class": "measurement", "name": "gS1"},
    "gs2": {"unit": "VA",  "device_class": "apparent_power", "state_class": "measurement", "name": "gS2"},
    "gs3": {"unit": "VA",  "device_class": "apparent_power", "state_class": "measurement", "name": "gS3"},
    "sp":  {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "sP"},
    "se":  {"unit": "kWh", "device_class": "energy",    "state_class": "total_increasing",  "name": "sE"},
    "sk":  {"unit": "kWp", "device_class": None,        "state_class": None,              "name": "sK"},
    "sa":  {"unit": "°",   "device_class": None,        "state_class": None,              "name": "sA"},
    "sz":  {"unit": "°",   "device_class": None,        "state_class": None,              "name": "sZ"},
    "bp":  {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "bP"},
    "bs":  {"unit": "%",   "device_class": "battery",   "state_class": "measurement",     "name": "bS"},
    "bc":  {"unit": "kWh", "device_class": "energy",    "state_class": None,              "name": "bC"},
    "bei": {"unit": "kWh", "device_class": "energy",    "state_class": "total_increasing",  "name": "bEI"},
    "beo": {"unit": "kWh", "device_class": "energy",    "state_class": "total_increasing",  "name": "bEO"},
    "wp":  {"unit": "kW",  "device_class": "power",     "state_class": "measurement",     "name": "wP"},
    "we":  {"unit": "kWh", "device_class": "energy",    "state_class": "total_increasing",  "name": "wE"},
    "ws":  {"unit": "%",   "device_class": None,        "state_class": "measurement",     "name": "wS"},
    "gei": {"unit": "kWh", "device_class": "energy",    "state_class": "total_increasing",  "name": "gEI"},
    "geo": {"unit": "kWh", "device_class": "energy",    "state_class": "total_increasing",  "name": "gEO"},
}

# Validate that NODE_KEY_META matches expected size
assert len(NODE_KEY_META) == _EXPECTED_KEY_COUNT, (
    f"NODE_KEY_META has {len(NODE_KEY_META)} keys but C firmware expects {_EXPECTED_KEY_COUNT}. "
    f"Update _EXPECTED_KEY_COUNT or check config-hub/src/enum.h MAX_MAPPINGS."
)

COMBINED_KEY_META: dict[str, dict] = {
    "combined_mesh_gp": {"name": "Grid Power (Net)"},
    "combined_mesh_sp": {"name": "Solar Power"},
    "combined_mesh_bp": {"name": "Battery Power"},
    "combined_mesh_gei": {"name": "Grid Energy Import (cumulative)"},
    "combined_mesh_geo": {"name": "Grid Energy Export (cumulative)"},
    "combined_mesh_se": {"name": "Solar Energy (cumulative)"},
    "combined_mesh_se_clean": {"name": "Solar Energy Clean"},
    "combined_mesh_bei": {"name": "Battery Energy In (cumulative)"},
    "combined_mesh_beo": {"name": "Battery Energy Out (cumulative)"},
    "combined_mesh_battery_capacity": {"name": "Total Battery Capacity"},
    "combined_mesh_solar_capacity": {"name": "Total Solar Capacity"},
    "combined_mesh_bs": {"name": "Average Battery SOC"},
    "combined_mesh_soc_weighted": {"name": "Weighted SOC by Capacity"},
    "combined_mesh_participants": {"name": "Active Participants"},
    "combined_mesh_config_ready": {"name": "Config Ready"},
}
