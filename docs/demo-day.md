# Demo: chuẩn bị, kịch bản và phương án dự phòng

Demo giao diện Streamlit. Phương án chính chạy backend trên máy local (giải nhanh, không phụ thuộc
mạng). Staging trên Render dùng làm minh chứng đã triển khai. Kịch bản gọi API riêng: `docs/demo-api.md`.

Số đo tham khảo với bài toán mẫu 25 ca học: local khoảng 8 giây, Render khoảng 46 đến 49 giây (gồm
khoảng 20 giây khởi động worker). Dịch vụ Render ngủ sau 15 phút, thức dậy mất khoảng 30 đến 45 giây.

## Trước ngày demo (làm trước 1 đến 2 ngày)
- [ ] Build sẵn image: `docker compose build` (lần đầu mất khoảng 13 phút nếu mạng chậm). Build xong thì
      chạy local không cần Internet.
- [ ] Chạy thử toàn bộ quy trình "Trước giờ demo" bên dưới, ghi lại thời gian giải với file demo.
- [ ] Chọn file Excel demo: `<<FILE_MAU>>` (giải được) và `<<FILE_LOI>>` (vô nghiệm, để minh họa chẩn đoán).
      Tránh dữ liệu 30 tiết/tuần/lớp (vô nghiệm) và bộ 50 lớp (chỉ ra FEASIBLE), xem `docs/known-issues.md`.
- [ ] Xuất sẵn file Excel kết quả và chụp ảnh các tab lịch, làm phương án cuối khi mọi thứ hỏng.
- [ ] Chuẩn bị mạng dự phòng (điện thoại phát 4G), sạc đầy pin, tắt cập nhật Windows tự khởi động lại.
- [ ] Tắt thông báo và đóng các cửa sổ có thông tin nhạy cảm. Không để `API_KEY` hiện trên màn hình
      chiếu (dùng `Read-Host -AsSecureString`, xem bên dưới).

## Trước giờ demo (15 phút)
**Local**
1. Mở Docker Desktop, chờ **Engine running**.
2. Đặt khóa (chỉ dùng trên máy này) rồi chạy:
   ```powershell
   $env:API_KEY = "khoa-demo-local"
   docker compose up -d
   docker compose ps -a
   ```
   Mong đợi: `migrate` Exited (0); `postgres`, `redis` healthy; `api`, `worker` Up.
3. Kiểm tra: `uv run python scripts/smoke_test.py http://localhost:8000` phải ra `SMOKE TEST OK`.
4. Mở giao diện, giữ nguyên cửa sổ đó (cùng cửa sổ đã đặt `API_KEY`):
   ```powershell
   uv run streamlit run src/timetable/interfaces/ui/app.py
   ```
   Vào `http://localhost:8501`, chạy thử một lần với `<<FILE_MAU>>`.

**Render (nếu cần trình bày staging)**
1. Đánh thức và kiểm tra: đặt `$base` và `API_KEY` của Render (nhập bằng `-AsSecureString`) rồi
   `uv run python scripts/smoke_test.py $base`.
2. Muốn giao diện trỏ tới Render thay vì local, chạy Streamlit trong một cửa sổ riêng:
   ```powershell
   $env:<<BIEN_URL>> = "https://timetable-solver-spsk.onrender.com"
   $secure = Read-Host "Dán API_KEY của Render" -AsSecureString
   $env:API_KEY = [System.Net.NetworkCredential]::new("", $secure).Password
   uv run streamlit run src/timetable/interfaces/ui/app.py
   ```
   Chạy trước một job để dịch vụ đã nóng (job đầu mất cả phút).

## Kịch bản (khoảng 6 đến 7 phút)
1. **Bài toán (30 giây):** xếp thời khóa biểu theo ràng buộc cứng (không trùng giáo viên, lớp, phòng)
   và ràng buộc mềm (tránh thứ Bảy, giữ một phòng cho mỗi môn, để dành phòng MBA).
2. **Nhập dữ liệu (1 phút):** tải `<<FILE_MAU>>` lên giao diện, nói ngắn về nội dung file.
3. **Giải (1 phút):** bấm giải, chờ khoảng 8 giây, mở tab tổng quan: trạng thái `OPTIMAL`, điểm phạt.
4. **Xem lịch (1,5 phút):** lần lượt tab lịch theo lớp, giáo viên, phòng.
5. **Xuất kết quả (30 giây):** tải file Excel kết quả.
6. **Đề vô nghiệm (1,5 phút):** tải `<<FILE_LOI>>`, giải, cho xem phần chẩn đoán chỉ ra nhóm ràng buộc
   gây xung đột.
7. **Hạ tầng (1 phút):** API + worker + Redis + PostgreSQL; CI tự kiểm tra rồi Render tự deploy; smoke test
   chạy sau mỗi lần deploy và mỗi 6 giờ (`docs/monitoring.md`); khóa API và bí mật nằm ngoài repo
   (`docs/security.md`).

## Nếu có sự cố
| Triệu chứng | Cách xử lý nhanh |
|---|---|
| Docker báo không kết nối được | Mở Docker Desktop, chờ Engine running rồi chạy lại. Quá 3 phút: dùng Render hoặc ảnh dự phòng |
| `docker compose` báo `Set API_KEY` | Đặt lại `$env:API_KEY = "khoa-demo-local"` trong cùng cửa sổ |
| Giao diện báo lỗi kết nối hoặc 401 | Kiểm tra `curl.exe http://localhost:8000/health`; `API_KEY` trong cửa sổ Streamlit phải trùng với lúc chạy `docker compose up` |
| Job chạy quá lâu hoặc kẹt | `docker compose logs worker --tail 30`; thử `docker compose restart worker` rồi gửi lại |
| Render chậm hoặc lỗi | Chuyển sang local. Đừng chờ Render thức dậy trước mặt khán giả |
| Mất mạng | Local chạy được không cần mạng (nếu đã build). Render thì không |
| Mọi thứ hỏng | Dùng ảnh chụp và file Excel kết quả đã chuẩn bị sẵn |

## Sau demo
`docker compose down` (giữ dữ liệu) hoặc `docker compose down -v` (xóa cả dữ liệu).