# data-analytics-jci
Repo for assignments on Data Analytics course from Johan Cruyff Institute.

## Assignment #3: GPS Athlete Training Session Analysis

Analysis of a single football training session recorded with a 10 Hz GPS tracker and a heart rate monitor. The goal is to turn raw tracking data into a clear, coach-facing picture of workload, movement and fatigue.

### What The Analysis Covers

- Data validation and cleaning (missing values, timestamp parsing, gap detection, speed cross-check)
- Transformations: speed in m/s, distance, acceleration, speed zones, sprint detection, heart rate zones
- Session split into two halves and 15-minute blocks to facilitate analysis
- Fatigue analysis using an efficiency index (distance per heartbeat)
- Five images: session overview, movement map, occupancy heatmap, intensity profile, and a per-block fatigue panel

The full write-up for the coach is in `report/` (PDF).

### Project Structure

    data/        raw data (not tracked in git — see below)
    notebooks/   analysis.ipynb (the full analysis)
    images/      images exported by the notebook
    report/      final PDF report

### Setup

Requires Python 3.11

```bash
# clone
git clone https://github.com/molendaluisa/data-analytics-jci.git
cd data-analytics-jci

# create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
```

### Data

The raw data file is **not included** in this repository (large file size).
To run the notebook, place the data file in `data/` and name it `raw_data.csv`. Optionally, you can always modify the path in the 1st notebook cell to point to where you file is. The dataset is also available at [[Data Analytics in Sports JCI] Assignment #3](https://drive.google.com/drive/folders/1UOdxvXjD4mikWyyH5Nra7soX9SJsscHk?usp=drive_link).

### Running

Open `notebooks/analysis.ipynb` in VS Code or Jupyter, select the `.venv` kernel and run all cells from top to bottom. Figures are saved to `images/`.

### Notes & Assumptions

- The sport and athlete details are unknown. Football is assumed based on the field dimensions (118 × 72 m). Given in the original spreadsheet.
- Heart rate zones use the session maximum (189 bpm) as a proxy, since the true maximum is unknown.
- See the report appendix for full method details and limitations.