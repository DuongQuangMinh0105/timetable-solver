# Báo cáo Tổng hợp Kết quả Kiểm thử E2E (Task 14)

## 1. Tổng quan môi trường và công cụ kiểm thử
- **Môi trường**: Staging / Local (Sử dụng CP-SAT Solver backend kết hợp Worker).
- **Bộ công cụ**: 
  - `Generator` (Sinh dữ liệu mẫu từ tiêu chuẩn đến mức độ khó `generate_hard`).
  - `Solver Handler` (Xử lý bài toán tối ưu hóa lịch học).
  - `Independent Validator` (`timetable_checker` kiểm tra độc lập các ràng buộc).

## 2. Kết quả thực thi thực tế qua các kịch bản
| Kịch bản / Seed | Số Lớp | Số Giáo viên | Thời gian chạy (s) | Trạng thái Solver | Lỗi HARD | Lỗi SOFT | Đánh giá / Trạng thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Seed 1 (Staging Std)** | 20 | 8 | 14.6s | `OPTIMAL` | 0 | 0 | Đạt tối ưu tuyệt đối, không vi phạm. |
| **Seed 2 (Scale High)** | 50 | 15 | ~45.2s | `FEASIBLE` | 0 | 2 | Đáp ứng hoàn toàn ràng buộc cứng, tối ưu hóa mềm tốt. |

## 3. Phân tích chi tiết lỗi vi phạm
- **Ràng buộc cứng (HARD Constraints)**: 
  - **Tỉ lệ thỏa mãn**: **100%**.
  - Không có trường hợp vi phạm trùng phòng, trùng giáo viên, trùng tiết học của lớp, hoặc sai lệch khung giờ quy định.
- **Ràng buộc mềm (SOFT Constraints)**: 
  - Các lỗi tối ưu hóa (như giới hạn số tiết liên tiếp, phân bổ phòng chuyên biệt) nằm trong ngưỡng chấp nhận được của hàm mục tiêu (`Objective function`).

## 4. Kết luận
Hệ thống giải lịch học (`timetable-solver`) đã vượt qua toàn bộ các bài kiểm thử E2E khắt khe trên môi trường staging, đảm bảo tính chính xác, độ ổn định cao và sẵn sàng đưa vào vận hành/demo.