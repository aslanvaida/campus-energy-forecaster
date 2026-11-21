"""Download the public datasets into data/external/ (nothing is committed).

    python scripts/download_data.py            # LBNL Building 59 (263 MB, CC0): the main demo building
    python scripts/download_data.py bdg2       # Building Data Genome 2: electricity, metadata, weather only (about 200 MB, CC BY 4.0)

LBNL Building 59: Luo et al., "A three-year dataset supporting research on building energy, HVAC controls, and occupancy
analytics", Lawrence Berkeley National Laboratory. https://zenodo.org/records/5951008
Building Data Genome Project 2: Miller et al. (2020), Scientific Data. https://zenodo.org/records/3887306
The BDG2 download reads only the three needed files out of the 595 MB archive (pip install remotezip).
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from campus_energy_forecaster.config import BDG2_DIR, LBNL_DIR

LBNL_URL = "https://zenodo.org/records/5951008/files/Building_59.zip?download=1"
BDG2_URL = "https://zenodo.org/records/3887306/files/buds-lab/building-data-genome-project-2-v1.0.zip?download=1"
BDG2_FILES = ("data/metadata/metadata.csv", "data/meters/cleaned/electricity_cleaned.csv", "data/weather/weather.csv")


def lbnl():
    if list(LBNL_DIR.rglob("ele.csv")):
        print("LBNL Building 59 already downloaded:", LBNL_DIR)
        return
    LBNL_DIR.mkdir(parents=True, exist_ok=True)
    archive = LBNL_DIR / "Building_59.zip"
    print(f"downloading {LBNL_URL} ...", flush=True)
    urllib.request.urlretrieve(LBNL_URL, archive)
    zipfile.ZipFile(archive).extractall(LBNL_DIR)
    archive.unlink()
    print("done:", LBNL_DIR)


def bdg2():
    from remotezip import RemoteZip
    BDG2_DIR.mkdir(parents=True, exist_ok=True)
    with RemoteZip(BDG2_URL) as z:
        for info in z.infolist():
            for want in BDG2_FILES:
                if info.filename.endswith(want):
                    target = BDG2_DIR / Path(want).name
                    if target.exists():
                        print("have", target.name)
                        continue
                    print("extracting", target.name, f"({info.file_size / 1e6:.0f} MB)", flush=True)
                    target.write_bytes(z.read(info.filename))
    print("done:", BDG2_DIR)


if __name__ == "__main__":
    {"lbnl": lbnl, "bdg2": bdg2}[sys.argv[1] if len(sys.argv) > 1 else "lbnl"]()
