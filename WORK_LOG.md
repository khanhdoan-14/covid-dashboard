# Nhật ký công việc — COVID-19 Dashboard

**Dự án:** `PDS301m_Project/outputs/covid_dashboard_vscode`  
**Cập nhật gần nhất:** 29/10/2026  
**Nguồn dữ liệu chính:** OWID COVID compact CSV từ Data Catalog; Kaggle `bolkonsky/covid19` là nguồn dự phòng/tham chiếu.

## Mục tiêu

Rà soát pipeline Python, đối chiếu các CSV đầu ra với CSV Kaggle, giữ đúng ý nghĩa dữ liệu nguồn, điều chỉnh biểu đồ và cập nhật dashboard HTML để chỉ trình bày các chỉ số có dữ liệu thật.

## Nhật ký theo thời gian

### 22/10/2026 — Kết nối nguồn Kaggle và chạy pipeline

- Cập nhật `covid_processor.py` để ưu tiên CSV Kaggle có sẵn, hoặc tải bộ dữ liệu `bolkonsky/covid19` qua KaggleHub khi chưa có bản cục bộ.
- Bổ sung tìm CSV OWID phù hợp trong thư mục dataset và kiểm tra các cột bắt buộc trước khi phân tích.
- Đặt Wikipedia ở vai trò nguồn scraping phụ để tham khảo/đối chiếu; không dùng Wikipedia thay cho nguồn CSV chính.
- Cập nhật `requirements.txt`, `README.md` và notebook để mô tả Kaggle là nguồn chính, cách tải dữ liệu và cách chạy dashboard.
- Bổ sung metadata về nguồn, phạm vi ngày thực tế và tình trạng sẵn có của dữ liệu tiêm chủng trong JSON/báo cáo/dashboard.
- Chạy notebook thành công ở lần này. Kết quả xác nhận snapshot Kaggle có 44.785 dòng nguồn, nhưng chỉ bao phủ đến 19/09/2020 và không có trường tiêm chủng được ghi nhận trong giai đoạn phân tích.

### 26/10/2026 — Rà soát CSV, sửa xử lý dữ liệu và trực quan hóa

- Đối chiếu CSV Kaggle gốc với CSV đã làm sạch, bảng tổng hợp theo quốc gia và JSON dùng bởi HTML.
- Phát hiện `cleaned_covid_subset.csv` và `country_summary.csv` là tệp cũ từ lần chạy trước, chứa dữ liệu đến năm 2023 và không khớp snapshot Kaggle đang sử dụng. Cập nhật lại cả hai tệp từ cùng pipeline hiện tại.
- Sửa làm sạch số ca mới: giữ giá trị thiếu là thiếu, không tự thay bằng 0; giữ cả số âm do nguồn ghi nhận điều chỉnh, không cắt về 0.
- Bổ sung chuẩn hóa/tính bù chỉ số trên một triệu dân khi giá trị nguồn bị thiếu, dựa trên số liệu và dân số tương ứng; không tạo dữ liệu tiêm chủng khi nguồn không có.
- Điều chỉnh biểu đồ notebook:
  - Biểu đồ đường thể hiện ca mới trung bình 7 ngày trên một triệu dân theo thời gian.
  - Heatmap Pearson dùng các chỉ số ca nhiễm, tử vong và ca mới trên một triệu dân; bỏ biến tiêm chủng không có dữ liệu.
  - Histogram thay phân phối tỷ lệ tiêm chủng bằng phân phối ca mới trung bình 7 ngày trên một triệu dân theo quốc gia.
- Điều chỉnh `dashboard.html`:
  - Thay biểu đồ/ô tiêm chủng bằng xếp hạng ca mới và tử vong trên một triệu dân.
  - Chuẩn hóa biểu đồ xu hướng tháng theo một triệu dân để so sánh các quốc gia có quy mô dân số khác nhau.
  - Cập nhật KPI và bảng quốc gia theo các trường có sẵn; hiển thị khoảng thời gian thực tế và thông báo rõ việc thiếu dữ liệu tiêm chủng.
- Cập nhật README, phần mô tả trong notebook và `summary_report.md` cho khớp với cách xử lý mới.
- Thêm `data_quality_audit.csv` để ghi số dòng, phạm vi ngày, khóa trùng, số giá trị thiếu, số điều chỉnh âm, số quan sát tiêm chủng và các phép đối chiếu chính.
- Loại bỏ ảnh histogram tiêm chủng cũ để tránh nhầm với biểu đồ mới.

## Kết quả kiểm tra đối chiếu

