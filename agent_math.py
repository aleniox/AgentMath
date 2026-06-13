import asyncio
import os
import re
import json
import inspect
from urllib.parse import urlparse

from dotenv import load_dotenv
import requests
from tools import GeometryEngine
load_dotenv()

LLM_API = os.getenv("LLM_API_URL", "http://10.0.99.116:8070/v1/chat/completions")
engine = GeometryEngine()

SKIP_METHODS = {'__init__'}

def build_tool_descriptions():
    """Tự động sinh danh sách tool từ các method public của GeometryEngine."""
    lines = []
    for name in sorted(dir(engine)):
        if name.startswith('_') or name in SKIP_METHODS:
            continue
        method = getattr(engine, name, None)
        if not callable(method):
            continue
        doc = inspect.getdoc(method) or "Không có mô tả."
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        param_str = ', '.join(params) if params else "Không có tham số"
        lines.append(f"{name}: {doc} Input: {param_str}")
    return '\n'.join(lines)

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


def parse_actions(text: str):
    """Parse LLM output thành actions. Có fallback cho final_answer:
       - Thử 1: parse JSON trực tiếp
       - Thử 2: nếu final_answer, lấy text bên ngoài JSON block
    """
    m_json = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    json_block = m_json.group(1) if m_json else text
    
    # Thử 1: parse chuẩn
    try:
        cleaned = ' '.join(line.strip() for line in json_block.split('\n'))
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
    
    # Thử 2: final_answer -> text ngoài JSON là lời giải
    if 'final_answer' in text:
        answer_text = ""
        if m_json:
            answer_text = text[m_json.end():].strip()
        else:
            m_ans = re.search(r'"answer"\s*:\s*"([^"]*)"', text)
            if m_ans:
                answer_text = m_ans.group(1)
        if answer_text:
            return [{"reason": "Hoàn thành bài toán",
                     "next_action": "final_answer",
                     "input": {"answer": answer_text},
                     "context": ""}]
    
    raise json.JSONDecodeError("Không thể parse JSON", text, 0)


