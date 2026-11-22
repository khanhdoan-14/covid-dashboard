"""Pipeline OOP cho du an Dashboard COVID-19."""

from __future__ import annotations

import json
import os
import re
from io import StringIO
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# List: nhom quoc gia duoc ve tren bieu do duong trong notebook.
SELECTED_COUNTRIES: list[str] = ["Vietnam", "United States", "India", "Brazil", "United Kingdom"]
# Dict: doi ma ISO thanh ten de tham khao trong bao cao.
COUNTRY_CODES: dict[str, str] = {"VNM": "Viet Nam", "USA": "United States", "IND": "India", "BRA": "Brazil", "GBR": "United Kingdom"}
# Set: 5 chau luc hien thi. OWID tach Bac My va Nam My, nen duoc gop thanh America.
FIVE_CONTINENTS: set[str] = {"Africa", "America", "Asia", "Europe", "Oceania"}
SOURCE_CONTINENTS: set[str] = {"Africa", "Asia", "Europe", "North America", "South America", "Oceania"}
CONTINENTS: set[str] = set()
# Tuple: khoang thoi gian phan tich.
DATE_WINDOW: tuple[str, str] = ("2020-01-01", "2023-12-31")

KAGGLE_DATASET_HANDLE = "bolkonsky/covid19"
KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/bolkonsky/covid19"
OWID_COMPACT_CSV_URL = "https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv"
OWID_COVID_DOCS_URL = "https://docs.owid.io/projects/etl/api/covid/"
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/COVID-19_pandemic_by_country_and_territory"


# Ham 1: loc DataFrame theo danh sach quoc gia, hoac tra ve toan bo khi danh sach rong.
def filter_countries(df: pd.DataFrame, countries: Iterable[str] | None) -> pd.DataFrame:
    """Trả về các dòng của danh sách quốc gia, hoặc toàn bộ bảng nếu không lọc."""
    return df.copy() if countries is None else df[df["location"].isin(list(countries))].copy()


