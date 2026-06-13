import asyncio
import os
import re
import json
from urllib.parse import urlparse

from dotenv import load_dotenv
import requests
from tools import GeometryEngine
load_dotenv()

LLM_API = os.getenv("LLM_API_URL", "http://10.0.99.116:8070/v1/chat/completions")
engine = GeometryEngine()

def call_llm(system: str, user: str) -> tuple[str | None, dict]:
    payload = {
        "model": "", "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], "stream": False,
        "options": {"temperature": 0.0, "top_p": 0.95, "top_k": 64, "num_ctx": 40000},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    resp = requests.post(LLM_API, json=payload, stream=False, timeout=120)
    if resp.status_code != 200:
        return None, {}
    data = resp.json()
    print(data.get("usage", data))
    return data["choices"][0]["message"]["content"], data.get("usage", {})



def extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    return json.loads(text.strip())


def main(query: str, context: str):
    MAX_STEPS = 100
    done = False
    history = ""

    system_prompt = """Bạn là chuyên gia Toán Hình Học, có khả năng phân tích đề bài và điều khiển các công cụ để tính toán tọa độ và dựng hình chính xác.

<tools>
reset_session: Xóa sạch dữ liệu cũ để bắt đầu bài toán mới. Không có tham số.
add_point: Thêm một điểm cụ thể khi biết rõ tọa độ thực tế (x, y). Input: name (str), x (float), y (float).
create_general_triangle: Khởi tạo một tam giác nhọn thường ngẫu nhiên để làm nền móng khi đề bài không cho số liệu/tọa độ cụ thể. Input: name_a (str), name_b (str), name_c (str).
create_circle_with_diameter: Khởi tạo đường tròn tâm O và tự động dựng trục đường kính đi qua 2 điểm đối xứng. Input: center_name (str), radius (float), point_diameter_1 (str), point_diameter_2 (str).
add_point_on_circle_arc: Lấy một điểm di động nằm trên cung tròn dựa theo góc lượng giác từ 0 đến 360 độ. Input: name (str), center_name (str), angle_deg (float).
add_segment: Kẻ đoạn thẳng nối trực tiếp nét giữa hai điểm đã được dựng sẵn trong hệ thống. Input: p1_name (str), p2_name (str).
get_midpoint: Tính toán và dựng tọa độ trung điểm của đoạn thẳng nối 2 điểm cho trước. Input: p1_name (str), p2_name (str), result_name (str).
get_line_line_intersection: Tìm tọa độ giao điểm của hai đường thẳng tổng quát (Đường 1 đi qua cặp điểm p1_l1, p2_l1 và Đường 2 đi qua cặp điểm p1_l2, p2_l2). Input: p1_l1 (str), p2_l1 (str), p1_l2 (str), p2_l2 (str), result_name (str).
get_perpendicular_projection: Hạ hình chiếu vuông góc từ một điểm xuống một đường thẳng đi qua 2 điểm cho trước (Tìm chân đường cao). Input: point_name (str), p1_line (str), p2_line (str), result_name (str).
get_perpendicular_line_intersection: Kẻ đường thẳng đi qua một điểm, vuông góc với một đoạn thẳng cho trước, rồi tìm ngay giao điểm của nó với một đường thẳng thứ hai. (Rất mạnh cho các bài toán dựng điểm nâng cao). Input: point_pass (str), p1_perp (str), p2_perp (str), p1_line2 (str), p2_line2 (str), result_name (str).
get_parallel_line_point: Dựng một điểm mới phối hợp với điểm cho trước tạo thành đường thẳng song song với một đường thẳng tham chiếu. Input: point_name (str), p1_ref (str), p2_ref (str), distance (float), result_name (str).
draw_geometry_and_save: Kết xuất toàn bộ tọa độ điểm, các nét vẽ đoạn thẳng, đường tròn thành file ảnh đồ họa PNG hoàn chỉnh. Không có tham số.
error_missing_tool: Công cụ phản hồi hệ thống (Feedback Critical). Chỉ gọi khi phân tích câu hỏi thấy xuất hiện tác vụ hình học bắt buộc nhưng hệ thống chưa lập trình công cụ tính toán tương ứng (Ví dụ: Vẽ tiếp tuyến, phân giác...). Khi gọi tool này, hệ thống sẽ dừng an toàn để bổ sung tính năng. Input: required_task (str).
</tools>

<rules>
- Mỗi lần bước (Step) chỉ được gọi duy nhất MỘT tool.
- Luôn gọi tool `reset_session` ở bước đầu tiên (Step 1) để đảm bảo không bị lẫn dữ liệu cũ.
- Đối với bài toán chứng minh KHÔNG CÓ TỌA ĐỘ: Bắt buộc dùng `create_general_triangle` để tự động gán tọa độ nền móng trước, tuyệt đối không tự bịa số cụ thể bằng `add_point`.
- Thực hiện tính toán/dựng hình tuần tự theo các dữ kiện đề bài đưa ra (Điểm -> Đường thẳng -> Trung điểm/Đường vuông góc).
- Khi đã dựng đủ tất cả các thực thể mà đề bài yêu cầu, hãy gọi tool `draw_geometry_and_save` để hoàn thành nhiệm vụ.
- Output bắt buộc phải tuân thủ định dạng JSON array:
  [{"reason": "Suy nghĩ logic của bạn về bước tiếp theo", "next_action": "tên_tool_cần_gọi", "input": {"tên_tham_số": "giá_trị"}, "context": "Tóm tắt trạng thái các điểm"}]
- TRƯỜNG HỢP ĐẶC BIỆT: Nếu phân tích đề bài thấy xuất hiện một thực thể hình học (như đường phân giác, tiếp tuyến, loại giao điểm đặc biệt...) mà KHÔNG CÓ bất kỳ tool nào trong danh sách trên đáp ứng được, hãy trả về định dạng báo lỗi như sau để báo cho lập trình viên bổ sung công cụ:
  [{"reason": "Phát hiện đề bài yêu cầu hành động [tên_hành_động] nhưng hệ thống chưa cung cấp công cụ phù hợp.", "next_action": "error_missing_tool", "input": {"required_task": "Mô tả tác vụ hình học bị thiếu cần phải lập trình"}, "context": "Dừng tiến trình do thiếu công cụ."}]
</rules>"""

    for step in range(MAX_STEPS):

        print(f"\n===== STEP {step+1}/{MAX_STEPS} =====")

        user = f"""<query>{query}</query>
<step>{step+1}/{MAX_STEPS}</step>
<current_geometry_state>
{history if history else "Hệ thống đang trống. Chưa có thực thể nào."}
</current_geometry_state>
<context>{context}</context>

<task>
Dựa vào <current_geometry_state>, hãy chọn bước đi tiếp theo.

QUY TẮC BẮT BUỘC ĐỂ TRÁNH VÒNG LẶP VÀ XỬ LÝ LỖI:
1. Nếu trong <current_geometry_state> ĐÃ CÓ từ 'reset_session' hoặc 'làm sạch hệ thống', TUYỆT ĐỐI KHÔNG ĐƯỢC gọi lại `reset_session` nữa. Hãy chuyển ngay sang bước dựng hình nền móng.
2. Với bài toán đường tròn hiện tại, sau khi đã reset, bước kế tiếp bắt buộc phải là khởi tạo cấu trúc gốc bằng cách gọi tool `create_circle_with_diameter`.
3. Chỉ gọi một tool duy nhất hợp lý cho bước này.
4. CƠ CHẾ PHẢN HỒI THIẾU CÔNG CỤ (FEEDBACK CRITICAL): Đọc kỹ yêu cầu tiếp theo của đề bài. Nếu bước tiếp theo bắt buộc phải kẻ một thực thể mà KHÔNG CÓ công cụ nào trong danh sách <tools> hỗ trợ thực hiện (Ví dụ: Yêu cầu vẽ tiếp tuyến, đường phân giác, kẻ đường vuông góc cắt đường thẳng khác... mà hệ thống chưa có hàm tính toán tương ứng), hãy dừng ngay lập tức và trả về lệnh báo lỗi hệ thống với next_action là "error_missing_tool". Không được cố tình gọi sai tool.
</task>"""
        content, usage = call_llm(system_prompt, user)
        if not content:
            print("LLM không phản hồi")
            continue

        print(f"LLM: {content[:300]}")

        try:
            actions = extract_json(content)
        except Exception as e:
            print(f"Parse JSON lỗi: {e}")
            continue

        if isinstance(actions, dict):
            actions = [actions]
        for act in actions:
            action = act.get("next_action", "")
            inp = act.get("input", {})
            
            print(f"Thực hiện tool: {action} với input: {inp}")
            
            if action == "error_missing_tool":
                tool_result = f"HỆ THỐNG ĐÃ DỪNG: Mô hình thông báo KHÔNG THỂ VẼ do thiếu công cụ lập trình cho tác vụ: [{inp.get('required_task')}]."
                print(f"\n[CRITICAL FEEDBACK]: {tool_result}")
                history += f"\n\nLLM trả về feedback lỗi: {tool_result}"
                done = True
                break
            # --- ĐIỀU PHỐI ĐỘNG (DYNAMIC DISPATCH) ---
            # Kiểm tra xem trong class GeometryEngine có hàm nào trùng tên với "action" không
            if hasattr(engine, action):
                # Lấy hàm đó ra
                tool_func = getattr(engine, action)
                
                try:
                    # Gọi hàm và truyền toàn bộ tham số từ "inp" vào dưới dạng **kwargs
                    # Nếu tool không có tham số (như reset_session), **inp sẽ tự động truyền trống.
                    tool_result = tool_func(**inp)
                except TypeError as e:
                    tool_result = f"Lỗi: Truyền sai tham số cho tool '{action}'. Chi tiết: {e}"
            else:
                tool_result = f"Lỗi: Hệ thống Engine không hỗ trợ tool có tên '{action}'"

            # --- KIỂM TRA ĐIỀU KIỆN DỪNG ---
            if action == "draw_geometry_and_save":
                done = True

            # --- CẬP NHẬT LỊCH SỬ ---
            print(f"-> Kết quả thực thi: {tool_result}")
            history += f"\n\nLLM đã chọn tool: {action} với input: {inp}. Kết quả hệ thống: {tool_result}"
            
            if done:
                break

        if done:
            break
        
if __name__ == "__main__":
    query = """Cho (O; R) có hai đường kính AB và C D vuông góc với nhau. Một điểm M di động trên cung nhỏ
BC (M không trùng với C và B), AM cắt C D tại N. Kẻ C H vuông góc với AM tại H. Gọi giao
điểm của DM với AB là F .
a. Chứng minh tứ giác OAC H nội tiếp.
b. Qua O kẻ đường thẳng vuông góc với OH cắt AM tại E. Chứng minh rằng OH song song với
DM và EN · HM = NH · ME.
c. Tìm vị trí của M trên cung nhỏ BC để SMNF đạt giá trị lớn nhất."""
    context = ""
    main(query, context)