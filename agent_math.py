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
    MAX_STEPS = 60
    done = False
    history = ""
    action_counter = {}  # loop detection: (action, frozenset(inp)) → count
    MAX_RETRIES = 3      # số lần tối đa gọi lại cùng tool với input tương tự

    tool_descriptions = build_tool_descriptions()

    system_prompt = f"""Bạn là chuyên gia Toán Hình Học, có khả năng phân tích đề bài và điều khiển các công cụ để tính toán tọa độ và dựng hình chính xác.

<tools>
{tool_descriptions}
</tools>

<huong_dan_toa_do_tong_quat>
1. Dựng hình học KHÔNG CÓ TỌA ĐỘ (bài toán tổng quát):
   - Luôn dựng các thực thể nền móng trước bằng `create_general_triangle` hoặc `create_circle_with_diameter`.
   - Đối với đường tròn đường kính BC (hoặc tên bất kỳ XY): Hãy gọi `create_circle_with_diameter` truyền đường kính này nằm ngang: `horizontal_p1="B"`, `horizontal_p2="C"`. Lúc này, B sẽ ở góc 180° (-R, 0) và C ở góc 0° (R, 0), tâm O ở gốc (0, 0).
   - Nếu đề bài cho "A là điểm chính giữa cung BC", điều này có nghĩa là OA vuông góc với BC. Vì BC nằm ngang, A phải nằm ở đỉnh trên (góc 90°, tọa độ (0, R)) hoặc đỉnh dưới (góc -90°, tọa độ (0, -R)). Bạn hãy dựng điểm A bằng `add_point_on_circle_arc(name="A", center_name="O", angle_deg=90)`.
   - Nếu đề bài có thêm đường kính AD (thường vuông góc với BC), hãy truyền trực tiếp vào `create_circle_with_diameter(center_name="O", radius=5, horizontal_p1="B", horizontal_p2="C", vertical_p1="A", vertical_p2="D")`. Điều này tự động đặt A ở (0, 5) và D ở (0, -5). KHÔNG được gọi lại `add_point_on_circle_arc` cho các điểm đã có trong đường kính để tránh lỗi ghi đè trùng tọa độ.
   - TRÁNH TRÙNG TỌA ĐỘ: Đảm bảo khớp đúng vai trò của các điểm từ đề bài. Tuyệt đối không gán nhầm tên điểm (ví dụ: dùng tên A, B làm đường kính nằm ngang trong khi đề bài bảo đường kính là BC). Hệ thống sẽ báo lỗi và không cho phép nếu bạn gán 2 điểm khác tên vào cùng một tọa độ (hoặc góc).
2. Lấy điểm trên đường tròn thỏa mãn khoảng cách tới một điểm mốc khác bằng bán kính R (ví dụ: lấy điểm P thuộc (O) sao cho khoảng cách từ P tới điểm mốc X bằng R):
   - Sử dụng tính chất của tam giác đều để tính góc lượng giác của điểm cần tìm.
   - Do khoảng cách từ tâm O đến X và P đều bằng R, và khoảng cách XP = R, nên tam giác OXP là tam giác đều, suy ra góc ở tâm XOP = 60°.
   - Như vậy, góc lượng giác của P sẽ lệch so với góc lượng giác của điểm mốc X một lượng 60° (tức là góc của P = góc_của_X + 60° hoặc góc_của_X - 60°).
   - Hãy tính toán góc này một cách cẩn thận trước khi gọi tool `add_point_on_circle_arc`.
3. Lấy điểm nằm trên một cung nhỏ giữa hai điểm P1 (ở góc a1) và P2 (ở góc a2):
   - Hãy chọn góc lượng giác cho điểm mới ở khoảng giữa a1 và a2 (ví dụ: trung bình cộng (a1 + a2)/2) để đảm bảo điểm đó nằm đúng trên cung nhỏ.
4. Tìm giao điểm thứ hai của một đường thẳng với đường tròn (khi đường thẳng đi qua một điểm mốc đã biết nằm trên đường tròn đó):
   - Sử dụng tool `get_line_circle_intersection` và truyền điểm mốc đã biết đó vào tham số `exclude_point`. Công cụ sẽ tự động loại bỏ giao điểm trùng với điểm mốc này và trả về chính xác tọa độ của giao điểm thứ hai.
5. Khi tìm giao điểm của hai đường thẳng bằng `get_line_line_intersection`:
   - Công cụ sẽ tự động vẽ kéo dài các đoạn thẳng gốc tới giao điểm mới. Bạn không cần tự gọi thêm các lệnh vẽ đoạn thẳng kéo dài.
6. KIỂM TRA TRƯỚC KHI VẼ TIẾP TUYẾN: Trước khi gọi `get_tangents_from_external_point`, bắt buộc kiểm tra điểm đó có nằm ngoài đường tròn không bằng `get_distance(point, center)`. So sánh với bán kính R. Nếu điểm nằm trong, điều chỉnh tọa độ trước khi tiếp tục.
7. ĐỒNG THỜI TƯ DUY GIẢI TOÁN VÀ DỰNG HÌNH (CO-REASONING):
   - Bạn không chỉ vẽ các nét được liệt kê trực tiếp ở đề bài, mà phải vẽ toàn bộ các nét phụ trợ được nhắc đến hoặc suy ra trong quá trình giải/chứng minh ở các câu a, b, c.
   - Nếu chứng minh nhiều điểm thuộc cùng một đường tròn (tứ giác nội tiếp), hãy bắt buộc gọi `add_circumcircle` cho các điểm đó. Ví dụ: chứng minh A, E, M, O, F cùng thuộc một đường tròn thì bắt buộc phải gọi `add_circumcircle` đi qua A, E, M (hoặc bất kỳ 3 điểm nào trong số chúng) để đường tròn ngoại tiếp này hiển thị nét đứt màu xanh lá cây trên hình.
   - Nếu có một điểm mới N nằm trên đoạn thẳng EF, và bạn kẻ đường vuông góc MN tới EF, bạn bắt buộc phải gọi `add_segment` nối E và F (nếu chưa được vẽ) trước khi vẽ MN, nếu không điểm N sẽ bị lơ lửng giữa không trung.
   - Hãy rà soát tất cả các cặp điểm có liên hệ hình học trong đề bài và lời giải (ví dụ: EF, OM, MD, DH, HC, v.v.) và gọi `add_segment` để nối chúng lại.
</huong_dan_toa_do_tong_quat>

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
- BẮT BUỘC TƯ DUY VẼ HÌNH ĐẦY ĐỦ: Trước khi gọi `draw_geometry_and_save`, bạn phải tự đặt câu hỏi: "Mọi đường thẳng, phân giác, đường tròn, đoạn thẳng nối phụ trợ được dùng để lập luận chứng minh trong lời giải đã được gọi tool vẽ đầy đủ chưa?". Nếu còn thiếu bất kỳ nét nối nào (như nối E-F, nối O-M, vẽ đường tròn ngoại tiếp, v.v.), hãy gọi các tool tương ứng để hoàn thiện hình vẽ trước khi xuất ảnh.
- KHUYẾN KHÍCH DỰNG HÌNH PHỤ TRỢ: Trong quá trình dựng hình và giải toán, nếu câu hỏi chứng minh hoặc nội dung đề bài nhắc đến các thực thể hoặc tính chất phụ trợ (ví dụ: nhiều điểm cùng thuộc một đường tròn, tứ giác nội tiếp, tam giác đều/cân/vuông, đường phân giác, v.v.), hãy chủ động gọi các công cụ tương ứng (như `add_circumcircle` để vẽ đường tròn ngoại tiếp dưới dạng nét đứt, hoặc `add_segment` để nối các đoạn thẳng phụ). Điều này giúp hình vẽ trực quan, sinh động và đầy đủ giống như hình vẽ lời giải trong thực tế.
- CẢNH BÁO LOOP: Nếu một tool bị lỗi 3 lần liên tiếp với cùng input, hệ thống sẽ tự động dừng. Không retry tool lỗi quá 2 lần. Hãy đổi hướng tiếp cận hoặc gọi `final_answer`.
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
