# Giám sát staging

## Cảnh báo hiện có
| Sự cố | Cách phát hiện |
|---|---|
| Deploy lỗi | Render gửi email (mục Notifications đã bật cho deploy lỗi) |
| Staging hỏng (`/health`, `/solve`, job, lịch) | Workflow `Smoke test staging` chạy mỗi 6 giờ trên GitHub Actions; thất bại thì GitHub gửi thông báo |
| Job lỗi lẻ tẻ | Chưa có cảnh báo riêng, kiểm tra bằng log hoặc truy vấn bên dưới |

Để nhận thông báo, bật mục **Actions** trong GitHub, Settings, Notifications. Chạy tay: tab Actions,
**Smoke test staging**, **Run workflow**.

## Truy vấn log (Render, dịch vụ `timetable-solver`, tab Logs)
- `Failed to process job` hoặc `Traceback`: job lỗi.
- `finished with status`: kết quả từng job.
- `Worker started`: worker được chạy cho một job. Các dòng `GET /health` là Render tự kiểm tra.

## Truy vấn trong Neon (SQL Editor)
```sql
select status, count(*) from jobs group by status;
select id, status from jobs where status = 'failed' order by id desc limit 10;
select column_name from information_schema.columns where table_name = 'jobs';
```
Câu cuối liệt kê các cột của bảng `jobs`. Nếu có cột lưu lý do lỗi (từ migration
`add_job_error_message`), thêm cột đó vào câu thứ hai.

## Dịch vụ ngủ (scale-to-zero)
- Render gói free ngủ sau 15 phút không có truy cập. Đo bằng smoke test: `/health` sau khi ngủ mất
  32,7 giây (lần khác 42,8 giây). Trước buổi demo hãy gọi `/health` trước vài phút.
- Neon cũng tạm dừng compute khi không dùng, nên truy vấn đầu tiên có thể chậm thêm vài giây.

## Tài nguyên và chi phí
- Một job với bài toán mẫu: khoảng 46 giây (khoảng 18 giây khởi động worker, khoảng 18 giây giải).
- Bộ nhớ và CPU trên Render: chưa đo được, vì trang Metrics của gói free không cho xem (nhóm
  thử và thấy yêu cầu nâng cấp). Ước tính từ lần đo trên máy phát triển (không phải trên Render):
  API khoảng 41 MB, worker mỗi job đỉnh khoảng 160 MB với 1 luồng, tổng dưới 512 MB. Dấu hiệu
  nghi hết bộ nhớ: job kẹt `RUNNING` hoặc dịch vụ khởi động lại bất thường trong log.
- Neon: hạn mức gói free là 100 giờ compute và 0,5 GB mỗi project. Chưa theo dõi mức dùng thực tế.
- Chi phí: Render $0 (gói free), Neon $0 (gói free). Smoke test mỗi 6 giờ dùng khoảng vài phút
  Actions mỗi lần, kiểm tra hạn mức ở GitHub, Settings, Billing.