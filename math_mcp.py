import os
import random
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from sympy import Point, Line, Circle as SymCircle
from mcp.server.fastmcp import FastMCP

# Khởi tạo FastMCP Server
mcp = FastMCP("Geometry Solver & Drawer")

# Lưu trữ trạng thái hình vẽ trong phiên làm việc
class GeometrySession:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.points = {}  # Lưu tên điểm: Point object
        self.lines = {}   # Lưu tên đường: Line object
        self.segments = [] # Lưu danh sách các đoạn thẳng cần vẽ: (p1, p2, color, linestyle)
        self.circles = []  # Lưu danh sách đường tròn: (center, radius, label)

# Khởi tạo một session toàn cục
session = GeometrySession()

def _convert_point(p):
    """Hàm phụ trợ chuyển Point SymPy thành tọa độ số thực (x, y)"""
    return float(p.x), float(p.y)

@mcp.tool()
def reset_session() -> str:
    """Xóa toàn bộ hình vẽ cũ để bắt đầu một bài toán hình học mới."""
    session.reset()
    return "Đã làm mới không gian hình học. Bạn có thể bắt đầu bài toán mới."

@mcp.tool()
def create_general_triangle(name_a: str = "A", name_b: str = "B", name_c: str = "C") -> str:
    """
    Tạo một tam giác tổng quát ngẫu nhiên (nhọn, không cân, không vuông) khi đề bài không cho tọa độ.
    Trả về tọa độ giả định của 3 đỉnh.
    """
    B = Point(0, 0)
    c_x = random.uniform(6, 8)
    C = Point(c_x, 0)
    
    a_x = random.uniform(c_x * 0.3, c_x * 0.7)
    a_y = random.uniform(4, 6)
    A = Point(a_x, a_y)
    
    session.points[name_a] = A
    session.points[name_b] = B
    session.points[name_c] = C
    
    # Tự động nối 3 cạnh tam giác
    session.segments.append((A, B, 'b', '-'))
    session.segments.append((B, C, 'b', '-'))
    session.segments.append((C, A, 'b', '-'))
    
    return f"Đã tạo tam giác tổng quát {name_a}{name_b}{name_c}.\nToạ độ giả định: {name_a}({float(A.x):.2f}, {float(A.y):.2f}), {name_b}(0,0), {name_c}({float(C.x):.2f}, 0)"

@mcp.tool()
def add_point(name: str, x: float, y: float) -> str:
    """Định nghĩa một điểm mới khi bài toán cho sẵn tọa độ cụ thể (ví dụ: A(0, 4))."""
    p = Point(x, y)
    session.points[name] = p
    return f"Đã thêm điểm {name}({x}, {y})"

@mcp.tool()
def get_midpoint(p1_name: str, p2_name: str, result_name: str) -> str:
    """Tìm trung điểm của đoạn thẳng nối giữa 2 điểm đã có và đặt tên cho điểm mới."""
    if p1_name not in session.points or p2_name not in session.points:
        return "Lỗi: Một trong hai điểm không tồn tại."
    
    p1 = session.points[p1_name]
    p2 = session.points[p2_name]
    mid = p1.midpoint(p2)
    session.points[result_name] = mid
    return f"Trung điểm của {p1_name}{p2_name} là {result_name} có tọa độ ({float(mid.x):.2f}, {float(mid.y):.2f})"

@mcp.tool()
def create_line_from_points(p1_name: str, p2_name: str, line_name: str) -> str:
    """Tạo một đường thẳng vô hạn đi qua hai điểm đã biết."""
    if p1_name not in session.points or p2_name not in session.points:
        return "Lỗi: Điểm không tồn tại."
    
    l = Line(session.points[p1_name], session.points[p2_name])
    session.lines[line_name] = l
    # Đồng thời thêm đoạn thẳng nối vào danh sách vẽ
    session.segments.append((session.points[p1_name], session.points[p2_name], 'b', '-'))
    return f"Đã tạo đường thẳng {line_name} đi qua {p1_name} và {p2_name}"

@mcp.tool()
def get_perpendicular_projection(point_name: str, p1_line: str, p2_line: str, result_name: str) -> str:
    """
    Hạ đường vuông góc (Đường cao): Tìm hình chiếu vuông góc của một điểm lên đường thẳng đi qua (p1_line, p2_line).
    Nối đoạn vuông góc bằng nét đứt đỏ.
    """
    if point_name not in session.points or p1_line not in session.points or p2_line not in session.points:
        return "Lỗi: Điểm nhập vào không tồn tại."
    
    p = session.points[point_name]
    line = Line(session.points[p1_line], session.points[p2_line])
    
    perp_line = line.perpendicular_line(p)
    h = line.intersection(perp_line)[0]
    
    session.points[result_name] = h
    # Nối đường vuông góc bằng nét đứt màu đỏ
    session.segments.append((p, h, 'r', '--'))
    return f"Hình chiếu vuông góc của {point_name} lên {p1_line}{p2_line} là {result_name}({float(h.x):.2f}, {float(h.y):.2f})"

@mcp.tool()
def draw_geometry_and_save() -> str:
    """
    Tiến hành vẽ toàn bộ các điểm, đường thẳng, đoạn thẳng và đường tròn đã dựng trong session.
    Trả về chuỗi base64 của ảnh hoặc đường dẫn lưu ảnh.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_aspect('equal')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.axhline(y=0, color='k', linewidth=0.8)
    ax.axvline(x=0, color='k', linewidth=0.8)
    
    # 1. Vẽ các đoạn thẳng
    for p1, p2, color, style in session.segments:
        x1, y1 = _convert_point(p1)
        x2, y2 = _convert_point(p2)
        ax.plot([x1, x2], [y1, y2], color=color, linestyle=style, linewidth=1.5)
        
    # 2. Vẽ các điểm và nhãn tên
    for name, point in session.points.items():
        x, y = _convert_point(point)
        ax.plot(x, y, 'ro', markersize=5)
        ax.text(x + 0.1, y + 0.1, name, fontsize=12, fontweight='bold')

    # Tự căn chỉnh góc nhìn
    ax.relim()
    ax.autoscale_view()
    
    # Lưu ảnh ra file cục bộ để người dùng xem trực tiếp
    output_path = os.path.abspath("geometry_output.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return f"Đã dựng hình thành công! Ảnh kết quả hiện tại được lưu tại: {output_path}"

if __name__ == "__main__":
    # Chạy server MCP qua cơ chế Stdio (Chuẩn cấu hình kết nối của Claude/Cursor)
    mcp.run(transport='stdio')