# Báo cáo E2E (seed=0, units=blocks)

| Profile | Unit | Trạng thái | Giây | Mục tiêu | Solver (room/sat/g316) | reference_cost | Vi phạm cứng | Kết luận |
|---|---|---|---|---|---|---|---|---|
| small | 15 | OPTIMAL | 0.5 | 0 | room=0, sat=0, g316=0 | room=0, sat=0, g316=0 | - | OK |
| spec | 40 | OPTIMAL | 1.7 | 0 | room=0, sat=0, g316=0 | room=0, sat=0, g316=0 | - | OK |
| many_mba | 34 | FEASIBLE | 30.1 | 10 | room=0, sat=10, g316=0 | room=0, sat=10, g316=0 | - | OK |
| many_art | 37 | OPTIMAL | 0.6 | 0 | room=0, sat=0, g316=0 | room=0, sat=0, g316=0 | - | OK |
| tight_teachers | 40 | OPTIMAL | 1.8 | 0 | room=0, sat=0, g316=0 | room=0, sat=0, g316=0 | - | OK |
| overload_mba | 20 | UNKNOWN | 30.1 | - | - | - | - | KHÁC DỰ KIẾN |

## Chi tiết các lần chạy có vấn đề

### overload_mba: KHÁC DỰ KIẾN