# Ham 2: chuyen cot ngay thang va bo sung cac cot nam/thang de nhom du lieu.
def format_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa ngày và tạo các cột năm, tháng để nhóm dữ liệu."""
    result = df.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.dropna(subset=["date"])
    result["year"] = result["date"].dt.year
    result["month"] = result["date"].dt.month
    result["year_month"] = result["date"].dt.to_period("M").astype(str)
    return result


# Ham 3: tinh mot chi so tren mot trieu dan, tranh chia cho dan so bang 0.
def calculate_per_million(df: pd.DataFrame, metric_column: str, population_column: str = "population") -> pd.Series:
    """Tính chỉ số trên một triệu dân, bỏ qua mẫu số dân số không hợp lệ."""
    metric = pd.to_numeric(df[metric_column], errors="coerce")
    population = pd.to_numeric(df[population_column], errors="coerce").replace(0, np.nan)
    return metric.div(population).mul(1_000_000)


# Ham 4: phan loai ty le tiem du lieu theo ba muc de hien thi tren dashboard.
def classify_vaccination_level(rate: float) -> str:
    """Xếp tỷ lệ tiêm chủng vào nhóm Low, Medium, High hoặc Unknown."""
    if pd.isna(rate):
        return "Unknown"
    if rate < 30:
        return "Low"
    if rate <= 70:
        return "Medium"
    return "High"


class CovidDataProcessor:
    """Quản lý các bước tải, làm sạch, phân tích, trực quan hóa và xuất dữ liệu."""

    numeric_columns = ["total_cases", "new_cases", "new_cases_smoothed", "total_deaths", "new_deaths_smoothed_per_million", "total_cases_per_million", "new_cases_per_million", "new_cases_smoothed_per_million", "total_deaths_per_million", "people_fully_vaccinated_per_hundred", "population"]

    # Ham khoi tao: luu cau hinh, duong dan va cac bien ket qua cua pipeline.
    def __init__(self, countries: list[str] | None = None, date_window: tuple[str, str] = DATE_WINDOW,
                 output_dir: str | Path = "outputs", data_path: str | Path | None = None,
                 visualization_countries: list[str] | None = None) -> None:
        """Lưu cấu hình pipeline và khởi tạo các vùng chứa kết quả xử lý."""
        self.countries = countries
        self.visualization_countries = visualization_countries or SELECTED_COUNTRIES
        self.date_window = date_window
        self.output_dir = Path(output_dir)
        self.data_path = Path(data_path) if data_path else None
        self.data_source: str | None = None
        self.raw: pd.DataFrame | None = None
        self.cleaned: pd.DataFrame | None = None
        self.subset: pd.DataFrame | None = None
        self.visual_data: pd.DataFrame | None = None
        self.summary_all: pd.DataFrame | None = None
        self.summary: pd.DataFrame | None = None
        self.wiki_summary: pd.DataFrame | None = None
        self.findings: dict[str, object] = {}

    # Ham tai du lieu: uu tien CSV Kaggle da co tren may, neu chua co thi tai bang KaggleHub.
    def load_data(self) -> pd.DataFrame:
        """Đọc CSV OWID; nếu tải thất bại thì thử dataset Kaggle làm nguồn dự phòng."""
        environment_path = os.environ.get("COVID_DATA_PATH")
        required = {"continent", "date", "population", "new_cases"}
        candidates = [
            self.data_path,
            Path(environment_path) if environment_path else None,
            Path("data/owid_compact_latest.csv"),
            Path("work/owid_compact_latest.csv"),
            Path("data/kaggle_covid19"),
            Path("data/owid-covid-data.csv"),
        ]
        local_path = next((path for path in candidates if path and path.exists()), None)

        if local_path is not None:
            csv_path = self._find_dataset_csv(local_path, required)
            self.data_source = self._describe_source(csv_path)
        else:
            try:
                csv_path = self._download_owid_compact()
                self.data_source = "OWID Catalog: current compact COVID-19 CSV"
            except Exception as error:
                try:
                    import kagglehub
                    downloaded_path = Path(kagglehub.dataset_download(KAGGLE_DATASET_HANDLE))
                    csv_path = self._find_dataset_csv(downloaded_path, required)
                    self.data_source = f"Kaggle fallback: {KAGGLE_DATASET_HANDLE} ({csv_path.name})"
                except Exception as fallback_error:
                    raise RuntimeError(
                        "Could not retrieve the current OWID catalog CSV or the Kaggle fallback. "
                        "Set COVID_DATA_PATH to a local OWID/Kaggle CSV and retry."
                    ) from fallback_error

        self.raw = pd.read_csv(csv_path, low_memory=False)
        if {"country", "code"}.issubset(self.raw.columns):
            self.raw = self.raw.rename(columns={"country": "location", "code": "iso_code"})
        missing = required.difference(self.raw.columns)
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
        if not {"iso_code", "location"}.issubset(self.raw.columns):
            raise ValueError("CSV must contain country identifiers as either (iso_code, location) or (code, country).")
        print(f"Loaded {len(self.raw):,} rows from {self.data_source}.")
        return self.raw

    @staticmethod
    def _describe_source(csv_path: Path) -> str:
        """Return a concise, human-readable source label for cached/local inputs."""
        if csv_path.name.lower() == "owid_compact_latest.csv":
            return "OWID Catalog: current compact COVID-19 CSV (cached)"
        if "kagglehub_cache" in str(csv_path).lower() or "kagglehub" in str(csv_path).lower():
            return f"Kaggle: {KAGGLE_DATASET_HANDLE} ({csv_path.name}, cached)"
        return f"Local CSV: {csv_path}"

    @staticmethod
    def _download_owid_compact() -> Path:
        """Tải CSV OWID theo từng khối và lưu vào cache cục bộ."""
        target = Path("work/owid_compact_latest.csv")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".csv.part")
        request = Request(OWID_COMPACT_CSV_URL, headers={"User-Agent": "COVID-P5-educational-project/1.0"})
        with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            expected_size = int(response.headers.get("Content-Length") or 0)
            copied = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
                copied += len(block)
        if expected_size and copied != expected_size:
            temporary.unlink(missing_ok=True)
            raise IOError(f"Incomplete OWID CSV download: {copied} of {expected_size} bytes.")
        temporary.replace(target)
        return target

    @staticmethod
    def _find_dataset_csv(path: Path, required: set[str]) -> Path:
        """Tìm CSV có schema OWID phù hợp trong file hoặc thư mục được chỉ định."""
        candidates = [path] if path.is_file() else sorted(path.rglob("*.csv"))
        matching: list[Path] = []
        for csv_path in candidates:
            if csv_path.suffix.lower() != ".csv":
                continue
            try:
                columns = set(pd.read_csv(csv_path, nrows=0).columns)
            except Exception:
                continue
            legacy_schema = {"iso_code", "location"}.issubset(columns)
            compact_schema = {"code", "country"}.issubset(columns)
            if required.issubset(columns) and (legacy_schema or compact_schema):
                matching.append(csv_path)
        if not matching:
            raise FileNotFoundError(
                f"No CSV with the required OWID columns was found in: {path}"
            )
        return next((item for item in matching if item.name.lower() == "owid_compact_latest.csv"),
                    next((item for item in matching if item.name.lower() == "owid-covid-data.csv"),
                         max(matching, key=lambda item: item.stat().st_size)))

    # Ham lam sach: chi giu cac quoc gia thuoc 5 chau luc va chuan hoa chi so.
    def clean_data(self) -> pd.DataFrame:
        """Lọc quốc gia, chuẩn hóa kiểu dữ liệu và bổ sung chỉ số còn thiếu."""
        if self.raw is None:
            raise RuntimeError("Call load_data() before clean_data().")
        df = self.raw.copy()
        # Loai bo World, income groups va cac dong tong hop OWID_.
        df = df[~df["iso_code"].astype(str).str.startswith("OWID_")]
        df = df[df["continent"].isin(SOURCE_CONTINENTS)].dropna(subset=["iso_code", "location"])
        # Gop North America va South America thanh America de dashboard co dung 5 chau luc.
        df["continent"] = df["continent"].replace({"North America": "America", "South America": "America"})
        df = format_dates(df)
        start, end = map(pd.Timestamp, self.date_window)
        df = df[df["date"].between(start, end)].copy()
        for column in self.numeric_columns:
            if column not in df.columns:
                df[column] = np.nan
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df = df.sort_values(["iso_code", "date"]).reset_index(drop=True)
        cumulative = ["total_cases", "total_deaths", "total_cases_per_million", "total_deaths_per_million", "people_fully_vaccinated_per_hundred", "population"]
        # Dien du lieu tich luy bang gia tri gan nhat cua cung mot quoc gia.
        df[cumulative] = df.groupby("iso_code")[cumulative].ffill()
        # Preserve missing reports and negative revisions from the source; neither means zero.
        rolling_cases = df.groupby("iso_code")["new_cases"].transform(lambda values: values.rolling(window=7, min_periods=1).mean())
        df["new_cases_smoothed"] = df["new_cases_smoothed"].fillna(rolling_cases)
        for metric in ("total_cases", "total_deaths", "new_cases_smoothed"):
            target = f"{metric}_per_million"
            calculated = calculate_per_million(df, metric)
            existing = pd.to_numeric(df[target], errors="coerce") if target in df.columns else pd.Series(np.nan, index=df.index, dtype="float64")
            df[target] = existing.fillna(calculated)
        # Keep the source's smoothed rate when present; calculate only missing observations.
        df["new_cases_per_million"] = pd.to_numeric(df["new_cases_per_million"], errors="coerce").fillna(calculate_per_million(df, "new_cases"))
        df["new_cases_smoothed_per_million"] = pd.to_numeric(df["new_cases_smoothed_per_million"], errors="coerce").fillna(calculate_per_million(df, "new_cases_smoothed"))
        df["vaccination_level"] = df["people_fully_vaccinated_per_hundred"].map(classify_vaccination_level)
        global CONTINENTS
        CONTINENTS = set(df["continent"].dropna().unique())
        self.cleaned = df
        self.subset = filter_countries(df, self.countries)
        print(f"Cleaned {len(df):,} country-day rows from {df['location'].nunique()} countries in {len(CONTINENTS)} continents.")
        return self.subset

    # Ham phu tro: doi chuoi so tu Wikipedia thanh so thuc neu co the.
    @staticmethod
    def _parse_number(value: object) -> float:
        """Chuyển số trên Wikipedia thành số thực và bỏ ký hiệu chú thích."""
        digits = re.sub(r"[^0-9]", "", re.sub(r"\[.*?\]", "", str(value)))
        return float(digits) if digits else np.nan

    # Ham scrape: cai bang so lieu tong hop tu Wikipedia de doi chieu, neu mang cho phep.
    def scrape_wikipedia_summary(self) -> pd.DataFrame | None:
        """Cào bảng tổng ca và tử vong Wikipedia để đối chiếu tham khảo."""
        try:
            request = Request(
                WIKIPEDIA_URL,
                headers={"User-Agent": "CovidDashboard/1.0 (educational data analysis)"},
            )
            with urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", errors="replace")
            tables = pd.read_html(StringIO(html))
            for table in tables:
                columns = [" ".join(map(str, col)) if isinstance(col, tuple) else str(col) for col in table.columns]
                country = next((column for column in columns if column.lower() in {"country", "location"}), None)
                cases = next((column for column in columns if column.lower() == "cases"), None)
                deaths = next((column for column in columns if column.lower() == "deaths"), None)
                if country and cases and deaths and len(table) > 50:
                    table.columns = columns
                    self.wiki_summary = pd.DataFrame({
                        "location": table[country].astype(str).str.replace(r"\[.*?\]", "", regex=True).str.strip(),
                        "wiki_cases": table[cases].map(self._parse_number),
                        "wiki_deaths": table[deaths].map(self._parse_number),
                    }).dropna(subset=["location", "wiki_cases"])
                    print(f"Scraped {len(self.wiki_summary):,} Wikipedia rows.")
                    return self.wiki_summary
        except Exception as error:
            print(f"Wikipedia comparison skipped: {error}")
        return None

    # Ham phan tich: tao bang tom tat cho tat ca quoc gia va tim dinh dich cua nhom hien thi.
    def analyze_country_trends(self, include_wikipedia: bool = True) -> pd.DataFrame:
        """Tổng hợp chỉ số theo quốc gia và chuẩn bị dữ liệu cho biểu đồ."""
        if self.cleaned is None:
            raise RuntimeError("Call clean_data() before analyze_country_trends().")
        self.summary_all = self.cleaned.groupby(["iso_code", "location"], as_index=False).agg(
            continent=("continent", "first"), total_cases=("total_cases", "max"),
            total_deaths=("total_deaths", "max"),
            cases_per_million=("total_cases_per_million", "max"),
            deaths_per_million=("total_deaths_per_million", "max"),
            avg_new_cases_per_million=("new_cases_smoothed_per_million", "mean"),
            vaccination_rate=("people_fully_vaccinated_per_hundred", "last"),
        )
        self.summary_all["vaccination_level"] = self.summary_all["vaccination_rate"].map(classify_vaccination_level)
        self.summary_all["country_code_name"] = self.summary_all["iso_code"].map(COUNTRY_CODES)
        if include_wikipedia:
            wiki_summary = self.wiki_summary if self.wiki_summary is not None else self.scrape_wikipedia_summary()
            if wiki_summary is not None:
                self.summary_all = self.summary_all.merge(wiki_summary, on="location", how="left")
        self.summary = filter_countries(self.summary_all, self.countries)
        self.visual_data = filter_countries(self.cleaned, self.visualization_countries)
        peak_indices = self.visual_data.groupby("location")["new_cases_smoothed"].idxmax()
        self.findings["peaks"] = self.visual_data.loc[peak_indices, ["location", "date", "new_cases_smoothed"]].sort_values("location")
        self.findings["high_vaccination"] = self.cleaned[self.cleaned["people_fully_vaccinated_per_hundred"] >= 70].groupby("location")["date"].min().sort_values().head(5)
        return self.summary.sort_values("location").reset_index(drop=True)

    # Ham truc quan hoa: ve bieu do duong, heatmap va histogram.
    def plot_all(self, show: bool = True) -> list[Path]:
        """Tạo và lưu biểu đồ xu hướng, tương quan và phân phối vaccine."""
        if self.summary_all is None or self.visual_data is None:
            raise RuntimeError("Call analyze_country_trends() before plot_all().")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="deep")
        saved: list[Path] = []
        fig, ax = plt.subplots(figsize=(14, 4.8))
        sns.lineplot(
            data=self.visual_data, x="date", y="new_cases_smoothed_per_million", hue="location", ax=ax,
            linewidth=1.8,
        )
        ax.set(title="Ca nhiễm mới trung bình 7 ngày trên một triệu dân", xlabel="Ngày", ylabel="Ca / 1 triệu dân")
        ax.set_ylim(bottom=0)
        ax.set_xlim(self.visual_data["date"].min(), self.visual_data["date"].max())
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[3, 6, 9, 12]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%y-%m"))
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#d9e2e2", linewidth=.8)
        ax.grid(axis="x", visible=False)
        ax.legend(title=None, loc="upper center", bbox_to_anchor=(.5, -.16), ncol=5, frameon=False)
        fig.tight_layout(rect=(0, .08, 1, 1))
        saved.append(self.output_dir / "chart1_line_new_cases.png")
        fig.savefig(saved[-1], dpi=160, bbox_inches="tight")
        if show: plt.show()
        plt.close(fig)
        heatmap_columns = {
            "cases_per_million": "Ca nhiễm tích lũy / 1 triệu dân",
            "deaths_per_million": "Tử vong tích lũy / 1 triệu dân",
            "avg_new_cases_per_million": "Ca mới TB 7 ngày / 1 triệu dân",
            "vaccination_rate": "Tiêm đủ liều cuối kỳ (%)",
        }
        correlations = self.summary_all[list(heatmap_columns)].rename(columns=heatmap_columns).corr(min_periods=2)
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(correlations, annot=True, fmt=".2f", cmap="coolwarm", center=0,
                    vmin=-1, vmax=1, square=True, linewidths=.5, ax=ax,
                    cbar_kws={"label": "He so tuong quan Pearson"}, mask=correlations.isna())
        ax.set(title="Tương quan Pearson giữa các chỉ số trên một triệu dân")
        fig.tight_layout()
        saved.append(self.output_dir / "chart2_heatmap_covid_indicators.png")
        fig.savefig(saved[-1], dpi=160, bbox_inches="tight")
        if show: plt.show()
        plt.close(fig)

        vaccination_rates = self.summary_all["vaccination_rate"].dropna()
        fig, ax = plt.subplots(figsize=(9, 5))
        if vaccination_rates.empty:
            ax.text(.5, .5, "Không có dữ liệu tiêm chủng trong nguồn", ha="center", va="center",
                    transform=ax.transAxes)
        else:
            sns.histplot(vaccination_rates, bins="fd", color="#078c84", edgecolor="white", ax=ax)
        ax.set(title="Phân bố tỷ lệ tiêm đủ liều theo quốc gia",
               xlabel="Người hoàn thành phác đồ ban đầu (%)", ylabel="Số lượng quốc gia")
        fig.tight_layout()
        saved.append(self.output_dir / "chart3_hist_vaccination_rate.png")
        fig.savefig(saved[-1], dpi=160, bbox_inches="tight")
        if show: plt.show()
        plt.close(fig)

        return saved

    # Ham tao du lieu cho HTML: rut gon du lieu ngay thanh chuoi thoi gian theo thang.
    def _build_dashboard_payload(self) -> dict[str, object]:
        """Tạo payload JSON gồm dữ liệu quốc gia và xu hướng tháng cho dashboard."""
        if self.cleaned is None or self.summary_all is None:
            raise RuntimeError("Run analysis before building dashboard data.")
        monthly = self.cleaned.groupby(["iso_code", "location", "continent", "year_month"], as_index=False).agg(
            new_cases_smoothed_per_million=("new_cases_smoothed_per_million", "mean"),
            new_deaths_smoothed_per_million=("new_deaths_smoothed_per_million", "mean"),
            new_cases_smoothed=("new_cases_smoothed", "mean"),
            deaths_per_million=("total_deaths_per_million", "max"),
            vaccination_rate=("people_fully_vaccinated_per_hundred", "last")
        ).replace({np.nan: None})
        observed_start = self.cleaned["date"].min().strftime("%Y-%m-%d")
        observed_end = self.cleaned["date"].max().strftime("%Y-%m-%d")
        vaccination_available = bool(self.cleaned["people_fully_vaccinated_per_hundred"].notna().any())
        return {"data_source": self.data_source,
                "date_window": [observed_start, observed_end],
                "requested_date_window": list(self.date_window),
                "vaccination_available": vaccination_available,
                "continents": sorted(CONTINENTS),
                "countries": self.summary_all.replace({np.nan: None}).to_dict(orient="records"),
                "monthly_trends": monthly.to_dict(orient="records")}

    def _build_data_quality_audit(self) -> pd.DataFrame:
        """Đối chiếu dữ liệu nguồn với dữ liệu sạch và trả về bảng kiểm tra."""
        if self.raw is None or self.cleaned is None or self.summary_all is None:
            raise RuntimeError("Run analysis before building the data-quality audit.")

        source_dates = pd.to_datetime(self.raw["date"], errors="coerce")
        source_cases = pd.to_numeric(self.raw["new_cases"], errors="coerce")
        source_scope = self.raw.loc[
            self.raw["continent"].isin(SOURCE_CONTINENTS)
            & ~self.raw["iso_code"].astype(str).str.startswith("OWID_")
            & pd.to_datetime(self.raw["date"], errors="coerce").between(*map(pd.Timestamp, self.date_window))
            & self.raw["location"].notna()
        ].copy()
        source_scope["date"] = pd.to_datetime(source_scope["date"], errors="coerce")
        source_cases_in_scope = pd.to_numeric(source_scope["new_cases"], errors="coerce")

        source_values = source_scope[["location", "date", "new_cases"]]
        clean_values = self.cleaned[["location", "date", "new_cases"]]
        comparison = source_values.merge(
            clean_values, on=["location", "date"], how="outer", suffixes=("_source", "_cleaned"), indicator=True
        )
        cases_match = comparison["_merge"].eq("both").all() and np.isclose(
            pd.to_numeric(comparison["new_cases_source"], errors="coerce"),
            pd.to_numeric(comparison["new_cases_cleaned"], errors="coerce"), equal_nan=True,
        ).all()

        vaccine = pd.to_numeric(source_scope["people_fully_vaccinated_per_hundred"], errors="coerce")
        reported_vaccine = vaccine.notna()
        clean_vaccine = self.cleaned.set_index(["location", "date"])["people_fully_vaccinated_per_hundred"]
        vaccine_match = True
        if reported_vaccine.any():
            keys = pd.MultiIndex.from_frame(source_scope.loc[reported_vaccine, ["location", "date"]])
            vaccine_match = np.isclose(
                vaccine.loc[reported_vaccine].to_numpy(dtype=float),
                pd.to_numeric(clean_vaccine.reindex(keys), errors="coerce").to_numpy(dtype=float),
                equal_nan=True,
            ).all()

        source_keys = [key for key in ("location", "date") if key in self.raw]
        clean_duplicate_count = int(self.cleaned.duplicated(["iso_code", "date"]).sum())
        countries = self.cleaned["location"].nunique()
        summary_countries = self.summary_all["location"].nunique()
        checks = [
            ("Source dataset", self.data_source or "Unknown", "OWID compact CSV (Kaggle fallback)", "INFO"),
            ("Source rows", len(self.raw), "As supplied by source", "INFO"),
            ("Source date range", f"{source_dates.min().date()} to {source_dates.max().date()}", f"Requested {self.date_window[0]} to {self.date_window[1]}", "INFO"),
            ("Duplicate source country-date keys", int(self.raw.duplicated(source_keys).sum()), 0, "PASS" if len(source_keys) == 2 and not self.raw.duplicated(source_keys).any() else "REVIEW"),
            ("Source missing new_cases", int(source_cases.isna().sum()), "Preserved as missing", "INFO"),
            ("Negative new_cases revisions in source", int(source_cases.lt(0).sum()), "Preserved; source revisions", "INFO"),
            ("Eligible source rows in analysis window", len(source_scope), len(self.cleaned), "PASS" if len(source_scope) == len(self.cleaned) else "REVIEW"),
            ("Missing new_cases in eligible source rows", int(source_cases_in_scope.isna().sum()), int(self.cleaned["new_cases"].isna().sum()), "PASS" if source_cases_in_scope.isna().sum() == self.cleaned["new_cases"].isna().sum() else "REVIEW"),
            ("Negative revisions in eligible source rows", int(source_cases_in_scope.lt(0).sum()), int(self.cleaned["new_cases"].lt(0).sum()), "PASS" if source_cases_in_scope.lt(0).sum() == self.cleaned["new_cases"].lt(0).sum() else "REVIEW"),
            ("Source vs cleaned new_cases values", "Exact match" if cases_match else "Mismatch", "Match by country and date", "PASS" if cases_match else "REVIEW"),
            ("Reported vaccination values preserved", "Exact match" if vaccine_match else "Mismatch", "All reported source values preserved", "PASS" if vaccine_match else "REVIEW"),
            ("Cleaned rows", len(self.cleaned), "Country rows in requested date window", "INFO"),
            ("Duplicate cleaned country-date keys", clean_duplicate_count, 0, "PASS" if not clean_duplicate_count else "REVIEW"),
            ("Cleaned country count vs summary", f"{countries} vs {summary_countries}", "Equal", "PASS" if countries == summary_countries else "REVIEW"),
            ("Vaccination observations", int(self.cleaned["people_fully_vaccinated_per_hundred"].notna().sum()), "Reported source observations", "INFO"),
            ("Countries with vaccination data", int(self.summary_all["vaccination_rate"].notna().sum()), "Country-level latest values in analysis window", "INFO"),
        ]
        return pd.DataFrame(checks, columns=["check", "observed", "expected", "status"])

    def _build_summary_report(self) -> str:
        """Tạo báo cáo ngắn về nguồn, phương pháp, kết quả và giới hạn dữ liệu."""
        if self.cleaned is None or self.summary_all is None:
            raise RuntimeError("Run analysis before building the summary report.")

        summary = self.summary_all
        cases = self.cleaned["new_cases_smoothed"].dropna()
        vaccine = summary["vaccination_rate"].dropna()
        correlation = summary[["deaths_per_million", "vaccination_rate"]].dropna()
        correlation_value = correlation.corr().iloc[0, 1] if len(correlation) >= 2 else np.nan

        def leader(column: str, descending: bool = True) -> pd.Series | None:
            """Lấy quốc gia đứng đầu theo chỉ số; trả về None nếu không có dữ liệu."""
            rows = summary.dropna(subset=[column]).sort_values(column, ascending=not descending)
            return None if rows.empty else rows.iloc[0]

        top_cases = leader("total_cases")
        top_deaths = leader("deaths_per_million")
        top_vaccine = leader("vaccination_rate")
        findings = [
            f"{top_cases['location']} có tổng ca nhiễm ghi nhận cao nhất ({int(top_cases['total_cases']):,})." if top_cases is not None else "Không có dữ liệu tổng ca nhiễm để xếp hạng.",
            f"{top_deaths['location']} có tử vong trên một triệu dân cao nhất ({top_deaths['deaths_per_million']:,.1f})." if top_deaths is not None else "Không có dữ liệu tử vong để xếp hạng.",
            f"{top_vaccine['location']} có tỷ lệ tiêm đủ liều cuối kỳ cao nhất ({top_vaccine['vaccination_rate']:.1f}%)." if top_vaccine is not None else "Không có dữ liệu tiêm chủng để xếp hạng.",
            f"Tương quan Pearson giữa tử vong tích lũy trên một triệu dân và tiêm đủ liều là {correlation_value:.2f} (n={len(correlation)}; không suy ra quan hệ nhân quả)." if len(correlation) >= 2 else "Không đủ dữ liệu để tính tương quan tử vong và vaccine.",
        ]

        wiki_note = (
            f"Đã ghép Wikipedia theo tên cho {int(summary['wiki_cases'].notna().sum())} quốc gia."
            if "wiki_cases" in summary else "Không có dữ liệu Wikipedia; phân tích vẫn dùng OWID."
        )
        vaccine_note = (
            f"Có {int(vaccine.gt(100).sum())} quốc gia/vùng ghi nhận trên 100%; có thể do mẫu số dân số hoặc cách báo cáo."
            if vaccine.gt(100).any() else "Không có tỷ lệ tiêm chủng vượt 100% trong bảng tóm tắt."
        )
        continents = ", ".join(sorted(CONTINENTS))
        findings_text = "\n".join(f"- {item}" for item in findings)
        vaccine_median = f"{vaccine.median():.1f}%" if not vaccine.empty else "không có dữ liệu"
        cases_mean = f"{cases.mean():,.2f}" if not cases.empty else "không có dữ liệu"
        cases_median = f"{cases.median():,.2f}" if not cases.empty else "không có dữ liệu"
        return f"""# Báo cáo mini: Phân tích dữ liệu COVID-19

