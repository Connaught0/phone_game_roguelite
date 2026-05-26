from pathlib import Path
import re
import sys

ROOT = Path('/home/ubuntu/devour_and_build_godot')
required_files = [
    'project.godot',
    'scenes/Main.tscn',
    'scenes/Player.tscn',
    'scenes/Enemy.tscn',
    'scenes/OverchargeProjectile.tscn',
    'ui/SkillQueueUI.tscn',
    'scripts/Main.gd',
    'scripts/Player.gd',
    'scripts/Enemy.gd',
    'scripts/SkillPayload.gd',
    'scripts/SkillQueueUI.gd',
    'scripts/OverchargeProjectile.gd',
    'README.md',
    'docs/ARCHITECTURE.md',
]

errors = []
warnings = []

for rel in required_files:
    if not (ROOT / rel).exists():
        errors.append(f'Missing required file: {rel}')

# Check res:// references in tscn and scripts point to existing files.
for path in list((ROOT / 'scenes').glob('*.tscn')) + list((ROOT / 'ui').glob('*.tscn')) + list((ROOT / 'scripts').glob('*.gd')):
    text = path.read_text(encoding='utf-8')
    for ref in re.findall(r'res://[^"\')\s]+', text):
        rel = ref.replace('res://', '')
        if not (ROOT / rel).exists():
            errors.append(f'{path.relative_to(ROOT)} references missing resource: {ref}')

# Check common scene property typo from earlier generation.
for path in (ROOT / 'scenes').glob('*.tscn'):
    text = path.read_text(encoding='utf-8')
    if 'nshape =' in text:
        errors.append(f'{path.relative_to(ROOT)} contains invalid property nshape')

# Check key implementation markers.
markers = {
    'scripts/Player.gd': [
        'func _physics_process',
        'func _try_auto_attack',
        'func try_devour_nearest',
        'func crush_slot',
        'overcharge_requested.emit',
        'MAX_SKILL_QUEUE_SIZE',
    ],
    'scripts/Main.gd': [
        'enum LevelState',
        'func _enter_arena_lock',
        'func _unlock_arena',
        'func _spawn_overcharge_projectile',
    ],
    'scripts/OverchargeProjectile.gd': [
        'area_entered.connect',
        'take_damage(damage',
    ],
    'scripts/SkillQueueUI.gd': [
        'signal slot_pressed',
        'func refresh_queue',
    ],
}
for rel, needed in markers.items():
    text = (ROOT / rel).read_text(encoding='utf-8')
    for marker in needed:
        if marker not in text:
            errors.append(f'{rel} missing marker: {marker}')

# Basic bracket sanity for scripts.
for path in (ROOT / 'scripts').glob('*.gd'):
    text = path.read_text(encoding='utf-8')
    if text.count('(') != text.count(')'):
        warnings.append(f'Parenthesis count mismatch candidate: {path.relative_to(ROOT)}')
    if text.count('[') != text.count(']'):
        warnings.append(f'Bracket count mismatch candidate: {path.relative_to(ROOT)}')

if errors:
    print('VALIDATION FAILED')
    for err in errors:
        print(f'ERROR: {err}')
    if warnings:
        for warn in warnings:
            print(f'WARNING: {warn}')
    sys.exit(1)

print('VALIDATION PASSED')
print(f'Project root: {ROOT}')
print(f'Required files checked: {len(required_files)}')
print('Core implementation markers checked successfully.')
if warnings:
    for warn in warnings:
        print(f'WARNING: {warn}')
