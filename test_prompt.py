import sys
from tools import GeometryEngine
import inspect, os

engine = GeometryEngine()
lines = []
for name in sorted(dir(engine)):
    if name.startswith('_') or name == '__init__':
        continue
    method = getattr(engine, name, None)
    if not callable(method):
        continue
    doc = inspect.getdoc(method) or 'No doc'
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())
    param_str = ', '.join(params) if params else 'N/A'
    lines.append(f'{name}: {doc} Input: {param_str}')
tool_descriptions = '\n'.join(lines)

with open('prompts/system.md', encoding='utf-8') as f:
    template = f.read()
system_prompt = template.format(tool_descriptions=tool_descriptions)

print(f"OK ({len(system_prompt)} chars)")
assert '<tools>' in system_prompt
assert 'reset_session' in system_prompt
assert 'final_answer' in system_prompt
print("All assertions passed")
