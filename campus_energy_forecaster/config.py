"""Paths and the explicit, editable assumptions behind every cost and carbon figure."""
from dataclasses import dataclass
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJ_ROOT / "data"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
LBNL_DIR = EXTERNAL_DATA_DIR / "lbnl"
WEB_DATA_DIR = PROJ_ROOT / "web" / "public" / "data"
RESULTS_JSON = WEB_DATA_DIR / "results.json"


@dataclass(frozen=True)
class Assumptions:
    """Change these to match a real site; every figure in the dashboard is computed from them."""
    # US average commercial electricity price in 2025, 13.41 cents/kWh (EIA Electric Power Monthly, Table 5.3).
    # Replace with the site's own tariff.
    tariff_usd_per_kwh: float = 0.1341
    # US average grid CO2 emission rate, 767.2 lb/MWh = 0.348 kg/kWh (EPA eGRID2023, total output rate).
    # Replace with the local grid factor.
    carbon_kg_per_kwh: float = 0.348