## Mục tiêu và nguồn dữ liệu

Nguồn chính là compact CSV hiện hành từ [OWID Data Catalog]({OWID_COMPACT_CSV_URL}) ([tài liệu OWID]({OWID_COVID_DOCS_URL})); [Kaggle `{KAGGLE_DATASET_HANDLE}`]({KAGGLE_DATASET_URL}) là nguồn dự phòng. Snapshot Kaggle cũ trong project chỉ tới 19/09/2020 và không đủ dữ liệu vaccine. {wiki_note}

## Phương pháp

Lọc dữ liệu quốc gia trong giai đoạn **{self.date_window[0]}–{self.date_window[1]}**; phạm vi quan sát **{self.cleaned['date'].min():%Y-%m-%d}–{self.cleaned['date'].max():%Y-%m-%d}**, gồm **{summary['location'].nunique()}** quốc gia/vùng thuộc {continents}. Giá trị thiếu và số điều chỉnh âm được giữ theo nguồn. Các biểu đồ gồm xu hướng ca mới, heatmap Pearson và phân bố tiêm đủ liều; dashboard hỗ trợ lọc quốc gia/châu lục và xem xu hướng tháng.

## Kết quả và giới hạn

Ca mới trung bình 7 ngày: trung bình **{cases_mean}**, trung vị **{cases_median}** ca/ngày trên dữ liệu quốc gia-ngày. Trung vị tiêm đủ liều cuối kỳ là **{vaccine_median}** trên các nơi có dữ liệu. Phát hiện:

