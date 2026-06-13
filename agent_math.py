import os
import re
import json
import inspect

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
    """Parse LLM output thành actions. Có fallback cho:
       - final_answer: text ngoài JSON block
       - JSON bị cắt/corrupt: regex trích xuất next_action
    """
    m_json = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    json_block = m_json.group(1) if m_json else text
    
    # Thử 1: parse JSON chuẩn
    try:
        cleaned = ' '.join(line.strip() for line in json_block.split('\n'))
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
    
    # Thử 2: final_answer → text ngoài JSON là lời giải
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
    
    # Thử 3: JSON bị cắt/corrupt → regex trích next_action + input
    m_action = re.search(r'"next_action"\s*:\s*"([^"]+)"', text)
    if m_action:
        action_name = m_action.group(1)
        inp = {}
        # Trích các key-value đơn giản trong input
        for kv in re.finditer(r'"(\w+)"\s*:\s*("[^"]*"|[\d.]+)', text):
            key, val = kv.group(1), kv.group(2)
            if key in ('next_action', 'reason', 'context'):
                continue
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                val = val.strip('"')
            inp[key] = val
        if action_name == 'final_answer':
            inp['answer'] = inp.get('answer', 'Lời giải chi tiết bị thiếu do lỗi parse.')
        return [{"reason": "Parsed from incomplete JSON",
                 "next_action": action_name, "input": inp, "context": ""}]
    
    raise json.JSONDecodeError("Không thể parse JSON", text, 0)


def main(query: str, context: str):
    MAX_STEPS = 60
    done = False
    history = ""
    action_counter = {}  # loop detection: (action, frozenset(inp)) → count
    MAX_RETRIES = 3      # số lần tối đa gọi lại cùng tool với input tương tự

    tool_descriptions = build_tool_descriptions()

    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system.md")
    with open(prompt_path, encoding="utf-8") as f:
        template = f.read()
    system_prompt = template.replace("{tool_descriptions}", tool_descriptions)

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
                except Exception as e:
                    tool_result = f"Lỗi thực thi tool '{action}': {e}"
            else:
                tool_result = f"Lỗi: Engine không hỗ trợ tool '{action}'"

            # --- LOOP DETECTION: nếu tool lỗi liên tiếp → force final_answer ---
            action_key = (action, frozenset(sorted(inp.items())))
            action_counter[action_key] = action_counter.get(action_key, 0) + 1
            if action_counter[action_key] >= MAX_RETRIES and "Lỗi" in tool_result:
                print(f"⚠️ Phát hiện loop: tool '{action}' lỗi {MAX_RETRIES} lần liên tiếp. Buộc dừng.")
                history += f"\n\n⚠️ LOOP DETECTED: {action} lỗi {MAX_RETRIES} lần. Kết quả cuối: {tool_result}"
                done = True
                break

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
    query = r"""Cho đoạn thẳng $MP$, lấy điểm $N$ bất kì nằm giữa $M$ và $P$. Vẽ $(O)$ đường kính $NP$. Lấy $H$ là trung điểm $MN$. Qua $H$ kẻ đường thẳng $d$ vuông góc với $MN$. Kẻ tiếp tuyến $HQ$ với $(O)$ tại $Q$. Tia $PQ$ cắt $d$ tại $K$. Chứng minh:  a) Tứ giác $KHNQ$ nội tiếp và $\widehat{NPQ} = \widehat{HKN}$.b) $\widehat{MKP} = 90^\circ$ và $PQ \cdot PK = PN \cdot PH$.c) $HQ^2 + PQ \cdot PK = PH^2$ và cho $\widehat{HKN} = 30^\circ$, $R = 6\text{ cm}$. Tính diện tích hình quạt $NOQ$.d) Lấy $I$ là trung điểm $KN$. Chứng minh chu vi đường tròn ngoại tiếp $\Delta QOI$ không đổi khi $N$ di chuyển trên $MP$."""
    context = ""
    main(query, context)
