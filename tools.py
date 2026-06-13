import matplotlib.pyplot as plt
import numpy as np
import random
import os

class GeometryEngine:
    def __init__(self):
        self.points = {}      # {"A": (x, y), "B": (x, y), ...}
        self.segments = []    # [("A", "B", "color", "linestyle"), ...]
        self.circles = []     # [("O", radius, "color", "linestyle"), ...]
        self.midpoints = []   # [("A", "M", "B"), ...]

    def reset_session(self):
        """Xóa toàn bộ dữ liệu để bắt đầu bài toán mới."""
        self.points.clear()
        self.segments.clear()
        self.circles.clear()
        self.midpoints.clear()
        if hasattr(self, 'r'): delattr(self, 'r')
        return "Đã làm sạch hệ thống. Sẵn sàng cho bài toán mới."

    def _check_points_exist(self, *names):
        missing = [name for name in names if name not in self.points]
        if missing:
            return f"Lỗi: Không tìm thấy điểm {', '.join(missing)} trong hệ thống. Hãy dựng các điểm này trước."
        return None

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

    def create_circle_with_diameter(self, center_name="O", radius=5,
                                     horizontal_p1=None, horizontal_p2=None,
                                     vertical_p1=None, vertical_p2=None):
        """Tạo đường tròn tâm center_name bán kính R. Tùy chọn tạo 1 hoặc 2 đường kính vuông góc.
        - horizontal_p1, horizontal_p2: hai đầu mút của đường kính thứ nhất (nằm ngang)
        - vertical_p1, vertical_p2: hai đầu mút của đường kính thứ hai (nằm dọc)
        """
        self.points[center_name] = (0.0, 0.0)
        self.r = float(radius)
        self.circles.append((center_name, self.r, 'b', '-'))
        
        if horizontal_p1 and horizontal_p2:
            self.points[horizontal_p1] = (-self.r, 0.0)
            self.points[horizontal_p2] = (self.r, 0.0)
            self.add_segment(horizontal_p1, horizontal_p2, 'k', '-')
            
        if vertical_p1:
            self.points[vertical_p1] = (0.0, self.r)
        if vertical_p2:
            self.points[vertical_p2] = (0.0, -self.r)
        if vertical_p1 and vertical_p2:
            self.add_segment(vertical_p1, vertical_p2, 'k', '-')
            
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
        self.midpoints.append((p1_name, result_name, p2_name))
        return f"Đã dựng trung điểm {result_name} của {p1_name}{p2_name}."

    def get_line_line_intersection(self, p1_l1, p2_l1, p1_l2, p2_l2, result_name):
        """Tìm giao điểm của 2 đường thẳng và tự động nối các nét vẽ kéo dài đến giao điểm."""
        self.add_segment(p1_l1, p2_l1, color='k', linestyle='-')
        self.add_segment(p1_l2, p2_l2, color='k', linestyle='-')
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
        
        # Tự động kéo dài đoạn thẳng gốc đến giao điểm (để đường vẽ không bị đứt quãng)
        dist1_1 = np.hypot(x1 - px, y1 - py)
        dist1_2 = np.hypot(x2 - px, y2 - py)
        far1 = p1_l1 if dist1_1 > dist1_2 else p2_l1
        
        dist2_1 = np.hypot(x3 - px, y3 - py)
        dist2_2 = np.hypot(x4 - px, y4 - py)
        far2 = p1_l2 if dist2_1 > dist2_2 else p2_l2
        
        self.add_segment(far1, result_name, color='k', linestyle='-')
        self.add_segment(far2, result_name, color='k', linestyle='-')
        return f"Đã tìm thấy giao điểm {result_name} tại ({px:.2f}, {py:.2f})."

    def get_line_circle_intersection(self, p1_line, p2_line, center_name, result_name1, result_name2=None, exclude_point=None):
        """Tìm các giao điểm của đường thẳng (đi qua p1_line, p2_line) với đường tròn tâm center_name.
        - result_name1: Tên điểm gán cho giao điểm thứ nhất.
        - result_name2: Tên điểm gán cho giao điểm thứ hai (nếu có).
        - exclude_point: Nếu được cung cấp, giao điểm nào trùng hoặc gần điểm này nhất sẽ bị loại bỏ, và giao điểm còn lại sẽ được gán cho result_name1.
        """
        self.add_segment(p1_line, p2_line, color='k', linestyle='-')
        if any(p not in self.points for p in [p1_line, p2_line, center_name]):
            return "Lỗi: Thiếu dữ liệu điểm."
        
        # Tìm bán kính đường tròn
        r = None
        for c_name, radius, _, _ in self.circles:
            if c_name == center_name:
                r = radius
                break
        if r is None:
            r = getattr(self, 'r', None)
        if r is None:
            return f"Lỗi: Chưa xác định được bán kính của đường tròn tâm {center_name}."
            
        x1, y1 = self.points[p1_line]
        x2, y2 = self.points[p2_line]
        cx, cy = self.points[center_name]
        
        dx, dy = x2 - x1, y2 - y1
        a = dx*dx + dy*dy
        if a < 1e-6:
            return "Lỗi: Hai điểm của đường thẳng trùng nhau."
            
        b = 2 * (dx*(x1 - cx) + dy*(y1 - cy))
        c = (x1 - cx)**2 + (y1 - cy)**2 - r*r
        
        disc = b*b - 4*a*c
        if disc < -1e-6:
            return f"Lỗi: Đường thẳng {p1_line}{p2_line} không cắt đường tròn tâm {center_name}."
        if disc < 0:
            disc = 0.0
            
        t1 = (-b + np.sqrt(disc)) / (2*a)
        t2 = (-b - np.sqrt(disc)) / (2*a)
        
        pt1 = (x1 + t1*dx, y1 + t1*dy)
        pt2 = (x1 + t2*dx, y1 + t2*dy)
        
        # Nếu có exclude_point, lọc bỏ điểm trùng/gần nó nhất
        if exclude_point and exclude_point in self.points:
            ex, ey = self.points[exclude_point]
            d1 = np.hypot(pt1[0] - ex, pt1[1] - ey)
            d2 = np.hypot(pt2[0] - ex, pt2[1] - ey)
            if d1 > d2:
                self.points[result_name1] = pt1
                if result_name2:
                    self.points[result_name2] = pt2
            else:
                self.points[result_name1] = pt2
                if result_name2:
                    self.points[result_name2] = pt1
        else:
            self.points[result_name1] = pt1
            if result_name2:
                self.points[result_name2] = pt2
                
        # Tự động vẽ các đoạn thẳng nối dài đến giao điểm để hiển thị hình vẽ hoàn chỉnh
        # Tìm điểm xa nhất trong p1_line, p2_line so với giao điểm mới vẽ để kéo dài
        for res_name in [result_name1, result_name2]:
            if res_name and res_name in self.points:
                px, py = self.points[res_name]
                dist1 = np.hypot(x1 - px, y1 - py)
                dist2 = np.hypot(x2 - px, y2 - py)
                far = p1_line if dist1 > dist2 else p2_line
                self.add_segment(far, res_name, color='k', linestyle='-')
                
        msg = f"Đã dựng giao điểm của đường thẳng {p1_line}{p2_line} với đường tròn tâm {center_name}: {result_name1}"
        if result_name2:
            msg += f" và {result_name2}"
        return msg

    def get_perpendicular_projection(self, point_name, p1_line, p2_line, result_name):
        """Hạ đường vuông góc từ một điểm xuống một đường thẳng (Tìm chân đường cao)."""
        err = self._check_points_exist(point_name, p1_line, p2_line)
        if err: return err
        
        self.add_segment(p1_line, p2_line, color='k', linestyle='-')
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_line]
        x2, y2 = self.points[p2_line]
        
        dx, dy = x2 - x1, y2 - y1
        mag2 = dx*dx + dy*dy
        if mag2 < 1e-6:
            return f"Lỗi: Đường thẳng không hợp lệ. Hai điểm {p1_line} và {p2_line} có tọa độ trùng nhau tại ({x1:g}, {y1:g}). Không thể xác định đường thẳng."
        
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

    def add_circle(self, center_name, radius, color='b', linestyle='-'):
        """Tạo/Thêm đường tròn tâm center_name.
        - radius: có thể là một số thực (bán kính cụ thể) hoặc tên của một điểm đã có (khi đó bán kính là khoảng cách từ center_name đến điểm đó).
        """
        if center_name not in self.points:
            return f"Lỗi: Không tìm thấy tâm {center_name}"
        
        if isinstance(radius, str):
            if radius not in self.points:
                return f"Lỗi: Không tìm thấy điểm {radius} để tính bán kính."
            cx, cy = self.points[center_name]
            rx, ry = self.points[radius]
            r_val = float(np.hypot(rx - cx, ry - cy))
        else:
            r_val = float(radius)
            
        self.circles.append((center_name, r_val, color, linestyle))
        if center_name == "O" or not hasattr(self, 'r'):
            self.r = r_val
        return f"Đã tạo đường tròn tâm {center_name} bán kính R={r_val:.4f}."

    def get_circle_circle_intersection(self, center1_name, center2_name, result_name1, result_name2=None, exclude_point=None):
        """Tìm giao điểm của hai đường tròn tâm center1_name và center2_name.
        - exclude_point: Nếu được cung cấp, giao điểm nào trùng hoặc gần điểm này nhất sẽ bị loại bỏ, và giao điểm còn lại sẽ được gán cho result_name1.
        """
        if center1_name not in self.points or center2_name not in self.points:
            return "Lỗi: Thiếu dữ liệu điểm tâm."
            
        r1, r2 = None, None
        for c_name, r, _, _ in self.circles:
            if c_name == center1_name: r1 = r
            if c_name == center2_name: r2 = r
        if r1 is None or r2 is None:
            return "Lỗi: Không tìm thấy bán kính của các đường tròn."
            
        x1, y1 = self.points[center1_name]
        x2, y2 = self.points[center2_name]
        d = np.hypot(x2 - x1, y2 - y1)
        
        if d > r1 + r2 + 1e-6 or d < abs(r1 - r2) - 1e-6 or d < 1e-6:
            return "Lỗi: Hai đường tròn không giao nhau."
            
        a = (r1**2 - r2**2 + d**2) / (2*d)
        h = np.sqrt(max(0.0, r1**2 - a**2))
        
        x_mid = x1 + (a/d)*(x2 - x1)
        y_mid = y1 + (a/d)*(y2 - y1)
        
        rx = -(y2 - y1)/d
        ry = (x2 - x1)/d
        
        pt1 = (x_mid + h*rx, y_mid + h*ry)
        pt2 = (x_mid - h*rx, y_mid - h*ry)
        
        if exclude_point and exclude_point in self.points:
            ex, ey = self.points[exclude_point]
            d1 = np.hypot(pt1[0] - ex, pt1[1] - ey)
            d2 = np.hypot(pt2[0] - ex, pt2[1] - ey)
            if d1 > d2:
                self.points[result_name1] = pt1
                if result_name2: self.points[result_name2] = pt2
            else:
                self.points[result_name1] = pt2
                if result_name2: self.points[result_name2] = pt1
        else:
            self.points[result_name1] = pt1
            if result_name2:
                self.points[result_name2] = pt2
                
        return f"Đã dựng giao điểm của 2 đường tròn: {result_name1}" + (f" và {result_name2}" if result_name2 else "")

    def get_tangents_from_external_point(self, external_point_name, center_name, tangent_point_name1, tangent_point_name2=None):
        """Tìm các tiếp điểm và vẽ các đường tiếp tuyến từ external_point_name đến đường tròn tâm center_name."""
        if external_point_name not in self.points or center_name not in self.points:
            return "Lỗi: Thiếu dữ liệu điểm."
            
        r_val = None
        for c_name, r, _, _ in self.circles:
            if c_name == center_name:
                r_val = r
                break
        if r_val is None:
            r_val = getattr(self, 'r', None)
        if r_val is None:
            return "Lỗi: Không tìm thấy bán kính đường tròn."
            
        x1, y1 = self.points[external_point_name]
        xc, yc = self.points[center_name]
        d = np.hypot(xc - x1, yc - y1)
        
        if d < r_val - 1e-6:
            return (f"Lỗi: Điểm {external_point_name} nằm TRONG đường tròn (khoảng cách đến tâm = {d:.4f} < bán kính R = {r_val:.4f}). "
                    f"Không thể vẽ tiếp tuyến. Hãy dùng `add_point` để di chuyển {external_point_name} ra xa tâm hơn, "
                    f"hoặc kiểm tra lại tọa độ. Gợi ý: dùng `get_distance('{external_point_name}', '{center_name}')` để kiểm tra.")
            
        L = np.sqrt(max(0.0, d**2 - r_val**2))
        
        a = (r_val**2 - L**2 + d**2) / (2*d)
        h = np.sqrt(max(0.0, r_val**2 - a**2))
        
        x_mid = xc + (a/d)*(x1 - xc)
        y_mid = yc + (a/d)*(y1 - yc)
        
        rx = -(y1 - yc)/d
        ry = (x1 - xc)/d
        
        pt1 = (x_mid + h*rx, y_mid + h*ry)
        pt2 = (x_mid - h*rx, y_mid - h*ry)
        
        self.points[tangent_point_name1] = pt1
        self.add_segment(external_point_name, tangent_point_name1, color='k', linestyle='-')
        
        if tangent_point_name2:
            self.points[tangent_point_name2] = pt2
            self.add_segment(external_point_name, tangent_point_name2, color='k', linestyle='-')
            
        return f"Đã dựng các tiếp tuyến từ {external_point_name} đến {center_name} với các tiếp điểm {tangent_point_name1}" + (f", {tangent_point_name2}" if tangent_point_name2 else "")

    def add_tangent_line_at_point(self, center_name, point_on_circle, result_name, length=5.0):
        """Dựng tiếp tuyến tại điểm point_on_circle thuộc đường tròn tâm center_name.
        Tạo thêm một điểm mới result_name nằm trên tiếp tuyến cách point_on_circle một đoạn = length để xác định hướng vẽ.
        """
        if center_name not in self.points or point_on_circle not in self.points:
            return "Lỗi: Thiếu dữ liệu điểm."
            
        xc, yc = self.points[center_name]
        xp, yp = self.points[point_on_circle]
        
        dx, dy = xp - xc, yp - yc
        r = np.hypot(dx, dy)
        if r < 1e-6:
            return "Lỗi: Điểm trùng với tâm đường tròn."
            
        tx = -dy / r
        ty = dx / r
        
        self.points[result_name] = (xp + tx * length, yp + ty * length)
        self.add_segment(point_on_circle, result_name, color='k', linestyle='-')
        return f"Đã dựng tiếp tuyến tại {point_on_circle} và tạo điểm {result_name} cách nó {length:g}."

    def get_angle_bisector_intersection(self, p_angle, p_left, p_right, p1_line, p2_line, result_name):
        """Dựng đường phân giác trong của góc p_left - p_angle - p_right, cắt đường thẳng p1_line-p2_line tại result_name."""
        self.add_segment(p_angle, p_left, color='k', linestyle='-')
        self.add_segment(p_angle, p_right, color='k', linestyle='-')
        self.add_segment(p1_line, p2_line, color='k', linestyle='-')
        if any(p not in self.points for p in [p_angle, p_left, p_right, p1_line, p2_line]):
            return "Lỗi: Thiếu dữ liệu điểm."
            
        xa, ya = self.points[p_angle]
        xb, yb = self.points[p_left]
        xc, yc = self.points[p_right]
        
        dab = np.hypot(xb - xa, yb - ya)
        dac = np.hypot(xc - xa, yc - ya)
        
        if dab < 1e-6 or dac < 1e-6:
            return "Lỗi: Điểm trùng nhau không xác định được góc."
            
        ux, uy = (xb - xa)/dab, (yb - ya)/dab
        vx, vy = (xc - xa)/dac, (yc - ya)/dac
        
        wx, wy = ux + vx, uy + vy
        mag_w = np.hypot(wx, wy)
        if mag_w < 1e-6:
            wx, wy = -uy, ux
        else:
            wx, wy = wx/mag_w, wy/mag_w
            
        x_bis = xa + wx
        y_bis = ya + wy
        
        self.points["_bis_temp"] = (x_bis, y_bis)
        res = self.get_line_line_intersection(p_angle, "_bis_temp", p1_line, p2_line, result_name)
        if "_bis_temp" in self.points:
            del self.points["_bis_temp"]
        
        self.add_segment(p_angle, result_name, color='m', linestyle='-.')
        return f"Đã dựng đường phân giác góc {p_left}{p_angle}{p_right} cắt {p1_line}{p2_line} tại {result_name}."

    def add_circumcircle(self, p1_name, p2_name, p3_name, center_name, color='g', linestyle='--'):
        """Dựng đường tròn ngoại tiếp đi qua 3 điểm p1_name, p2_name, p3_name.
        Tạo điểm tâm mới đặt tên là center_name và tự động vẽ đường tròn ngoại tiếp này dưới dạng nét đứt.
        Nếu tâm tính được trùng với tọa độ của một điểm đã có, sẽ dùng lại điểm đó.
        """
        if any(p not in self.points for p in [p1_name, p2_name, p3_name]):
            return "Lỗi: Thiếu dữ liệu điểm để dựng đường tròn ngoại tiếp."
            
        x1, y1 = self.points[p1_name]
        x2, y2 = self.points[p2_name]
        x3, y3 = self.points[p3_name]
        
        A1 = 2 * (x2 - x1)
        B1 = 2 * (y2 - y1)
        C1 = x2**2 + y2**2 - (x1**2 + y1**2)
        
        A2 = 2 * (x3 - x1)
        B2 = 2 * (y3 - y1)
        C2 = x3**2 + y3**2 - (x1**2 + y1**2)
        
        den = A1 * B2 - B1 * A2
        if abs(den) < 1e-6:
            return "Lỗi: 3 điểm thẳng hàng, không thể dựng đường tròn ngoại tiếp."
            
        cx = (C1 * B2 - B1 * C2) / den
        cy = (A1 * C2 - C1 * A2) / den
        
        # Kiểm tra xem tọa độ đã có điểm nào chưa
        existing = None
        for name, (px, py) in self.points.items():
            if abs(px - cx) < 1e-9 and abs(py - cy) < 1e-9:
                existing = name
                break
        
        if existing:
            actual_name = existing
            if existing != center_name:
                actual_name = center_name
                self.points[actual_name] = (float(cx), float(cy))
        else:
            self.points[center_name] = (float(cx), float(cy))
            actual_name = center_name
        
        r_val = float(np.hypot(x1 - cx, y1 - cy))
        self.circles.append((actual_name, r_val, color, linestyle))
        
        msg = f"Đã dựng đường tròn ngoại tiếp đi qua {p1_name}, {p2_name}, {p3_name} với tâm {actual_name}"
        if existing:
            msg += f" (tọa độ trùng với {existing}, dùng lại)"
        msg += f" và bán kính R={r_val:.4f}."
        return msg

    def get_perpendicular_line_point(self, point_name, p1_ref, p2_ref, result_name, distance=2.0):
        """Tạo điểm mới result_name nằm trên đường thẳng vuông góc với p1_ref-p2_ref và đi qua point_name.
        Dùng add_segment(point_name, result_name) sau đó để vẽ đường vuông góc."""
        if any(p not in self.points for p in [point_name, p1_ref, p2_ref]):
            return "Lỗi: Thiếu dữ liệu điểm."
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_ref]
        x2, y2 = self.points[p2_ref]
        dx, dy = x2 - x1, y2 - y1
        mag = np.hypot(dx, dy)
        if mag < 1e-6:
            return "Lỗi: Đoạn tham chiếu không hợp lệ."
        # Vectơ pháp tuyến (vuông góc)
        nx, ny = -dy / mag, dx / mag
        self.points[result_name] = (x0 + nx * distance, y0 + ny * distance)
        self.add_segment(point_name, result_name, color='m', linestyle='-')
        return f"Đã tạo điểm {result_name} trên đường vuông góc với {p1_ref}{p2_ref} qua {point_name}."

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
        err = self._check_points_exist(point_name, p1_line, p2_line)
        if err: return err
        
        self.add_segment(p1_line, p2_line, color='k', linestyle='-')
        x0, y0 = self.points[point_name]
        x1, y1 = self.points[p1_line]
        x2, y2 = self.points[p2_line]
        dx, dy = x2 - x1, y2 - y1
        mag2 = dx*dx + dy*dy
        if mag2 < 1e-6:
            return f"Lỗi: Đường thẳng không hợp lệ. Hai điểm {p1_line} và {p2_line} có tọa độ trùng nhau tại ({x1:g}, {y1:g}). Không thể xác định đường thẳng."
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
        
        from matplotlib.patches import Polygon, Circle
        
        # Thiết lập cấu hình đồ họa độ phân giải cao
        fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
        
        current_r = getattr(self, 'r', 5.0)
        offset = current_r * 0.05  # Khoảng cách chữ động tránh đè lên điểm chấm
        
        # 1. Hơi lọc điểm: Phân biệt điểm chính (visible) và điểm phụ trợ
        import re
        def is_visible_point(name):
            if name.startswith('_'):
                return False
            # Nếu tên chứa ký tự viết thường (ví dụ: 'alt', 'tangent', 'temp'), đó là điểm phụ trợ
            if any(c.islower() for c in name):
                return False
            return True
            
        visible_points = {name: coord for name, coord in self.points.items() if is_visible_point(name)}
        
        # 2. Định nghĩa Palette màu cao cấp
        COLOR_MAP = {
            'b': '#4a69bd',      # Slate Blue
            'g': '#10ac84',      # Emerald Green
            'k': '#2d3436',      # Charcoal/Dark Gray
            'r': '#ee5253',      # Coral Red
            'm': '#8854d0',      # Soft Purple
            'c': '#0a3d62',      # Navy Blue / Dark Teal
            'y': '#f39c12',      # Amber Orange
        }
        
        def get_color(c):
            return COLOR_MAP.get(c, c)
            
        # 3. Vẽ các đường tròn
        for center_name, radius, color, style in self.circles:
            if center_name in self.points:
                cx, cy = self.points[center_name]
                circle_art = Circle((cx, cy), radius, color=get_color(color), fill=False, linestyle=style, linewidth=1.2)
                ax.add_patch(circle_art)
                
        # 4. Gom nhóm và vẽ các đoạn thẳng (chỉ vẽ nối giữa các điểm)
        drawn_connections = set()
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
                ax.plot([x1, x2], [y1, y2], color=get_color(color), linestyle=style, linewidth=1.2)
                if is_visible_point(p1_name) and is_visible_point(p2_name):
                    drawn_connections.add(tuple(sorted((p1_name, p2_name))))
                
        # 5. Tự động tìm các góc vuông và vẽ biểu tượng góc vuông (Right-angle indicators)
        for B_name, (bx, by) in visible_points.items():
            neighbors = []
            for p1, p2 in drawn_connections:
                if p1 == B_name:
                    neighbors.append(p2)
                elif p2 == B_name:
                    neighbors.append(p1)
            
            for i in range(len(neighbors)):
                for j in range(i + 1, len(neighbors)):
                    A_name, C_name = neighbors[i], neighbors[j]
                    ax_coord, ay_coord = visible_points[A_name]
                    cx_coord, cy_coord = visible_points[C_name]
                    
                    # Vector BA và BC
                    ux, uy = ax_coord - bx, ay_coord - by
                    vx, vy = cx_coord - bx, cy_coord - by
                    
                    mag_u = np.hypot(ux, uy)
                    mag_v = np.hypot(vx, vy)
                    if mag_u < 1e-5 or mag_v < 1e-5:
                        continue
                        
                    cos_theta = (ux*vx + uy*vy) / (mag_u * mag_v)
                    if abs(cos_theta) < 1e-3: # Gần vuông góc
                        s = current_r * 0.035
                        ux_unit, uy_unit = ux / mag_u, uy / mag_u
                        vx_unit, vy_unit = vx / mag_v, vy / mag_v
                        
                        p0 = (bx, by)
                        p1 = (bx + s * ux_unit, by + s * uy_unit)
                        p2 = (bx + s * (ux_unit + vx_unit), by + s * (uy_unit + vy_unit))
                        p3 = (bx + s * vx_unit, by + s * vy_unit)
                        
                        rect = Polygon([p0, p1, p2, p3], closed=True, 
                                       facecolor='#dcdde1', edgecolor='#7f8c8d', 
                                       alpha=0.6, linewidth=0.8, zorder=2)
                        ax.add_patch(rect)
                        
        # 6. Vẽ ký hiệu bằng nhau trên các trung đoạn (Midpoint ticks)
        if hasattr(self, 'midpoints'):
            for A_name, M_name, B_name in self.midpoints:
                if A_name in visible_points and M_name in visible_points and B_name in visible_points:
                    coords = [visible_points[A_name], visible_points[M_name], visible_points[B_name]]
                    for X, Y in [(coords[0], coords[1]), (coords[1], coords[2])]:
                        mid_pt = ((X[0] + Y[0]) / 2, (X[1] + Y[1]) / 2)
                        dx, dy = Y[0] - X[0], Y[1] - X[1]
                        len_d = np.hypot(dx, dy)
                        if len_d > 1e-5:
                            px, py = -dy / len_d, dx / len_d
                            h = current_r * 0.025
                            ax.plot([mid_pt[0] - px*h/2, mid_pt[0] + px*h/2],
                                    [mid_pt[1] - py*h/2, mid_pt[1] + py*h/2],
                                    color='#57606f', linewidth=1.0, zorder=4)

        # 7. Vẽ các điểm (Nodes)
        for name, (x, y) in visible_points.items():
            ax.plot(x, y, marker='o', markerfacecolor='#ff4757', markeredgecolor='#c0392b', 
                    markeredgewidth=0.8, markersize=4.5, zorder=5)

        # 8. Đặt vị trí nhãn (Labels) thông minh tránh đè chữ
        for name, (x, y) in visible_points.items():
            connected_dirs = []
            
            # 8a. Đặt vị trí nhãn cho tâm O chéo dưới bên phải để tránh đè các đường kính vuông góc
            if name == 'O':
                dir_x, dir_y = 0.7, -0.7
            else:
                # 8b. Kiểm tra nếu điểm nằm trên đường tròn nào đó, ưu tiên đẩy nhãn ra phía ngoài đường tròn
                on_circle_boundary = False
                radial_dx, radial_dy = 0.0, 0.0
                for center_name, radius, _, _ in self.circles:
                    if center_name in self.points:
                        cx, cy = self.points[center_name]
                        dist_to_c = np.hypot(x - cx, y - cy)
                        if abs(dist_to_c - radius) < 1e-2:
                            on_circle_boundary = True
                            radial_dx += (x - cx) / dist_to_c
                            radial_dy += (y - cy) / dist_to_c
                
                if on_circle_boundary:
                    mag_r = np.hypot(radial_dx, radial_dy)
                    if mag_r > 1e-5:
                        dir_x, dir_y = radial_dx / mag_r, radial_dy / mag_r
                    else:
                        dir_x, dir_y = 1.0, 1.0
                else:
                    for p1, p2 in drawn_connections:
                        other = None
                        if p1 == name:
                            other = p2
                        elif p2 == name:
                            other = p1
                        if other and other in visible_points:
                            ox, oy = visible_points[other]
                            ux, uy = ox - x, oy - y
                            len_u = np.hypot(ux, uy)
                            if len_u > 1e-5:
                                connected_dirs.append((ux / len_u, uy / len_u))
                    
                    if connected_dirs:
                        sum_dx = sum(d[0] for d in connected_dirs)
                        sum_dy = sum(d[1] for d in connected_dirs)
                        mag_s = np.hypot(sum_dx, sum_dy)
                        if mag_s > 1e-5:
                            dir_x, dir_y = -sum_dx / mag_s, -sum_dy / mag_s
                        else:
                            dir_x, dir_y = 0.7, -0.7
                    else:
                        dir_x, dir_y = 0.7, 0.7
            
            text_x = x + dir_x * offset
            text_y = y + dir_y * offset
            
            ha = 'center'
            if dir_x > 0.35:
                ha = 'left'
            elif dir_x < -0.35:
                ha = 'right'
                
            va = 'center'
            if dir_y > 0.35:
                va = 'bottom'
            elif dir_y < -0.35:
                va = 'top'
                
            ax.text(text_x, text_y, name, fontsize=12, fontfamily='serif', fontstyle='italic', 
                    color='#2c3e50', fontweight='semibold',
                    horizontalalignment=ha, verticalalignment=va, zorder=6)

        # 9. Tự động điều chỉnh Viewport
        xs = [p[0] for p in visible_points.values()]
        ys = [p[1] for p in visible_points.values()]
        for center_name, radius, _, _ in self.circles:
            if center_name in self.points:
                cx, cy = self.points[center_name]
                xs.extend([cx - radius, cx + radius])
                ys.extend([cy - radius, cy + radius])
                
        all_coords = xs + ys
        if all_coords:
            max_val = max(abs(coord) for coord in all_coords)
            limit_val = max_val * 1.15
        else:
            limit_val = current_r * 1.5
            
        ax.set_xlim(-limit_val, limit_val)
        ax.set_ylim(-limit_val, limit_val)
        
        ax.set_aspect('equal', adjustable='box')
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return f"Thành công! Hình vẽ hình học trực quan đã được xuất ra file: {os.path.abspath(filename)}"
    
    def get_perpendicular_line_intersection(self, point_pass, p1_perp, p2_perp, p1_line2, p2_line2, result_name):
        """Kẻ đường thẳng qua point_pass vuông góc với p1_perp-p2_perp và cắt p1_line2-p2_line2 tại result_name."""
        self.add_segment(p1_perp, p2_perp, color='k', linestyle='-')
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