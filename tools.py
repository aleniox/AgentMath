import matplotlib.pyplot as plt
import numpy as np
import random
import os

class GeometryEngine:
    def __init__(self):
        self.points = {}      # {"A": (x, y), "B": (x, y), ...}
        self.segments = []    # [("A", "B", "color", "linestyle"), ...]
        self.circles = []     # [("O", radius, "color", "linestyle"), ...]

    def reset_session(self):
        """Xóa toàn bộ dữ liệu để bắt đầu bài toán mới."""
        self.points.clear()
        self.segments.clear()
        self.circles.clear()
        if hasattr(self, 'r'): delattr(self, 'r')
        return "Đã làm sạch hệ thống. Sẵn sàng cho bài toán mới."

    # ==========================================
    # NHÓM 1: KHỞI TẠO NỀN MÓNG (THỰC THỂ GỐC)
    # ==========================================
    
    def add_point(self, name, x, y):
        """Thêm một điểm cụ thể khi biết tọa độ."""
        self.points[name] = (float(x), float(y))
        return f"Đã thêm điểm {name}({x:g}, {y:g})"

    def create_general_triangle(self, name_a="A", name_b="B", name_c="C"):
        """Tạo một tam giác nhọn tổng quát ngẫu nhiên, tránh các trường hợp đặc biệt."""
        c_x = random.uniform(7, 10)
        a_x = random.uniform(c_x * 0.3, c_x * 0.7)
        a_y = random.uniform(5, 8)
        
        self.points[name_b] = (0.0, 0.0)
        self.points[name_c] = (c_x, 0.0)
        self.points[name_a] = (a_x, a_y)
        
        self.add_segment(name_a, name_b, color='g', linestyle='-')
        self.add_segment(name_b, name_c, color='g', linestyle='-')
        self.add_segment(name_c, name_a, color='g', linestyle='-')
        return f"Đã tạo tam giác tổng quát {name_a}{name_b}{name_c}."

    def add_point_on_circle_arc(self, name, center_name, angle_deg):
        """Lấy một điểm nằm trên đường tròn theo góc lượng giác (độ)."""
        if center_name not in self.points:
            return f"Lỗi: Không tìm thấy tâm {center_name}"
        r = getattr(self, 'r', None)
        if r is None:
            return "Lỗi: Chưa khởi tạo bán kính đường tròn. Hãy gọi create_circle_with_diameter trước."
        ox, oy = self.points[center_name]
        alpha = np.radians(float(angle_deg))
        x = ox + r * np.cos(alpha)
        y = oy + r * np.sin(alpha)
        self.points[name] = (x, y)
        return f"Đã lấy điểm {name} trên đường tròn với góc {angle_deg}°."

    # ĐỔI TÊN HÀM NÀY:
    def create_circle_with_diameter(self, center_name="O", radius=5,
                                     point_diameter_1=None, point_diameter_2=None,
                                     point_diameter_3=None, point_diameter_4=None):
        """Tạo đường tròn tâm O bán kính R. Tùy chọn tạo 1 hoặc 2 đường kính vuông góc.
        - p1-p2: đường kính thứ nhất (nằm ngang)
        - p3-p4: đường kính thứ hai vuông góc (nằm dọc)
        """
        self.points[center_name] = (0.0, 0.0)
        self.r = float(radius)
        self.circles.append((center_name, self.r, 'b', '-'))
        
        if point_diameter_1 and point_diameter_2:
            self.points[point_diameter_1] = (-self.r, 0.0)
            self.points[point_diameter_2] = (self.r, 0.0)
            self.add_segment(point_diameter_1, point_diameter_2, 'k', '-')
            
        if point_diameter_3 and point_diameter_4:
            self.points[point_diameter_3] = (0.0, self.r)
            self.points[point_diameter_4] = (0.0, -self.r)
            self.add_segment(point_diameter_3, point_diameter_4, 'k', '-')
            
        return f"Đã tạo đường tròn tâm {center_name} bán kính R={radius}."

    # ==========================================
    # NHÓM 2: CÁC PHÉP TOÁN ĐẠI SỐ HÌNH HỌC (TÍNH TOÁN)
    # ==========================================

    def add_segment(self, p1_name, p2_name, color='k', linestyle='-'):
        """Nối đoạn thẳng giữa 2 điểm."""
        if p1_name in self.points and p2_name in self.points:
            self.segments.append((p1_name, p2_name, color, linestyle))
            return f"Đã nối đoạn {p1_name}{p2_name}."
        return f"Lỗi: Không tìm thấy điểm để nối."

    def get_midpoint(self, p1_name, p2_name, result_name):
        """Tìm trung điểm của đoạn thẳng."""
        x1, y1 = self.points[p1_name]
        x2, y2 = self.points[p2_name]
        self.points[result_name] = ((x1 + x2) / 2, (y1 + y2) / 2)
        return f"Đã dựng trung điểm {result_name} của {p1_name}{p2_name}."

    def get_line_line_intersection(self, p1_l1, p2_l1, p1_l2, p2_l2, result_name):
        """Tìm giao điểm của 2 đường thẳng và tự động nối các nét vẽ hệ quả."""
        x1, y1 = self.points[p1_l1]
        x2, y2 = self.points[p2_l1]
        x3, y3 = self.points[p1_l2]
        x4, y4 = self.points[p2_l2]
        
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-6:
            return f"Lỗi: Hai đường thẳng {p1_l1}{p2_l1} và {p1_l2}{p2_l2} song song hoặc trùng nhau."
            
        px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / den
        py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / den
        self.points[result_name] = (px, py)
        
        # TỰ ĐỘNG NỐI TOÀN BỘ 2 ĐƯỜNG THẲNG (nét đứt) để user thấy rõ
        self.add_segment(p1_l1, p2_l1, color='b', linestyle=':')
        self.add_segment(p1_l2, p2_l2, color='b', linestyle=':')
        return f"Đã tìm thấy giao điểm {result_name} tại ({px:.2f}, {py:.2f})."

    def get_perpendicular_projection(self, point_name, p1_line, p2_line, result_name):
        """Hạ đường vuông góc từ một điểm xuống một đường thẳng (Tìm chân đường cao)."""
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_line]
        x2, y2 = self.points[p2_line]
        
        dx, dy = x2 - x1, y2 - y1
        mag2 = dx*dx + dy*dy
        if mag2 < 1e-6: return "Lỗi: Đường thẳng không hợp lệ."
        
        u = ((x0 - x1) * dx + (y0 - y1) * dy) / mag2
        hx = x1 + u * dx
        hy = y1 + u * dy
        self.points[result_name] = (hx, hy)
        self.add_segment(point_name, result_name, color='r', linestyle='--')
        return f"Đã hạ đường vuông góc từ {point_name} xuống {p1_line}{p2_line} tại {result_name}."

    def get_parallel_line_point(self, point_name, p1_ref, p2_ref, distance, result_name):
        """Tạo một điểm tạo với point_name thành đường thẳng song song với p1_ref-p2_ref."""
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_ref]
        x2, y2 = self.points[p2_ref]
        
        dx, dy = x2 - x1, y2 - y1
        length = np.hypot(dx, dy)
        # Tạo điểm mới tịnh tiến theo vecto chỉ phương của đường thẳng tham chiếu
        nx = x0 + (dx / length) * distance
        ny = y0 + (dy / length) * distance
        self.points[result_name] = (nx, ny)
        self.add_segment(point_name, result_name, color='m', linestyle=':')
        return f"Đã dựng đường thẳng qua {point_name} song song với {p1_ref}{p2_ref}."

    # ==========================================
    # NHÓM 3: CÔNG CỤ PHỤ TRỢ & KIỂM TRA
    # ==========================================

    def final_answer(self, answer):
        """Kết thúc bài toán, output lời giải text (chứng minh, tính toán, kết luận)."""
        return f"LỜI GIẢI:\n{answer}"

    def get_distance(self, p1_name, p2_name):
        """Tính khoảng cách Euclid giữa 2 điểm."""
        x1, y1 = self.points[p1_name]
        x2, y2 = self.points[p2_name]
        d = np.hypot(x2 - x1, y2 - y1)
        return f"Khoảng cách {p1_name}{p2_name} = {d:.4f}"

    def check_collinear(self, p1_name, p2_name, p3_name):
        """Kiểm tra 3 điểm có thẳng hàng không (diện tích tam giác ≈ 0)."""
        x1, y1 = self.points[p1_name]
        x2, y2 = self.points[p2_name]
        x3, y3 = self.points[p3_name]
        area = abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2
        if area < 1e-9:
            return f"{p1_name}, {p2_name}, {p3_name} thẳng hàng."
        return f"{p1_name}, {p2_name}, {p3_name} KHÔNG thẳng hàng (diện tích={area:.6f})."

    def reflect_point_over_line(self, point_name, p1_line, p2_line, result_name):
        """Tìm điểm đối xứng của một điểm qua một đường thẳng."""
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_line]
        x2, y2 = self.points[p2_line]
        dx, dy = x2 - x1, y2 - y1
        mag2 = dx*dx + dy*dy
        if mag2 < 1e-6:
            return "Lỗi: Đường thẳng không hợp lệ."
        u = ((x0 - x1) * dx + (y0 - y1) * dy) / mag2
        hx = x1 + u * dx
        hy = y1 + u * dy
        self.points[result_name] = (2*hx - x0, 2*hy - y0)
        self.add_segment(point_name, result_name, color='c', linestyle=':')
        return f"Đã dựng điểm {result_name} đối xứng với {point_name} qua {p1_line}{p2_line}."

    # ==========================================
    # NHÓM 4: KẾT XUẤT ĐỒ HỌA (RENDER)
    # ==========================================
    def draw_geometry_and_save(self, filename="geometry_output.png"):
        """Kết xuất toàn bộ hình vẽ (điểm, đoạn thẳng, đường tròn) thành file ảnh PNG."""
        if not self.points: 
            return "Không có dữ liệu vẽ hình."
        
        # Thiết lập cấu hình đồ họa độ phân giải cao
        fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
        
        # 1. Lấy bán kính hiện tại để tính toán tỉ lệ hiển thị nhãn (Label)
        current_r = getattr(self, 'r', 5.0)
        offset = current_r * 0.04  # Khoảng cách chữ động tránh đè lên điểm chấm
        
        # 2. Vẽ tất cả các đường tròn có trong bộ nhớ
        for center_name, radius, color, style in self.circles:
            cx, cy = self.points[center_name]
            circle_art = plt.Circle((cx, cy), radius, color=color, fill=False, linestyle=style, linewidth=1.8)
            ax.add_patch(circle_art)
            
        # 3. Vẽ tất cả các đoạn thẳng đã đăng ký (loại bỏ trùng lặp)
        seen_pairs = set()
        unique_segments = []
        for seg in self.segments:
            p1, p2 = seg[0], seg[1]
            key = tuple(sorted((p1, p2)))
            if key not in seen_pairs:
                seen_pairs.add(key)
                unique_segments.append(seg)
        for p1_name, p2_name, color, style in unique_segments:
            if p1_name in self.points and p2_name in self.points:
                x1, y1 = self.points[p1_name]
                x2, y2 = self.points[p2_name]
                ax.plot([x1, x2], [y1, y2], color=color, linestyle=style, linewidth=1.5)
            
        # 4. Vẽ các điểm (Nodes) và Gắn nhãn thông minh (Labels)
        # Gom nhóm các điểm chính để ưu tiên hiển thị màu nổi bật
        main_vertices = ['A', 'B', 'C', 'D', 'O', 'M']
        
        for name, (x, y) in self.points.items():
            # Điểm gốc/Đỉnh chính màu đỏ, các giao điểm hệ quả màu xanh nước biển
            point_color = 'ro' if name in main_vertices else 'bo'
            ax.plot(x, y, point_color, markersize=6, zorder=5)
            
            # Tự động căn vị trí nhãn dựa trên vị trí điểm để tránh đè nét vẽ (Kỹ thuật tránh đè chữ)
            text_x, text_y = x + offset, y + offset
            if x < 0: text_x = x - offset * 2.5  # Nếu nằm bên trái trục Oy, đẩy chữ sang trái
            if y < 0: text_y = y - offset * 2.0  # Nếu nằm dưới trục Ox, đẩy chữ xuống dưới
                
            ax.text(text_x, text_y, name, fontsize=13, fontweight='bold', 
                    color='darkred' if name in main_vertices else 'darkblue',
                    zorder=6)
            
        # 5. Cấu hình giới hạn khung trục (Viewport) tự động co giãn theo thực thể xa nhất
        xs = [p[0] for p in self.points.values()]
        ys = [p[1] for p in self.points.values()]
        all_coords = xs + ys + [current_r, -current_r]
        
        max_val = max(abs(coord) for coord in all_coords)
        limit_val = max_val * 1.25  # Chừa 25% rìa ngoài để không bị mất chữ Label
        
        ax.set_xlim(-limit_val, limit_val)
        ax.set_ylim(-limit_val, limit_val)
        
        # Giữ tỉ lệ 1:1 tuyệt đối để đường tròn luôn tròn, không bao giờ bị méo elip
        ax.set_aspect('equal', adjustable='box')
        
        # Ẩn các vạch số thô kệch của hệ trục tọa độ giải tích để giống hình vẽ Sách giáo khoa
        ax.axis('off') 
        
        # Tự động tối ưu bố cục không gian vẽ trước khi lưu file
        plt.tight_layout()
        
        # Lưu hình ảnh chất lượng cao
        plt.savefig(filename, dpi=300, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return f"Thành công! Hình vẽ hình học trực quan đã được xuất ra file: {os.path.abspath(filename)}"
    
    def get_perpendicular_line_intersection(self, point_pass, p1_perp, p2_perp, p1_line2, p2_line2, result_name):
        """Kẻ đường thẳng qua point_pass vuông góc với p1_perp-p2_perp và cắt p1_line2-p2_line2 tại result_name."""
        if any(p not in self.points for p in [point_pass, p1_perp, p2_perp, p1_line2, p2_line2]):
            return "Lỗi: Thiếu dữ liệu điểm để tính toán."
            
        x0, y0 = self.points[point_pass]
        x1, y1 = self.points[p1_perp]
        x2, y2 = self.points[p2_perp]
        
        dx, dy = x2 - x1, y2 - y1
        if np.hypot(dx, dy) < 1e-6: return "Lỗi: Đoạn vuông góc không hợp lệ."
        
        A1, B1 = dx, dy
        C1 = dx * x0 + dy * y0
        
        xa, ya = self.points[p1_line2]
        xb, yb = self.points[p2_line2]
        
        A2 = yb - ya
        B2 = xa - xb
        C2 = A2 * xa + B2 * ya
        
        den = A1 * B2 - B1 * A2
        if abs(den) < 1e-6:
            return "Lỗi: Không tìm thấy giao điểm (Đường thẳng song song)."
            
        ex = (C1 * B2 - B1 * C2) / den
        ey = (A1 * C2 - C1 * A2) / den
        
        self.points[result_name] = (ex, ey)
        self.add_segment(point_pass, result_name, color='m', linestyle='-')
        self.add_segment(p1_line2, p2_line2, color='b', linestyle=':')
        return f"Đã dựng đường vuông góc qua {point_pass} cắt {p1_line2}{p2_line2} tại {result_name}."