{findings_text}

Số liệu là ca được báo cáo; mức xét nghiệm và cập nhật khác nhau. Tương quan không chứng minh quan hệ nhân quả. {vaccine_note}

## Tệp đầu ra

CSV dữ liệu sạch và bảng tổng hợp, `dashboard_data.json`, `data_quality_audit.csv`, các biểu đồ và trang `dashboard.html`.
"""

    def export_results(self) -> tuple[Path, Path, Path, Path]:
        """Xuất các CSV, JSON, audit và báo cáo sau khi phân tích xong."""
        if self.cleaned is None or self.summary_all is None:
            raise RuntimeError("Run the analysis before exporting results.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cleaned_file = self.output_dir / "cleaned_covid_all_countries.csv"
        summary_file = self.output_dir / "country_summary_all.csv"
        dashboard_file = self.output_dir / "dashboard_data.json"
        report_file = self.output_dir / "summary_report.md"

        self.cleaned.to_csv(cleaned_file, index=False, encoding="utf-8-sig")
        self.summary_all.to_csv(summary_file, index=False, encoding="utf-8-sig")
        selected = self.cleaned["location"].isin(self.visualization_countries)
        self.cleaned.loc[selected].to_csv(self.output_dir / "cleaned_covid_subset.csv", index=False, encoding="utf-8-sig")
        self.summary_all[self.summary_all["location"].isin(self.visualization_countries)].to_csv(
            self.output_dir / "country_summary.csv", index=False, encoding="utf-8-sig"
        )
        self._build_data_quality_audit().to_csv(self.output_dir / "data_quality_audit.csv", index=False, encoding="utf-8-sig")
        dashboard_file.write_text(
            json.dumps(self._build_dashboard_payload(), ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
        report_file.write_text(self._build_summary_report(), encoding="utf-8")
        return cleaned_file, summary_file, dashboard_file, report_file
