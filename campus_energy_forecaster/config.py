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
    # California commercial electricity price, 2025: 26.16 cents/kWh (EIA-861 final annual data, "Historical State Data",
    # Total Electric Industry). For reference the US commercial average is 13.37 cents/kWh. The demo building is in
    # Berkeley, California. Replace with the site's own tariff.
    tariff_usd_per_kwh: float = 0.2616
    # CAMX (WECC California) grid CO2 total output emission rate, 428.464 lb/MWh = 0.194 kg/kWh (EPA eGRID2023 Revision 2).
    # For reference the US average is 767.209 lb/MWh = 0.348 kg/kWh. Replace with the local grid factor.
    carbon_kg_per_kwh: float = 0.194
