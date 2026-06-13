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

actions = {
    "reset_session": engine.reset_session,
    "add_point": engine.add_point,
    "get_midpoint": engine.get_midpoint,
    "get_perpendicular_projection": engine.get_perpendicular_projection,
    "draw_geometry_and_save": engine.draw_geometry_and_save,
}

def main(query: str, context: str):
    MAX_STEPS = 100
    done = False
    history = ""

    system_prompt = """Bạn là chuyên gia Toán Hình Học, có khả năng phân tích đề bài và điều khiển các công cụ để tính toán tọa độ và dựng hình chính xác.

<tools>
reset_session: Xóa hình cũ để bắt đầu bài mới. Không có Input.
create_general_triangle: Tạo tam giác tổng quát (khi đề bài không cho tọa độ). Input: name_a, name_b, name_c (Tên 3 đỉnh).
add_point: Thêm điểm cụ thể khi biết tọa độ. Input: name, x, y.
get_midpoint: Tìm trung điểm. Input: p1_name, p2_name, result_name.
create_line_from_points: Tạo đường thẳng đi qua 2 điểm và nối chúng. Input: p1_name, p2_name, line_name.
get_perpendicular_projection: Hạ đường vuông góc từ 1 điểm xuống đường thẳng đi qua 2 điểm (Đường cao). Input: point_name, p1_line, p2_line, result_name.
draw_geometry_and_save: Xuất/Dựng hình hoàn chỉnh và lưu thành file ảnh. Không có Input.
</tools>

<rules>
- Mỗi lần bước (Step) chỉ được gọi duy nhất MỘT tool.
- Luôn gọi tool `reset_session` ở bước đầu tiên (Step 1) để đảm bảo không bị lẫn dữ liệu cũ.
- Đối với bài toán chứng minh KHÔNG CÓ TỌA ĐỘ: Bắt buộc dùng `create_general_triangle` để tự động gán tọa độ nền móng trước, tuyệt đối không tự bịa số cụ thể bằng `add_point`.
- Thực hiện tính toán/dựng hình tuần tự theo các dữ kiện đề bài đưa ra (Điểm -> Đường thẳng -> Trung điểm/Đường vuông góc).
- Khi đã dựng đủ tất cả các thực thể mà đề bài yêu cầu, hãy gọi tool `draw_geometry_and_save` để hoàn thành nhiệm vụ.
- Output bắt buộc phải tuân thủ định dạng JSON array:
  [{"reason": "Suy nghĩ logic của bạn về bước tiếp theo", "next_action": "tên_tool_cần_gọi", "input": {"tên_tham_số": "giá_trị"}, "context": "Tóm tắt trạng thái các điểm đã dựng được"}]
</rules>"""

    for step in range(MAX_STEPS):

        print(f"\n===== STEP {step+1}/{MAX_STEPS} =====")

        user = f"""<query>{query}</query>
<step>{step+1}/{MAX_STEPS}</step>
<history>{history}</history>
<context>{context}</context>
<task>Phân tích đề bài toán hình học: "{query}" và gọi các công cụ tương ứng để dựng hình.

Hướng dẫn tư duy:
1. Nếu đây là Step 1, hãy gọi `reset_session`.
2. Đọc kỹ đề bài xem có tọa độ sẵn không. Nếu KHÔNG có, hãy gọi `create_general_triangle` cho tam giác nền móng được nhắc tới trong đề.
3. Xác định các điểm hệ quả (Trung điểm, Đường cao, Chân đường vuông góc) và gọi tool tương ứng để tính toán tọa độ cho chúng.
4. Cuối cùng, sau khi đã dựng xong toàn bộ cấu trúc hình học, gọi `draw_geometry_and_save` để xuất file ảnh cho người dùng.</task>"""

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
            inp = act.get("input", "")
            history += f"\n\nLLM đã chọn tool: {action} với input: {inp}"
            if action == "reset_session":
                tool_result = engine.reset_session()
            elif action == "add_point":
                tool_result = engine.add_point(inp.get("name"), inp.get("x"), inp.get("y"))
            elif action == "get_midpoint":
                tool_result = engine.get_midpoint(inp.get("p1_name"), inp.get("p2_name"), inp.get("result_name"))
            elif action == "get_perpendicular_projection":
                tool_result = engine.get_perpendicular_projection(inp.get("point_name"), inp.get("p1_line"), inp.get("p2_line"), inp.get("result_name"))
            elif action == "draw_geometry_and_save":
                tool_result = engine.draw_geometry_and_save()
                print(f"Kết quả: {tool_result}")
                done = True
                break
            else:
                tool_result = f"Lỗi: Không tìm thấy tool có tên '{action}'"

        if done:
            break
        
if __name__ == "__main__":
    query = "Cho tam giác ABC vuông tại B, AB=BC. Vẽ trung điểm M của BC và chân đường cao H từ B xuống AC."
    context = ""
    main(query, context)