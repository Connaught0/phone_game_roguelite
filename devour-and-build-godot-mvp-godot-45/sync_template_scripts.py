from pathlib import Path
import re

root = Path(__file__).resolve().parent
template_path = root / 'create_project_files.py'
template = template_path.read_text(encoding='utf-8')
script_keys = [
    'scripts/SkillPayload.gd',
    'scripts/Enemy.gd',
    'scripts/OverchargeProjectile.gd',
    'scripts/Player.gd',
    'scripts/SkillQueueUI.gd',
    'scripts/Main.gd',
]

for key in script_keys:
    script_text = (root / key).read_text(encoding='utf-8')
    if "'''" in script_text:
        raise ValueError(f"Cannot safely embed triple single quotes in {key}")
    pattern = re.compile(rf"('{re.escape(key)}': r''').*?(''',)", re.DOTALL)
    replacement = rf"\1{script_text}\2"
    template, count = pattern.subn(replacement, template, count=1)
    if count != 1:
        raise RuntimeError(f"Failed to update template entry: {key}")

template_path.write_text(template, encoding='utf-8')
print(f'Synchronized {len(script_keys)} script templates into {template_path}')
