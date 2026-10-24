# Giải thích mô hình xếp thời khóa biểu (cho báo cáo và demo)

## 1. Bài toán
Xếp các môn học của nhiều lớp vào lưới thời gian (ngày x tiết) và phòng học sao cho không ai bị
xếp hai nơi cùng lúc, đồng thời lịch "đẹp" nhất có thể. Đây là bài toán thỏa ràng buộc kèm tối ưu.
Chúng tôi dùng **CP-SAT** (OR-Tools): bộ giải mô tả bài toán bằng các biến nhị phân và ràng buộc,
rồi tự tìm lời giải, và có thể **chứng minh** một lịch là tối ưu hoặc không tồn tại.

## 2. Biến quyết định
Mỗi môn cần học được tách thành các **ca học** (một ca là một khối 1 hoặc 2 tiết liên tiếp,
ví dụ môn 3 tiết thành khối 2 và khối 1). Với mỗi ca `u`, ngày `d`, tiết bắt đầu `p` và phòng `r`
có một biến `s[u,d,p,r]` bằng 1 nếu ca đó bắt đầu ở đó. Ô nào bị cấm ngay từ đầu (phòng sai loại,
phòng nhỏ hơn sĩ số, tiết ngoài khung) thì không có biến, nên mô hình nhỏ hơn.

## 3. Ràng buộc cứng (bắt buộc đúng)
| Ràng buộc | Ý nghĩa |
|---|---|
| Mỗi ca học đúng một lần | Mỗi ca có đúng một ô bắt đầu (ngày, tiết, phòng) |
| Phòng không trùng giờ | Một phòng, một tiết chỉ có một ca |
| Giáo viên không trùng giờ | Một giáo viên không dạy hai nơi cùng lúc |
| Lớp không trùng giờ | Một lớp không học hai môn cùng lúc |
| Tối đa 2 tiết liên tiếp | Một lớp không học liền quá 2 tiết (tính cả tiết bị chiếm) |
| Loại phòng và sức chứa | Lớp MBA chỉ vào phòng MBA (G316), môn vẽ vào phòng vẽ (G313), phòng phải đủ chỗ |
| Tiết cho phép | Chỉ dùng tiết 1 đến 6 (7 và 8 bị cấm) |

Chi tiết từng encoder: `docs/encoders.md`, `docs/constraints.md`.

## 4. Ràng buộc mềm và hàm mục tiêu
Lịch hợp lệ có thể có nhiều, ta chọn lịch **ít điểm phạt nhất**:

| Mục | Trọng số | Ý nghĩa |
|---|---|---|
| Ổn định phòng | 5 | Một môn nên dùng một phòng cố định, mỗi phòng thừa bị phạt |
| Tránh thứ Bảy | 10 | Mỗi ca xếp vào thứ Bảy bị phạt |
| Để dành G316 | 2 | Môn không phải MBA mà dùng G316 thì bị phạt |

Hàm mục tiêu = tổng (trọng số x số lần vi phạm). Điểm 0 nghĩa là lịch hoàn hảo. Trọng số chọn qua
benchmark, xem `docs/reports/solver_params.md`.

## 5. Kiểm tra độc lập
Sau khi giải, `check_timetable` kiểm tra lại các ràng buộc cứng **không dùng CP-SAT**. Nếu mô hình
có lỗi, lịch sai bị phát hiện và job báo thất bại thay vì trả lịch sai.

## 6. Khi không có lịch: chẩn đoán vô nghiệm
Dữ liệu sai thì bộ giải trả "vô nghiệm". Hệ thống giải thích lý do bằng tiếng Việt (xem
`docs/diagnosis.md`):
1. **Kiểm tra nhanh trước khi giải:** đếm sức chứa (giáo viên, phòng, lớp). Ví dụ giáo viên T1 được
   giao 33 tiết nhưng chỉ có 30 ô trong tuần: báo ngay, không cần chạy solver.
2. **Lõi vô nghiệm của CP-SAT:** mỗi nhóm ràng buộc gắn một "công tắc"; solver chỉ ra tập công
   tắc nhỏ nhất đủ gây mâu thuẫn, ta dịch thành câu dễ hiểu.

Ví dụ thực tế (`docs/samples/`): thiếu phòng MBA, giáo viên quá tải, thiếu phòng, tiết ép ngoài
khoảng 1 đến 6 (báo lỗi ngay lúc đọc file).

## 7. Hiệu năng và giới hạn
- 30 lớp: tối ưu trong khoảng 13 s với 2 luồng.
- 50 lớp: có lịch hợp lệ trong 60 s nhưng chưa chứng minh tối ưu (FEASIBLE).
- Bài toán thuộc lớp NP-khó, nên lớp lớn hơn cần nhiều CPU hơn hoặc chia nhỏ bài toán.
- Chưa mô hình hóa: giờ bận của giáo viên (`unavailable_slots`) và ép môn vào ô cố định
  (`fixed_day`, `fixed_period`) trong file Excel mẫu; hai cột này bị bỏ qua và được cảnh báo.

## 8. Câu hỏi thường gặp khi bảo vệ
- **Vì sao CP-SAT chứ không heuristic hay thuật toán di truyền?** CP-SAT cho đảm bảo đúng ràng
  buộc cứng và có thể chứng minh tối ưu hoặc vô nghiệm; heuristic không đảm bảo.
- **Sao kết quả mỗi lần chạy hơi khác nhau?** Bộ giải chạy nhiều luồng và có yếu tố ngẫu nhiên;
  cùng seed và 1 luồng thì lặp lại được.
- **Làm sao biết lịch đúng?** Có bộ kiểm tra độc lập chạy sau mỗi lần giải, và hơn 350 test tự động.
