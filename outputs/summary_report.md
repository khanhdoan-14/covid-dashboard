# Báo cáo mini: Phân tích dữ liệu COVID-19

## Mục tiêu và nguồn dữ liệu

Nguồn chính là compact CSV hiện hành từ [OWID Data Catalog](https://catalog.ourworldindata.org/garden/covid/latest/compact/compact.csv) ([tài liệu OWID](https://docs.owid.io/projects/etl/api/covid/)); [Kaggle `bolkonsky/covid19`](https://www.kaggle.com/datasets/bolkonsky/covid19) là nguồn dự phòng. Snapshot Kaggle cũ trong project chỉ tới 19/09/2020 và không đủ dữ liệu vaccine. Không có dữ liệu Wikipedia; phân tích vẫn dùng OWID.

## Phương pháp

Lọc dữ liệu quốc gia trong giai đoạn **2020-01-01–2023-12-31**; phạm vi quan sát **2020-01-01–2023-12-31**, gồm **237** quốc gia/vùng thuộc Africa, America, Asia, Europe, Oceania. Giá trị thiếu và số điều chỉnh âm được giữ theo nguồn. Các biểu đồ gồm xu hướng ca mới, heatmap Pearson và phân bố tiêm đủ liều; dashboard hỗ trợ lọc quốc gia/châu lục và xem xu hướng tháng.

## Kết quả và giới hạn

Ca mới trung bình 7 ngày: trung bình **2,291.79**, trung vị **15.29** ca/ngày trên dữ liệu quốc gia-ngày. Trung vị tiêm đủ liều cuối kỳ là **62.6%** trên các nơi có dữ liệu. Phát hiện:

- United States có tổng ca nhiễm ghi nhận cao nhất (103,436,829).
- Peru có tử vong trên một triệu dân cao nhất (6,587.4).
- Gibraltar có tỷ lệ tiêm đủ liều cuối kỳ cao nhất (110.2%).
- Tương quan Pearson giữa tử vong tích lũy trên một triệu dân và tiêm đủ liều là 0.16 (n=210; không suy ra quan hệ nhân quả).

Số liệu là ca được báo cáo; mức xét nghiệm và cập nhật khác nhau. Tương quan không chứng minh quan hệ nhân quả. Có 1 quốc gia/vùng ghi nhận trên 100%; có thể do mẫu số dân số hoặc cách báo cáo.

## Tệp đầu ra

CSV dữ liệu sạch và bảng tổng hợp, `dashboard_data.json`, `data_quality_audit.csv`, các biểu đồ và trang `dashboard.html`.