def main(query: str, context: str):
    MAX_STEPS = 100
    done = False
    history = ""

    tool_descriptions = build_tool_descriptions()

    system_prompt = f"""Bạn là chuyên gia Toán Hình Học, có khả năng phân tích đề bài và điều khiển các công cụ để tính toán tọa độ và dựng hình chính xác.

<tools>
{tool_descriptions}
</tools>

<rules>
- Mỗi bước (Step) chỉ được gọi duy nhất MỘT tool.
- Luôn gọi tool `reset_session` ở bước đầu tiên (Step 1) để đảm bảo không bị lẫn dữ liệu cũ.
- Đối với bài toán KHÔNG CÓ TỌA ĐỘ: Bắt buộc dùng `create_general_triangle` hoặc `create_circle_with_diameter` để tự động gán tọa độ nền móng trước, tuyệt đối không tự bịa số cụ thể bằng `add_point`.
- Đối với bài toán CÓ TỌA ĐỘ: Dùng `add_point` cho từng đỉnh.
- Thực hiện tính toán/dựng hình tuần tự theo các dữ kiện đề bài đưa ra.
- Khi đã dựng xong toàn bộ cấu trúc hình học, hãy gọi:
  1. `draw_geometry_and_save` để xuất ảnh
  2. `final_answer` để đưa ra lời giải text (chứng minh, tọa độ, kết luận)
- BẮT BUỘC: Sau `draw_geometry_and_save` bắt buộc phải gọi `final_answer`.
- Khi gọi `final_answer` Sau đó viết lời giải chi tiết (chứng minh, tọa độ, kết luận).
- BẮT BUỘC: Trước khi gọi `draw_geometry_and_save`, kiểm tra **tất cả các cặp điểm** được nối trong đề bài đều đã gọi `add_segment`. Nếu thiếu cạnh/cung nào, hãy bổ sung bằng `add_segment`.
- Output bắt buộc tuân thủ định dạng JSON array:
  [{{"reason": "Suy nghĩ logic của bạn về bước tiếp theo", "next_action": "tên_tool", "input": {{"param": "value"}}, "context": "Tóm tắt trạng thái các điểm"}}]
- TRƯỜNG HỢP ĐẶC BIỆT: Nếu phân tích đề bài thấy xuất hiện tác vụ hình học mà KHÔNG CÓ tool nào đáp ứng được, hãy trả về:
  [{{"reason": "Phát hiện yêu cầu [tác_vụ] nhưng chưa có công cụ.", "next_action": "error_missing_tool", "input": {{"required_task": "Mô tả tác vụ bị thiếu"}}, "context": "Dừng do thiếu công cụ."}}]
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

QUY TẮC BẮT BUỘC ĐỂ TRÁNH VÒNG LẶP VÀ ĐẢM BẢO HÌNH VẼ HOÀN CHỈNH:
1. Nếu đã có 'reset_session' trong lịch sử, KHÔNG gọi lại. Chuyển sang dựng hình nền móng.
2. Chỉ gọi một tool duy nhất hợp lý cho bước này.
3. Sau khi gọi `draw_geometry_and_save`, gọi ngay `final_answer` ở step kế tiếp.
4. Nếu thiếu tool để thực hiện tác vụ hình học, gọi `error_missing_tool`.
5. KIỂM TRA KẾT NỐI: Trước khi gọi `draw_geometry_and_save`, dò lại toàn bộ đề bài. Với mỗi cặp điểm được nhắc đến (cạnh tam giác, đường chéo, đường cao, giao tuyến...), hãy đảm bảo đã gọi `add_segment` cho chúng.
</task>"""

        content, usage = call_llm(system_prompt, user)
        if not content:
            print("LLM không phản hồi")
            continue

        print(f"LLM: {content[:300]}")

        try:
            actions = parse_actions(content)
        except Exception as e:
            print(f"Parse JSON lỗi: {e}")
            continue

        if isinstance(actions, dict):
            actions = [actions]
        for act in actions:
            action = act.get("next_action", "")
            inp = act.get("input", {})
            
            print(f"Thực hiện tool: {action} với input: {inp}")
            
            # Xử lý các action đặc biệt không nằm trong engine
            if action == "error_missing_tool":
                tool_result = f"HỆ THỐNG ĐÃ DỪNG: Thiếu công cụ cho tác vụ: [{inp.get('required_task')}]."
                print(f"\n[CRITICAL]: {tool_result}")
                done = True
                break

            if action == "final_answer":
                tool_result = inp if isinstance(inp, str) else inp.get("answer", str(inp))
                print(f"\n✅ HOÀN THÀNH: {tool_result}")
                done = True
                break

            # --- ĐIỀU PHỐI ĐỘNG (DYNAMIC DISPATCH) ---
            if hasattr(engine, action):
                tool_func = getattr(engine, action)
                try:
                    tool_result = tool_func(**inp)
                except TypeError as e:
                    tool_result = f"Lỗi: Sai tham số tool '{action}'. Chi tiết: {e}"
            else:
                tool_result = f"Lỗi: Engine không hỗ trợ tool '{action}'"

            # --- KIỂM TRA ĐIỀU KIỆN DỪNG ---
            if action == "draw_geometry_and_save":
                print(f"Kết quả: {tool_result}")

            # --- CẬP NHẬT LỊCH SỬ ---
            print(f"-> Kết quả: {tool_result}")
            history += f"\n\nLLM chọn tool: {action} input: {inp} → Kết quả: {tool_result}"

            if done:
                break

        if done:
            break

if __name__ == "__main__":
    query = """Cho (O; R) có hai đường kính AB và CD vuông góc với nhau. Một điểm M di động trên cung nhỏ BC (M không trùng với C và B), AM cắt CD tại N. Kẻ CH vuông góc với AM tại H. Gọi giao điểm của DM với AB là F.
a. Chứng minh tứ giác OACH nội tiếp.
b. Qua O kẻ đường thẳng vuông góc với OH cắt AM tại E. Chứng minh rằng OH song song với DM và EN · HM = NH · ME.
c. Tìm vị trí của M trên cung nhỏ BC để SMNF đạt giá trị lớn nhất."""
    context = ""
    main(query, context)
