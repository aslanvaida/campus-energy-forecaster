"""Load the public LBNL Building 59 dataset (Luo et al. 2022, CC0) as one tidy hourly frame.

Columns (kW, hourly mean of the 15-minute readings), indexed in local time (America/Los_Angeles):
    hvac       both wings' HVAC meters        lighting  south-wing lighting meter (the north-wing meter is not in the data)
    plug       both wings' miscellaneous electric loads (plug loads)
    total      hvac + lighting + plug
    temp, rh, solar   outdoor air temperature (degC), relative humidity (%), solar radiation (W/m2)
"""
from pathlib import Path

import pandas as pd

from campus_energy_forecaster.config import LBNL_DIR

LOAD_COLUMNS = ["hvac", "lighting", "plug"]
LOCAL_TZ = "America/Los_Angeles"      # Berkeley, California


def find_csv(name: str, root: Path = LBNL_DIR) -> Path:
    hits = list(Path(root).rglob(name))
    if not hits:
        raise FileNotFoundError(f"{name} not found under {root}. Run `python scripts/download_data.py` first.")
    return hits[0]


def _hourly(path: Path, columns: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True, usecols=lambda c: c == "date" or c in columns)
    return df.apply(pd.to_numeric, errors="coerce").resample("h").mean()


def load_building(root: Path = LBNL_DIR) -> pd.DataFrame:
    ele = _hourly(find_csv("ele.csv", root), ["mels_S", "mels_N", "lig_S", "hvac_N", "hvac_S"])
    wx = _hourly(find_csv("site_weather.csv", root), ["air_temp_set_1", "relative_humidity_set_1", "solar_radiation_set_1"])
    out = pd.DataFrame({
        "hvac": ele[["hvac_N", "hvac_S"]].sum(axis=1, min_count=2),      # NaN if either wing is missing
        "lighting": ele["lig_S"],
        "plug": ele[["mels_N", "mels_S"]].sum(axis=1, min_count=2),
    })
    out["total"] = out[LOAD_COLUMNS].sum(axis=1, min_count=3)
    out = out.join(wx.rename(columns={"air_temp_set_1": "temp", "relative_humidity_set_1": "rh", "solar_radiation_set_1": "solar"}))
    out = out.loc[:"2020-12-31 23:00"]                                    # the last row of the files is 2021-01-01 00:00
    return to_local_time(out).loc["2018-01-01":]


def to_local_time(df: pd.DataFrame, tz: str = LOCAL_TZ) -> pd.DataFrame:
    """The files are timestamped in UTC (solar radiation peaks at 20:00, occupancy at 17:00-21:00). Convert to the
    building's local clock so hours, weekdays and holidays mean what a facilities manager expects. The repeated
    hour at the end of daylight saving time is averaged; the skipped hour at its start becomes a gap."""
    out = df.copy()
    out.index = out.index.tz_localize("UTC").tz_convert(tz).tz_localize(None)
    out = out.groupby(level=0).mean().asfreq("h")
    out.index.name = "timestamp"
    return out
