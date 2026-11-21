"""Download the public LBNL Building 59 dataset (CC0, 263 MB) into data/external/lbnl/ and unzip it.

Luo et al., "A three-year dataset supporting research on building energy, HVAC controls, and occupancy analytics",
Lawrence Berkeley National Laboratory. https://zenodo.org/records/5951008
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from campus_energy_forecaster.config import LBNL_DIR

URL = "https://zenodo.org/records/5951008/files/Building_59.zip?download=1"


def main():
    if list(LBNL_DIR.rglob("ele.csv")):
        print("LBNL Building 59 already downloaded:", LBNL_DIR)
        return
    LBNL_DIR.mkdir(parents=True, exist_ok=True)
    archive = LBNL_DIR / "Building_59.zip"
    print(f"downloading {URL} ...", flush=True)
    urllib.request.urlretrieve(URL, archive)
    zipfile.ZipFile(archive).extractall(LBNL_DIR)
    archive.unlink()
    print("done:", LBNL_DIR)


if __name__ == "__main__":
    main()
