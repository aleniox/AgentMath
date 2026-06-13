import matplotlib.pyplot as plt
from sympy import Point, Line, Circle as SymCircle

from tools import GeometrySolver
# 1. Khởi tạo bộ giải
solver = GeometrySolver()

# 2. Định nghĩa các điểm đỉnh (Dùng Point của SymPy)
A = Point(0, 4)
B = Point(0, 0)
# Lưu ý: C(6, 0) tạo thành tam giác vuông tại B
C = Point(6, 0)

# 3. Vẽ các điểm và các cạnh tam giác
solver.draw_point(A, "A")
solver.draw_point(B, "B")
solver.draw_point(C, "C")

solver.draw_segment(A, B)
solver.draw_segment(B, C)
solver.draw_segment(C, A)

# 4. Tìm và vẽ trung điểm M của BC
M = solver.get_midpoint(B, C, "M")
print(f"Tọa độ trung điểm M: {M}")

# 5. Tạo đường thẳng BC để hạ đường cao từ A
line_BC = Line(B, C)
H = solver.get_perpendicular_projection(A, line_BC, "H")
print(f"Tọa độ hình chiếu vuông góc H (chân đường cao): {H}")

# Vẽ đường cao AH (vẽ nét đứt '---' màu đỏ 'r')
solver.draw_segment(A, H, color='r', linestyle='--')

# 6. Xuất hình ảnh
solver.render(title="Giai bai toan hinh hoc tam giac ABC")