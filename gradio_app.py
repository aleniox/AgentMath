import os
import re
import json
import inspect
import io
import sys
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
import requests
from tools import GeometryEngine

load_dotenv()

LLM_API = os.getenv("LLM_API_URL", "http://10.0.99.116:8070/v1/chat/completions")
SKIP_METHODS = {'__init__'}

def build_tool_descriptions(engine):
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

def call_llm(system: str, user: str, api_url: str):
    payload = {
        "model": "", "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], "stream": False,
        "options": {"temperature": 0.0, "top_p": 0.95, "top_k": 64, "num_ctx": 40000},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    resp = requests.post(api_url, json=payload, stream=False, timeout=120)
    if resp.status_code != 200:
        return None, {}
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})

def parse_actions(text: str):
    m_json = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    json_block = m_json.group(1) if m_json else text
    try:
        cleaned = ' '.join(line.strip() for line in json_block.split('\n'))
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
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

def solve_problem(query: str, api_url: str, progress=gr.Progress()):
    if not query.strip():
        return "⚠️ Vui lòng nhập đề bài.", None, ""
    
    engine = GeometryEngine()
    log_lines = []
    output_image = None
    
    def log(msg):
        log_lines.append(msg)
        progress(0, desc=msg[:80])
    
    tool_descriptions = build_tool_descriptions(engine)
    
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system.md")
    with open(prompt_path, encoding="utf-8") as f:
        template = f.read()
    system_prompt = template.replace("{tool_descriptions}", tool_descriptions)

    MAX_STEPS = 50
    done = False
    history = ""
    answer_text = ""
    
    for step in range(MAX_STEPS):
        if done:
            break
        
        step_msg = f"\n{'='*40}\nSTEP {step+1}/{MAX_STEPS}\n{'='*40}"
        log(step_msg)
        
        user = f"""<query>{query}</query>
<step>{step+1}/{MAX_STEPS}</step>
<current_geometry_state>
{history if history else "Hệ thống đang trống. Chưa có thực thể nào."}
</current_geometry_state>
<task>
Dựa vào <current_geometry_state>, hãy chọn bước đi tiếp theo.

QUY TẮC BẮT BUỘC ĐỂ TRÁNH VÒNG LẶP VÀ ĐẢM BẢO HÌNH VẼ HOÀN CHỈNH:
1. Nếu đã có 'reset_session' trong lịch sử, KHÔNG gọi lại. Chuyển sang dựng hình nền móng.
2. Chỉ gọi một tool duy nhất hợp lý cho bước này.
3. Sau khi gọi `draw_geometry_and_save`, gọi ngay `final_answer` ở step kế tiếp.
4. Nếu thiếu tool để thực hiện tác vụ hình học, gọi `error_missing_tool`.
5. KIỂM TRA KẾT NỐI: Trước khi gọi `draw_geometry_and_save`, dò lại toàn bộ đề bài. Với mỗi cặp điểm được nhắc đến (cạnh tam giác, đường chéo, đường cao, giao tuyến...), hãy đảm bảo đã gọi `add_segment` cho chúng.
</task>"""

        content, usage = call_llm(system_prompt, user, api_url)
        if not content:
            log("❌ LLM không phản hồi")
            continue
        
        log(f"LLM: {content[:200]}...")
        
        try:
            actions = parse_actions(content)
        except Exception as e:
            log(f"⚠️ Parse JSON lỗi: {e}")
            continue
        
        if isinstance(actions, dict):
            actions = [actions]
        
        for act in actions:
            action = act.get("next_action", "")
            inp = act.get("input", {})
            
            log(f"🔧 Tool: {action} | Input: {inp}")
            
            if action == "error_missing_tool":
                msg = f"HỆ THỐNG ĐÃ DỪNG: Thiếu công cụ cho tác vụ: [{inp.get('required_task')}]."
                log(f"❌ {msg}")
                done = True
                break
            
            if action == "final_answer":
                answer_text = inp if isinstance(inp, str) else inp.get("answer", str(inp))
                log(f"✅ HOÀN THÀNH")
                done = True
                break
            
            if hasattr(engine, action):
                tool_func = getattr(engine, action)
                try:
                    tool_result = tool_func(**inp)
                except Exception as e:
                    tool_result = f"Lỗi thực thi tool '{action}': {e}"
            else:
                tool_result = f"Lỗi: Engine không hỗ trợ tool '{action}'"
            
            log(f"   Kết quả: {tool_result[:150]}")
            history += f"\n\nLLM chọn tool: {action} input: {inp} → {tool_result}"
    
    # Kiểm tra file ảnh đã được tạo chưa
    img_path = Path("geometry_output.png")
    if img_path.exists():
        log(f"📷 Ảnh đã lưu tại: {img_path.resolve()}")
    
    full_log = "\n".join(log_lines)
    
    # Nếu file ảnh không tồn tại, thử vẽ lại
    if not img_path.exists() and engine.points:
        try:
            result = engine.draw_geometry_and_save()
            log(f"📷 {result}")
        except Exception as e:
            log(f"⚠️ Không thể vẽ hình: {e}")
    
    return full_log, str(img_path) if img_path.exists() else None, answer_text


