# COVID-19 Dashboard - VS Code Notebook

Open `covid_dashboard.ipynb` in VS Code with the Python and Jupyter extensions.

## Main data source

The main input is OWID's current [compact COVID-19 CSV from its Data Catalog](https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv), which contains cases, deaths, vaccinations, and country/date identifiers in one file. The project also keeps the requested [Kaggle `bolkonsky/covid19` dataset](https://www.kaggle.com/datasets/bolkonsky/covid19) as a fallback/reference; its cached snapshot is older and does not include vaccination data. OWID's [COVID documentation](https://docs.owid.io/projects/etl/api/covid/) describes the compact file and its metadata.

Wikipedia is an optional web-scraping comparison source. It is not the primary dataset and its current totals may cover a different time period than the OWID data.

## Setup

In the VS Code terminal, create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Use **Select Kernel** at the upper-right of the notebook and choose `.venv`, then choose **Run All**. On first run, the pipeline downloads OWID's compact CSV to `work/owid_compact_latest.csv`. To use a local CSV instead, set `COVID_DATA_PATH` to that file or its containing folder. If the OWID catalog cannot be reached, the pipeline falls back to KaggleHub.

The notebook includes four Python basics requirements, list/dictionary/set/tuple examples, NumPy descriptive statistics, Pandas analysis, and Markdown insight notes.

Generated files are saved in `outputs/`: cleaned data, country summaries, dashboard JSON, a data-quality audit, a mini report, and three charts (new cases over time, a Pearson correlation heatmap including vaccination, and the distribution of fully vaccinated coverage by country).

## HTML dashboard

Run all cells in `covid_dashboard.ipynb` first so it creates `outputs/dashboard_data.json`. Then open `dashboard.html` with **Open with Live Server** in VS Code. The dashboard has continent and country filters, top-country comparisons for cases/deaths/vaccination, monthly case and death trends per million people, and a separate monthly vaccination trend. Missing values remain gaps rather than being filled with zero.