- CSV Kaggle gốc: **44.785 dòng**, ngày từ **31/12/2019 đến 19/09/2020**.
- Dữ liệu quốc gia trong kỳ phân tích sau khi loại dòng tổng hợp và lọc ngày: **44.001 dòng**, từ **01/01/2020 đến 19/09/2020**.
- Số quốc gia/vùng lãnh thổ: **209**; số nhóm châu lục sau khi gộp Bắc/Nam Mỹ: **5**.
- Khóa trùng `(iso_code, date)` trong nguồn và dữ liệu sạch: **0**.
- Có **603** giá trị `new_cases` thiếu trong các dòng thuộc phạm vi phân tích; chúng được giữ thiếu.
- Có **17** giá trị `new_cases` âm trong phạm vi phân tích; chúng được giữ như các điều chỉnh của nguồn.
- Đã so sánh từng giá trị `new_cases` giữa nguồn và CSV sạch trong phạm vi ngày: **khớp**.
- Số quốc gia giữa dữ liệu sạch, bảng tổng hợp và JSON dashboard: **khớp 209**.
- CSV subset có **1.315 dòng** cho 5 quốc gia dùng ở biểu đồ; đối chiếu với CSV toàn bộ: **khớp**.
- JSON có **1.591 bản ghi xu hướng tháng**; phạm vi ngày khớp với CSV.
- Dữ liệu tiêm chủng: **0 quan sát** trong snapshot; dashboard không ước tính hoặc trình bày giá trị giả.
- Audit không có dòng trạng thái `REVIEW`; các kiểm tra đối chiếu chính đều `PASS`.

## Tệp đã cập nhật hoặc tạo mới

### Mã nguồn và mô tả

- `covid_processor.py`
- `dashboard.html`
- `covid_dashboard.ipynb`
- `README.md`

### Đầu ra trong `outputs/`

- `cleaned_covid_all_countries.csv`
- `cleaned_covid_subset.csv`
- `country_summary_all.csv`
- `country_summary.csv`
- `dashboard_data.json`
- `data_quality_audit.csv`
- `summary_report.md`
- `chart1_line_new_cases.png`
- `chart2_heatmap_covid_indicators.png`
- `chart3_hist_cases_per_million.png`

## Cách chạy và giới hạn đã biết

- Các tệp đầu ra ngày 26/10/2026 được tạo lại bằng chính `CovidDataProcessor` từ CSV Kaggle đã tải trong cache; bước scraping Wikipedia phụ được bỏ qua trong lần chạy này vì không cần thiết cho các phép phân tích chính.
- Mã notebook đã được cập nhật. Lệnh thực thi notebook qua `nbconvert` không hoàn tất trong phiên làm việc này; vì vậy đầu ra cũ lưu trong các cell notebook đã được xóa để tránh hiển thị số liệu lỗi thời. Các CSV, JSON, báo cáo và ảnh biểu đồ bên ngoài notebook đã được tạo lại thành công bằng pipeline.
- Do snapshot Kaggle chỉ có dữ liệu đến 19/09/2020, dashboard không thể hiển thị các làn sóng sau ngày này hoặc xu hướng tiêm chủng. Muốn phân tích các giai đoạn đó cần một phiên bản dataset có phạm vi ngày và cột dữ liệu tương ứng; không nên suy diễn từ snapshot hiện tại.
- Mở `dashboard.html` bằng Live Server trong VS Code để tải JSON cục bộ và xem các biểu đồ tương tác.

### 29/10/2026 — Chuyển sang OWID compact hiện hành và chạy lại notebook

- Cập nhật nguồn chính sang compact CSV hiện hành từ OWID Data Catalog, nguồn có cả ca nhiễm, tử vong và tiêm chủng trong cùng bảng; Kaggle `bolkonsky/covid19` tiếp tục được giữ làm nguồn dự phòng/tham chiếu. Wikipedia chỉ dùng để scraping đối chiếu tổng số ca/tử vong.
- Tải/cached dữ liệu OWID tại `work/owid_compact_latest.csv` (CSV khoảng 174 MiB; dữ liệu nguồn có 617.667 dòng, từ 01/01/2020 đến 30/08/2026). Phân tích project giữ cửa sổ 01/01/2020–31/12/2023 để cùng phạm vi với các phần đã trình bày.
- Chạy thành công toàn bộ `covid_dashboard.ipynb` bằng kernel `.venv` và `nbconvert`; notebook hiện lưu 11 cell đã chạy cùng kết quả đầu ra.
- Tạo lại các CSV, JSON, báo cáo và biểu đồ từ cùng một lần chạy. Dữ liệu sạch có **343.983 dòng** của **237 quốc gia/vùng lãnh thổ** thuộc 5 châu lục; gồm **217.328** quan sát vaccine và **214** quốc gia/vùng có dữ liệu tiêm chủng.
- Đối chiếu dữ liệu nguồn với kết quả sạch theo quốc gia/ngày: `new_cases` khớp chính xác; mọi giá trị vaccine nguồn có báo cáo đều được giữ; khóa quốc gia-ngày trùng là **0** ở cả nguồn và dữ liệu sạch; các kiểm tra so khớp trong audit đều `PASS`.
- Bổ sung vào `data_quality_audit.csv` phép kiểm tra giá trị `new_cases` và vaccine được bảo toàn; sửa nhãn nguồn kỳ vọng để phản ánh OWID là nguồn chính.
- Khôi phục trực quan hóa vaccine: biểu đồ đường ca mới đã làm mượt, heatmap Pearson gồm chỉ số vaccine, histogram tỷ lệ tiêm đủ liều; dashboard có xếp hạng vaccine và xu hướng tháng riêng cho ca, tử vong, vaccine.
- Báo cáo ghi nhận tương quan Pearson giữa tử vong tích lũy trên một triệu dân và tỷ lệ tiêm đủ liều cuối kỳ là **r=0,16 (n=210)**. Đây là tương quan mô tả ở cấp quốc gia, không chứng minh quan hệ nhân quả. Một quốc gia/vùng có tỷ lệ báo cáo vượt 100%, được ghi rõ là giới hạn mẫu số/ghi nhận của nguồn.
- Scrape Wikipedia thành công và ghép được dữ liệu tham khảo theo tên cho **218** quốc gia; các chỉ số phân tích chính vẫn lấy từ OWID.
- Xóa ảnh histogram ca mới trên một triệu dân cũ để tránh nhầm với biểu đồ vaccine được tạo lại.