# ===== Gradio Interface =====
examples = [
    ["Cho tam giác ABC vuông tại B, AB=4, BC=6. Vẽ trung điểm M của BC và chân đường cao H từ A xuống BC."],
    ["Cho (O; R) có hai đường kính AB và CD vuông góc với nhau. Một điểm M di động trên cung nhỏ BC (M không trùng với C và B), AM cắt CD tại N. Kẻ CH vuông góc với AM tại H. Gọi giao điểm của DM với AB là F. a. Chứng minh tứ giác OACH nội tiếp. b. Qua O kẻ đường thẳng vuông góc với OH cắt AM tại E. Chứng minh rằng OH song song với DM và EN · HM = NH · ME. c. Tìm vị trí của M trên cung nhỏ BC để SMNF đạt giá trị lớn nhất."],
    ["Cho đường tròn (O; R) đường kính AB. Lấy C thuộc (O) sao cho AC = R. Trên cung nhỏ BC lấy điểm D (D khác B và C). AC cắt BD tại E. Kẻ EH vuông góc với AB tại H. Tia DH cắt (O) tại điểm thứ hai là F. (a) Chứng minh 4 điểm A, E, D, H cùng thuộc một đường tròn. (b) Chứng minh ∠DHE = ∠DFC, từ đó suy ra △BCF đều. (c) Xác định vị trí điểm D để chu vi tứ giác ABDC đạt giá trị lớn nhất."],
]

with gr.Blocks(title="🧮 Geometry AI Agent", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🧮 Geometry AI Agent
    Nhập đề bài hình học, agent sẽ tự phân tích, dựng hình và đưa ra lời giải.
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            api_url = gr.Textbox(
                label="LLM API URL",
                value=os.getenv("LLM_API_URL", "http://10.0.99.116:8070/v1/chat/completions"),
                placeholder="http://..."
            )
    
    with gr.Row():
        with gr.Column(scale=2):
            query = gr.Textbox(
                label="📝 Đề bài",
                placeholder="Nhập đề bài hình học...",
                lines=6
            )
            with gr.Row():
                run_btn = gr.Button("🚀 Giải bài toán", variant="primary", size="lg")
                clear_btn = gr.Button("🗑️ Xoá", size="lg")
        
        with gr.Column(scale=1):
            image_output = gr.Image(label="📷 Hình vẽ", type="filepath", height=400)
    
    with gr.Accordion("📋 Log chi tiết", open=True):
        log_output = gr.Textbox(label="Các bước thực hiện", lines=15, max_lines=30)
    
    with gr.Accordion("💡 Lời giải", open=True):
        answer_output = gr.Textbox(label="Kết quả", lines=8)
    
    gr.Examples(
        examples=examples,
        inputs=query,
        label="📌 Ví dụ đề bài"
    )
    
    def run_solver(query_text, api_url_text):
        if not query_text.strip():
            return "⚠️ Vui lòng nhập đề bài.", None, ""
        try:
            log_text, img_path, answer = solve_problem(query_text, api_url_text)
            return log_text, img_path, answer
        except Exception as e:
            return f"❌ Lỗi: {e}", None, ""
    
    run_btn.click(
        fn=run_solver,
        inputs=[query, api_url],
        outputs=[log_output, image_output, answer_output]
    )
    
    clear_btn.click(
        fn=lambda: ("", None, ""),
        outputs=[log_output, image_output, answer_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
