import matplotlib.pyplot as plt
from sympy import Point, Line, Circle as SymCircle
import os

class GeometryEngine:
    def __init__(self):
        self.points = {}  # Lưu trữ điểm: {"A": (x, y), "B": (x, y), ...}

    def reset_session(self):
        self.points.clear()
        return "Đã xóa toàn bộ dữ liệu hình cũ."

    def add_point(self, name, x, y):
        self.points[name] = (float(x), float(y))
        return f"Đã thêm điểm {name}({x}, {y})"

    def get_midpoint(self, p1_name, p2_name, result_name):
        if p1_name not in self.points or p2_name not in self.points:
            return f"Lỗi: Không tìm thấy điểm {p1_name} hoặc {p2_name}"
        x1, y1 = self.points[p1_name]
        x2, y2 = self.points[p2_name]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        self.points[result_name] = (mx, my)
        return f"Đã tính trung điểm {result_name}({mx}, {my}) của {p1_name}{p2_name}"

    def get_perpendicular_projection(self, point_name, p1_line, p2_line, result_name):
        if point_name not in self.points or p1_line not in self.points or p2_line not in self.points:
            return "Lỗi: Thiếu dữ liệu điểm để tính hình chiếu vuông góc."
        
        # Trong bài toán cụ thể này, chân đường cao từ A xuống BC chính là B(0,0)
        # Để tổng quát, ta lấy hình chiếu của điểm lên đường thẳng:
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_line]
        x2, y2 = self.points[p2_line]
        
        if x1 == x2 and y1 == y2:
            return "Lỗi: Hai điểm tạo đường thẳng trùng nhau."
            
        # Vectơ pháp tuyến đường thẳng
        dx, dy = x2 - x1, y2 - y1
        mag2 = dx*dx + dy*dy
        u = ((x0 - x1) * dx + (y0 - y1) * dy) / mag2
        hx = x1 + u * dx
        hy = y1 + u * dy
        
        self.points[result_name] = (hx, hy)
        return f"Đã tìm được chân đường vuông góc {result_name}({hx}, {hy})"

    def draw_geometry_and_save(self):
        if not self.points:
            return "Không có dữ liệu để vẽ."
            
        plt.figure(figsize=(6, 6))
        
        # Lấy tọa độ các điểm để cấu hình trục
        xs = [p[0] for p in self.points.values()]
        ys = [p[1] for p in self.points.values()]
        
        # Vẽ các điểm và nhãn (Label)
        for name, (x, y) in self.points.items():
            plt.plot(x, y, 'ro' if name in ['A','B','C'] else 'bo') # Đỉnh màu đỏ, điểm phụ màu xanh
            plt.text(x + 0.2, y + 0.2, f"{name}({x:g}, {y:g})", fontsize=12, fontweight='bold')
        
        # Tự động nối các đỉnh của tam giác nếu có đủ ABC
        if all(k in self.points for k in ['A', 'B', 'C']):
            A, B, C = self.points['A'], self.points['B'], self.points['C']
            plt.plot([A[0], B[0], C[0], A[0]], [A[1], B[1], C[1], A[1]], 'g-', linewidth=2)
            
        # Nối thêm đoạn AM nếu có điểm M
        if 'A' in self.points and 'M' in self.points:
            plt.plot([self.points['A'][0], self.points['M'][0]], [self.points['A'][1], self.points['M'][1]], 'k--')

        plt.xlim(min(xs) - 1, max(xs) + 2)
        plt.ylim(min(ys) - 1, max(ys) + 2)
        plt.axhline(0, color='black',linewidth=0.5)
        plt.axvline(0, color='black',linewidth=0.5)
        plt.grid(True, linestyle=':')
        plt.title("Hình vẽ hình học tự động sinh bởi AI Agent")
        
        filename = "geometry_plot.png"
        plt.savefig(filename, dpi=300)
        plt.close()
        return f"Đã lưu hình ảnh thành công vào file: {os.path.abspath(filename)}"