## Đầu ra sau lần chạy 29/10/2026

- Nguồn cache: `work/owid_compact_latest.csv`.
- Dữ liệu: `outputs/cleaned_covid_all_countries.csv`, `outputs/cleaned_covid_subset.csv`, `outputs/country_summary_all.csv`, `outputs/country_summary.csv`, `outputs/dashboard_data.json`, `outputs/data_quality_audit.csv`.
- Báo cáo và biểu đồ: `outputs/summary_report.md`, `outputs/chart1_line_new_cases.png`, `outputs/chart2_heatmap_covid_indicators.png`, `outputs/chart3_hist_vaccination_rate.png`.
- Trang tương tác: `dashboard.html`; notebook đã chạy: `covid_dashboard.ipynb`.

### 02/11/2026 — Kiểm tra dashboard trong trình duyệt

- Mở `dashboard.html` qua local HTTP server để trình duyệt tải được `outputs/dashboard_data.json`; xác nhận tiêu đề, nguồn, kỳ phân tích, KPI Vietnam, các biểu đồ canvas, xu hướng vaccine theo tháng và bảng quốc gia được render.
- Thử lọc châu lục: chọn Asia làm danh sách quốc gia và số liệu Afghanistan cập nhật đúng. Thử tìm Japan trong phạm vi đã lọc: KPI/bảng cập nhật sang Japan, giá trị khớp `dashboard_data.json`.
- Phát hiện bộ đếm trạng thái vẫn hiển thị tổng 237 quốc gia / 5 châu lục khi lọc Asia. Sửa `dashboard.html` để đếm số quốc gia và châu lục đang lọc; xác nhận sau sửa hiển thị **50 quốc gia | 1 châu lục** cho Asia.
- Không thấy lỗi tải dữ liệu hoặc lỗi hiển thị quan sát được trong lần kiểm tra giao diện; JavaScript đã qua kiểm tra cú pháp ở lần rà trước. Kiểm tra console DevTools không có sẵn qua tab trình duyệt tích hợp.

### 02/11/2026 — Tinh gọn mã và thêm mô tả hàm

- Tách `export_results()` thành các bước đọc được: tạo audit chất lượng, tạo báo cáo và xuất kết quả; giữ các trường CSV/JSON và cách đối chiếu dữ liệu.
- Gộp logic vẽ ba biểu đồ thanh xếp hạng vào một hàm dùng chung; bỏ helper/mảng màu không được dùng ở JavaScript.
- Bổ sung docstring tiếng Việt cho mọi hàm trong `covid_processor.py` và bốn hàm minh họa trong notebook; thêm comment mô tả các hàm và bộ xử lý sự kiện trong `dashboard.html`.
- Sửa câu thông báo notebook để dùng đúng OWID làm nguồn phân tích khi Wikipedia không khả dụng.
- `py_compile` và kiểm tra cú pháp JavaScript thành công; AST xác nhận 19 hàm Python và 4 hàm notebook đều có docstring. Chạy trực tiếp pipeline thành công trên cache OWID: **343.983 dòng sạch, 237 quốc gia**, audit có **0** trạng thái `REVIEW`.
- Thử chạy lại notebook bằng `nbconvert` nhưng tiến trình kernel không hoàn tất trong thời gian chờ; vì vậy các output cell lưu sẵn chưa được tạo lại theo mã vừa chỉnh. Pipeline trực tiếp đã tạo mới CSV, JSON, biểu đồ và báo cáo.
