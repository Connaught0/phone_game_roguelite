from pathlib import Path

ROOT = Path('/home/ubuntu/devour_and_build_godot')

files = {
    'project.godot': r'''config_version=5

[application]
config/name="Devour & Build MVP"
run/main_scene="res://scenes/Main.tscn"
config/features=PackedStringArray("4.2", "Mobile")

[display]
window/size/viewport_width=720
window/size/viewport_height=1280
window/handheld/orientation=1
window/stretch/mode="canvas_items"
window/stretch/aspect="keep_width"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
''',

    '.gitignore': r'''# Godot 4
.godot/
.import/
export.cfg
export_presets.cfg
*.translation

# OS / editor
.DS_Store
Thumbs.db
.vscode/
.idea/

# Local generated archives
*.zip
''',

    'scripts/SkillPayload.gd': r'''class_name SkillPayload
extends Resource

@export var skill_id: String = ""
@export_enum("Fire", "Ice", "Poison", "Lightning") var element: String = "Fire"
@export_enum("Heal", "SpeedUp", "AttackBoost", "Fortify") var crush_reward: String = "Heal"

func duplicate_payload() -> SkillPayload:
	var payload: SkillPayload = SkillPayload.new()
	payload.skill_id = skill_id
	payload.element = element
	payload.crush_reward = crush_reward
	return payload

static func create(payload_id: String, element_name: String, reward_name: String) -> SkillPayload:
	var payload: SkillPayload = SkillPayload.new()
	payload.skill_id = payload_id
	payload.element = element_name
	payload.crush_reward = reward_name
	return payload
''',

    'scripts/Enemy.gd': r'''class_name Enemy
extends Area2D

signal died(enemy: Enemy)

@export var max_health: float = 40.0
@export var move_speed: float = 0.0
@export var attack_damage: float = 8.0
@export var attack_range: float = 80.0
@export_enum("Fire", "Ice", "Poison", "Lightning") var element_tag: String = "Fire"
@export_enum("Projectile", "ConeAOE", "Aura") var action_type: String = "Projectile"
@export_enum("Heal", "SpeedUp", "AttackBoost", "Fortify") var crush_reward: String = "Heal"
@export var devourable: bool = true

var current_health: float

@onready var body: Polygon2D = $Body
@onready var health_label: Label = $HealthLabel
@onready var element_label: Label = $ElementLabel

func _ready() -> void:
	current_health = max_health
	add_to_group("enemies")
	_update_look()
	_update_labels()

func get_skill_payload() -> SkillPayload:
	return SkillPayload.create(name, element_tag, crush_reward)

func take_damage(amount: float, elements: Array = []) -> void:
	current_health = maxf(0.0, current_health - amount)
	print("Enemy %s took %.1f damage, elements=%s, hp=%.1f" % [name, amount, str(elements), current_health])
	_update_labels()
	if current_health <= 0.0:
		_die()

func take_devour() -> void:
	print("Enemy %s was devoured, payload=%s/%s" % [name, element_tag, crush_reward])
	_die()

func _die() -> void:
	if is_queued_for_deletion():
		return
	died.emit(self)
	queue_free()

func _update_labels() -> void:
	if is_instance_valid(health_label):
		health_label.text = "%d" % int(ceil(current_health))
	if is_instance_valid(element_label):
		element_label.text = element_tag.substr(0, 1)

func _update_look() -> void:
	body.color = _element_color(element_tag)

func _element_color(element: String) -> Color:
	match element:
		"Fire":
			return Color(1.0, 0.25, 0.12)
		"Ice":
			return Color(0.35, 0.85, 1.0)
		"Poison":
			return Color(0.35, 1.0, 0.25)
		"Lightning":
			return Color(1.0, 0.9, 0.15)
		_:
			return Color.WHITE
''',

    'scripts/OverchargeProjectile.gd': r'''class_name OverchargeProjectile
extends Area2D

@export var speed: float = 920.0
@export var damage: float = 120.0
@export var lifetime: float = 1.25

var direction: Vector2 = Vector2.UP
var element: String = "Fire"
var _hit_targets: Dictionary = {}

@onready var body: Polygon2D = $Body
@onready var element_label: Label = $ElementLabel

func _ready() -> void:
	area_entered.connect(_on_area_entered)
	_update_look()

func setup(payload: SkillPayload, fire_direction: Vector2) -> void:
	element = payload.element
	direction = fire_direction.normalized()
	if direction == Vector2.ZERO:
		direction = Vector2.UP
	rotation = direction.angle() + PI / 2.0
	_update_look()

func _physics_process(delta: float) -> void:
	global_position += direction * speed * delta
	lifetime -= delta
	if lifetime <= 0.0:
		queue_free()

func _on_area_entered(area: Area2D) -> void:
	if area is Enemy and not _hit_targets.has(area.get_instance_id()):
		_hit_targets[area.get_instance_id()] = true
		area.take_damage(damage, [element, "Overcharge"])

func _update_look() -> void:
	if not is_inside_tree():
		return
	body.color = _element_color(element)
	element_label.text = element.substr(0, 1)

func _element_color(element_name: String) -> Color:
	match element_name:
		"Fire":
			return Color(1.0, 0.45, 0.15)
		"Ice":
			return Color(0.45, 0.95, 1.0)
		"Poison":
			return Color(0.45, 1.0, 0.35)
		"Lightning":
			return Color(1.0, 0.95, 0.25)
		_:
			return Color.WHITE
''',

    'scripts/Player.gd': r'''class_name Player
extends CharacterBody2D

signal skill_queue_changed(queue: Array)
signal overcharge_requested(payload: SkillPayload, origin: Vector2, direction: Vector2)
signal devoured_enemy(enemy: Enemy, payload: SkillPayload)

const MAX_SKILL_QUEUE_SIZE: int = 3
const DOUBLE_TAP_WINDOW: float = 0.28
const LEFT_UI_RATIO: float = 0.33

enum PlayerState { IDLE_MOVING, DEVOURING, CRUSHING }

@export var max_health: float = 100.0
@export var base_move_speed: float = 360.0
@export var base_attack_damage: float = 18.0
@export var target_detection_radius: float = 260.0
@export var auto_attack_interval: float = 1.0
@export var devour_dash_time: float = 0.12
@export var invincibility_duration: float = 0.22

var current_health: float = 100.0
var state: PlayerState = PlayerState.IDLE_MOVING
var skill_queue: Array[SkillPayload] = []
var is_invincible: bool = false
var bonus_move_speed: float = 0.0
var bonus_attack_damage: float = 0.0

var _drag_active: bool = false
var _movement_input: Vector2 = Vector2.ZERO
var _last_drag_position: Vector2 = Vector2.ZERO
var _last_tap_time: float = -10.0
var _last_move_direction: Vector2 = Vector2.UP
var _auto_attack_timer: float = 0.0

@onready var radius_shape: CollisionShape2D = $DetectionRadius
@onready var status_label: Label = $StatusLabel

func _ready() -> void:
	current_health = max_health
	_ensure_desktop_input_actions()
	if radius_shape.shape is CircleShape2D:
		radius_shape.shape.radius = target_detection_radius
	_emit_queue_changed()
	_update_status_label()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		_handle_screen_touch(event)
	elif event is InputEventScreenDrag:
		_handle_screen_drag(event)
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_handle_mouse_button(event)
	elif event is InputEventMouseMotion:
		_handle_mouse_motion(event)

func _physics_process(delta: float) -> void:
	var keyboard_input: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if keyboard_input != Vector2.ZERO:
		_movement_input = keyboard_input
		_last_move_direction = keyboard_input.normalized()

	if state == PlayerState.DEVOURING:
		velocity = Vector2.ZERO
		move_and_slide()
		return

	var final_speed: float = base_move_speed + bonus_move_speed
	velocity = _movement_input.normalized() * final_speed
	if velocity.length() > 0.1:
		_last_move_direction = velocity.normalized()
	move_and_slide()

func _process(delta: float) -> void:
	_auto_attack_timer -= delta
	if _auto_attack_timer <= 0.0:
		_auto_attack_timer = auto_attack_interval
		_try_auto_attack()
	_update_status_label()

func crush_slot(index: int) -> void:
	if index < 0 or index >= skill_queue.size():
		print("Crush ignored: slot %d is empty" % [index + 1])
		return

	var payload: SkillPayload = skill_queue[index]
	skill_queue.remove_at(index)
	_apply_crush_reward(payload)
	_emit_queue_changed()

func try_devour_nearest() -> void:
	if state == PlayerState.DEVOURING:
		return
	var target: Enemy = _find_nearest_devourable_enemy()
	if target == null:
		print("Devour failed: no devourable enemy in radius")
		return
	_perform_devour(target)

func _handle_screen_touch(event: InputEventScreenTouch) -> void:
	if _is_left_ui_zone(event.position):
		return
	if event.pressed:
		_drag_active = true
		_last_drag_position = event.position
		_handle_tap_candidate()
	else:
		_drag_active = false
		_movement_input = Vector2.ZERO

func _handle_screen_drag(event: InputEventScreenDrag) -> void:
	if not _drag_active or _is_left_ui_zone(event.position):
		return
	_movement_input = event.relative.limit_length(64.0) / 64.0
	_last_drag_position = event.position

func _handle_mouse_button(event: InputEventMouseButton) -> void:
	if _is_left_ui_zone(event.position):
		return
	if event.pressed:
		_drag_active = true
		_last_drag_position = event.position
		_handle_tap_candidate()
	else:
		_drag_active = false
		_movement_input = Vector2.ZERO

func _handle_mouse_motion(event: InputEventMouseMotion) -> void:
	if not _drag_active or _is_left_ui_zone(event.position):
		return
	_movement_input = event.relative.limit_length(64.0) / 64.0
	_last_drag_position = event.position

func _handle_tap_candidate() -> void:
	var now: float = Time.get_ticks_msec() / 1000.0
	if now - _last_tap_time <= DOUBLE_TAP_WINDOW:
		try_devour_nearest()
		_last_tap_time = -10.0
	else:
		_last_tap_time = now

func _is_left_ui_zone(screen_position: Vector2) -> bool:
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	return screen_position.x <= viewport_size.x * LEFT_UI_RATIO

func _perform_devour(target: Enemy) -> void:
	state = PlayerState.DEVOURING
	is_invincible = true
	var payload: SkillPayload = target.get_skill_payload().duplicate_payload()
	var target_position: Vector2 = target.global_position

	var tween: Tween = create_tween()
	tween.tween_property(self, "global_position", target_position, devour_dash_time).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	await tween.finished

	if is_instance_valid(target):
		devoured_enemy.emit(target, payload)
		target.take_devour()
	_resolve_devour(payload, target_position)

	await get_tree().create_timer(invincibility_duration).timeout
	is_invincible = false
	if state == PlayerState.DEVOURING:
		state = PlayerState.IDLE_MOVING

func _resolve_devour(payload: SkillPayload, origin: Vector2) -> void:
	if skill_queue.size() < MAX_SKILL_QUEUE_SIZE:
		skill_queue.append(payload)
		print("Devour resolved: payload added, queue=%s" % _queue_debug_text())
		_emit_queue_changed()
	else:
		print("Devour resolved: queue full, overcharge projectile emitted with %s" % payload.element)
		overcharge_requested.emit(payload, origin, _last_move_direction)

func _try_auto_attack() -> void:
	var target: Enemy = _find_nearest_enemy()
	if target == null:
		return
	var elements: Array[String] = _current_elements()
	var damage: float = base_attack_damage + bonus_attack_damage + skill_queue.size() * 4.0
	print("Auto attack: target=%s damage=%.1f elements=%s" % [target.name, damage, str(elements)])
	target.take_damage(damage, elements)

func _find_nearest_enemy() -> Enemy:
	var nearest: Enemy = null
	var nearest_distance: float = INF
	for node in get_tree().get_nodes_in_group("enemies"):
		if not is_instance_valid(node) or not (node is Enemy):
			continue
		var distance: float = global_position.distance_to(node.global_position)
		if distance <= target_detection_radius and distance < nearest_distance:
			nearest = node
			nearest_distance = distance
	return nearest

func _find_nearest_devourable_enemy() -> Enemy:
	var target: Enemy = _find_nearest_enemy()
	if target != null and target.devourable:
		return target
	return null

func _current_elements() -> Array[String]:
	var elements: Array[String] = []
	for payload in skill_queue:
		if not elements.has(payload.element):
			elements.append(payload.element)
	return elements

func _apply_crush_reward(payload: SkillPayload) -> void:
	state = PlayerState.CRUSHING
	print("Crush slot: reward=%s from %s" % [payload.crush_reward, payload.element])
	match payload.crush_reward:
		"Heal":
			current_health = minf(max_health, current_health + max_health * 0.2)
		"SpeedUp":
			bonus_move_speed += 160.0
			_reset_temporary_buff("speed", 3.0)
		"AttackBoost":
			bonus_attack_damage += 18.0
			_reset_temporary_buff("attack", 3.0)
		"Fortify":
			is_invincible = true
			_reset_temporary_buff("fortify", 2.0)
		_:
			pass
	await get_tree().create_timer(0.18).timeout
	if state == PlayerState.CRUSHING:
		state = PlayerState.IDLE_MOVING

func _reset_temporary_buff(buff_name: String, duration: float) -> void:
	await get_tree().create_timer(duration).timeout
	match buff_name:
		"speed":
			bonus_move_speed = maxf(0.0, bonus_move_speed - 160.0)
		"attack":
			bonus_attack_damage = maxf(0.0, bonus_attack_damage - 18.0)
		"fortify":
			is_invincible = false

func _emit_queue_changed() -> void:
	skill_queue_changed.emit(skill_queue)

func _queue_debug_text() -> String:
	var parts: Array[String] = []
	for payload in skill_queue:
		parts.append("%s/%s" % [payload.element, payload.crush_reward])
	return "[" + ", ".join(parts) + "]"

func _update_status_label() -> void:
	if not is_instance_valid(status_label):
		return
	var state_text: String = str(PlayerState.keys()[state])
	status_label.text = "HP %d/%d
%s
Queue %d/3" % [int(current_health), int(max_health), state_text, skill_queue.size()]

func _ensure_desktop_input_actions() -> void:
	var bindings: Dictionary = {
		"move_left": KEY_A,
		"move_right": KEY_D,
		"move_up": KEY_W,
		"move_down": KEY_S,
	}
	for action_name: String in bindings.keys():
		if not InputMap.has_action(action_name):
			InputMap.add_action(action_name)
		var event: InputEventKey = InputEventKey.new()
		event.keycode = int(bindings[action_name])
		if not InputMap.action_has_event(action_name, event):
			InputMap.action_add_event(action_name, event)
''',

    'scripts/SkillQueueUI.gd': r'''extends CanvasLayer

signal slot_pressed(index: int)

@onready var slots: Array[Button] = [$Root/SlotContainer/Slot1 as Button, $Root/SlotContainer/Slot2 as Button, $Root/SlotContainer/Slot3 as Button]
@onready var info_label: Label = $Root/InfoLabel
@onready var help_label: Label = $Root/HelpLabel

func _ready() -> void:
	for i in range(slots.size()):
		var index: int = i
		slots[i].pressed.connect(func() -> void:
			slot_pressed.emit(index)
		)
	refresh_queue([])
	help_label.text = "右侧拖拽移动 / 快速双击吞噬
左下点击槽位粉碎技能"

func refresh_queue(queue: Array) -> void:
	for i in range(slots.size()):
		var button: Button = slots[i]
		if i < queue.size():
			var payload: SkillPayload = queue[i]
			button.text = "%d
%s
%s" % [i + 1, payload.element, payload.crush_reward]
			button.disabled = false
			button.modulate = _element_color(payload.element)
		else:
			button.text = "%d
空" % [i + 1]
			button.disabled = true
			button.modulate = Color(0.45, 0.45, 0.45, 0.85)
	info_label.text = "Skill Queue: %d/3" % queue.size()

func _element_color(element: String) -> Color:
	match element:
		"Fire":
			return Color(1.0, 0.45, 0.25, 1.0)
		"Ice":
			return Color(0.45, 0.88, 1.0, 1.0)
		"Poison":
			return Color(0.45, 1.0, 0.35, 1.0)
		"Lightning":
			return Color(1.0, 0.95, 0.25, 1.0)
		_:
			return Color.WHITE
''',

    'scripts/Main.gd': r'''extends Node2D

enum LevelState { SCROLLING, ARENA_LOCK, UNLOCK }

const ENEMY_SCENE: PackedScene = preload("res://scenes/Enemy.tscn")
const PROJECTILE_SCENE: PackedScene = preload("res://scenes/OverchargeProjectile.tscn")

@export var arena_trigger_y: float = 120.0
@export var scroll_follow_offset: Vector2 = Vector2(0.0, -260.0)

var level_state: LevelState = LevelState.SCROLLING
var _arena_enemies: Array[Enemy] = []
var _corridor_index: int = 0

@onready var world: Node2D = $World
@onready var player: Player = $World/Player
@onready var camera: Camera2D = $World/Camera2D
@onready var ui: CanvasLayer = $SkillQueueUI
@onready var state_label: Label = $SkillQueueUI/Root/StateLabel

func _ready() -> void:
	player.skill_queue_changed.connect(ui.refresh_queue)
	player.overcharge_requested.connect(_spawn_overcharge_projectile)
	ui.slot_pressed.connect(player.crush_slot)
	camera.enabled = true
	_spawn_opening_corridor()
	ui.refresh_queue(player.skill_queue)
	_update_state_label()

func _process(delta: float) -> void:
	match level_state:
		LevelState.SCROLLING:
			_update_scrolling_camera(delta)
			if player.global_position.y <= arena_trigger_y:
				_enter_arena_lock()
		LevelState.ARENA_LOCK:
			_check_arena_clear()
		LevelState.UNLOCK:
			_update_scrolling_camera(delta)
	_update_state_label()

func _update_scrolling_camera(delta: float) -> void:
	var desired_position: Vector2 = player.global_position + scroll_follow_offset
	camera.global_position = camera.global_position.lerp(desired_position, clampf(delta * 5.0, 0.0, 1.0))

func _spawn_opening_corridor() -> void:
	var base_y: float = 710.0 - _corridor_index * 820.0
	_spawn_enemy(Vector2(250, base_y), "Fire", "Heal")
	_spawn_enemy(Vector2(470, base_y - 120), "Ice", "SpeedUp")
	_spawn_enemy(Vector2(360, base_y - 270), "Poison", "AttackBoost")
	_corridor_index += 1

func _enter_arena_lock() -> void:
	level_state = LevelState.ARENA_LOCK
	_arena_enemies.clear()
	camera.global_position = Vector2(360.0, arena_trigger_y - 120.0)
	print("Level state: ARENA_LOCK")

	var rows: Array[float] = [arena_trigger_y - 130.0, arena_trigger_y - 300.0]
	var elements: Array[String] = ["Fire", "Ice", "Poison", "Lightning", "Fire", "Ice"]
	var rewards: Array[String] = ["Heal", "SpeedUp", "AttackBoost", "Fortify", "Heal", "AttackBoost"]
	var idx: int = 0
	for row in range(rows.size()):
		for col in range(3):
			var pos: Vector2 = Vector2(210.0 + col * 150.0, rows[row])
			var enemy: Enemy = _spawn_enemy(pos, elements[idx], rewards[idx])
			_arena_enemies.append(enemy)
			idx += 1

func _check_arena_clear() -> void:
	_arena_enemies = _arena_enemies.filter(func(enemy: Enemy) -> bool:
		return is_instance_valid(enemy) and not enemy.is_queued_for_deletion()
	)
	if _arena_enemies.is_empty():
		_unlock_arena()

func _unlock_arena() -> void:
	level_state = LevelState.UNLOCK
	print("Level state: UNLOCK")
	await get_tree().create_timer(0.65).timeout
	arena_trigger_y -= 820.0
	_spawn_opening_corridor()
	level_state = LevelState.SCROLLING
	print("Level state: SCROLLING")

func _spawn_enemy(pos: Vector2, element: String, reward: String) -> Enemy:
	var enemy: Enemy = ENEMY_SCENE.instantiate()
	enemy.global_position = pos
	enemy.element_tag = element
	enemy.crush_reward = reward
	enemy.name = "Enemy_%s_%03d" % [element, randi() % 1000]
	world.add_child(enemy)
	enemy.died.connect(_on_enemy_died)
	return enemy

func _on_enemy_died(enemy: Enemy) -> void:
	print("Enemy died: %s" % enemy.name)

func _spawn_overcharge_projectile(payload: SkillPayload, origin: Vector2, direction: Vector2) -> void:
	var projectile: OverchargeProjectile = PROJECTILE_SCENE.instantiate()
	world.add_child(projectile)
	projectile.global_position = origin + direction.normalized() * 34.0
	projectile.setup(payload, direction)

func _update_state_label() -> void:
	var level_state_text: String = str(LevelState.keys()[level_state])
	state_label.text = "Level: %s
Arena trigger Y: %d" % [level_state_text, int(arena_trigger_y)]
''',

    'scenes/Player.tscn': r'''[gd_scene load_steps=4 format=3]

[ext_resource type="Script" path="res://scripts/Player.gd" id="1_player"]

[sub_resource type="CircleShape2D" id="CircleShape2D_body"]
radius = 24.0

[sub_resource type="CircleShape2D" id="CircleShape2D_detection"]
radius = 260.0

[node name="Player" type="CharacterBody2D"]
script = ExtResource("1_player")

[node name="Body" type="Polygon2D" parent="."]
color = Color(0.1, 0.72, 1, 1)
polygon = PackedVector2Array(0, -30, 24, 18, -24, 18)

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("CircleShape2D_body")

[node name="DetectionRadius" type="CollisionShape2D" parent="."]
visible = false
shape = SubResource("CircleShape2D_detection")

[node name="StatusLabel" type="Label" parent="."]
offset_left = -58.0
offset_top = 32.0
offset_right = 88.0
offset_bottom = 104.0
text = "HP"
''',

    'scenes/Enemy.tscn': r'''[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://scripts/Enemy.gd" id="1_enemy"]

[sub_resource type="RectangleShape2D" id="RectangleShape2D_enemy"]
size = Vector2(48, 48)

[node name="Enemy" type="Area2D"]
collision_layer = 2
collision_mask = 5
script = ExtResource("1_enemy")

[node name="Body" type="Polygon2D" parent="."]
color = Color(1, 0.25, 0.12, 1)
polygon = PackedVector2Array(-24, -24, 24, -24, 24, 24, -24, 24)

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("RectangleShape2D_enemy")

[node name="HealthLabel" type="Label" parent="."]
offset_left = -18.0
offset_top = -56.0
offset_right = 52.0
offset_bottom = -28.0
text = "40"

[node name="ElementLabel" type="Label" parent="."]
offset_left = -8.0
offset_top = -14.0
offset_right = 24.0
offset_bottom = 20.0
text = "F"
''',

    'scenes/OverchargeProjectile.tscn': r'''[gd_scene load_steps=3 format=3]

[ext_resource type="Script" path="res://scripts/OverchargeProjectile.gd" id="1_projectile"]

[sub_resource type="CircleShape2D" id="CircleShape2D_projectile"]
radius = 18.0

[node name="OverchargeProjectile" type="Area2D"]
collision_layer = 4
collision_mask = 2
script = ExtResource("1_projectile")

[node name="Body" type="Polygon2D" parent="."]
color = Color(1, 0.85, 0.15, 1)
polygon = PackedVector2Array(0, -28, 18, 18, 0, 10, -18, 18)

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("CircleShape2D_projectile")

[node name="ElementLabel" type="Label" parent="."]
offset_left = -8.0
offset_top = -12.0
offset_right = 24.0
offset_bottom = 20.0
text = "F"
''',

    'ui/SkillQueueUI.tscn': r'''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/SkillQueueUI.gd" id="1_ui"]

[node name="SkillQueueUI" type="CanvasLayer"]
script = ExtResource("1_ui")

[node name="Root" type="Control" parent="."]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2

[node name="SlotContainer" type="HBoxContainer" parent="Root"]
layout_mode = 0
offset_left = 24.0
offset_top = 1110.0
offset_right = 360.0
offset_bottom = 1230.0
theme_override_constants/separation = 12

[node name="Slot1" type="Button" parent="Root/SlotContainer"]
custom_minimum_size = Vector2(104, 104)
layout_mode = 2
text = "1\n空"

[node name="Slot2" type="Button" parent="Root/SlotContainer"]
custom_minimum_size = Vector2(104, 104)
layout_mode = 2
text = "2\n空"

[node name="Slot3" type="Button" parent="Root/SlotContainer"]
custom_minimum_size = Vector2(104, 104)
layout_mode = 2
text = "3\n空"

[node name="InfoLabel" type="Label" parent="Root"]
layout_mode = 0
offset_left = 24.0
offset_top = 1056.0
offset_right = 360.0
offset_bottom = 1092.0
text = "Skill Queue: 0/3"

[node name="HelpLabel" type="Label" parent="Root"]
layout_mode = 0
offset_left = 360.0
offset_top = 1120.0
offset_right = 700.0
offset_bottom = 1228.0
horizontal_alignment = 2
text = "Help"

[node name="StateLabel" type="Label" parent="Root"]
layout_mode = 0
offset_left = 24.0
offset_top = 24.0
offset_right = 360.0
offset_bottom = 92.0
text = "Level"
''',

    'scenes/Main.tscn': r'''[gd_scene load_steps=4 format=3]

[ext_resource type="Script" path="res://scripts/Main.gd" id="1_main"]
[ext_resource type="PackedScene" path="res://scenes/Player.tscn" id="2_player"]
[ext_resource type="PackedScene" path="res://ui/SkillQueueUI.tscn" id="3_ui"]

[node name="Main" type="Node2D"]
script = ExtResource("1_main")

[node name="World" type="Node2D" parent="."]

[node name="Player" parent="World" instance=ExtResource("2_player")]
position = Vector2(360, 900)

[node name="Camera2D" type="Camera2D" parent="World"]
position = Vector2(360, 640)
enabled = true
position_smoothing_enabled = true
position_smoothing_speed = 5.0

[node name="SkillQueueUI" parent="." instance=ExtResource("3_ui")]
''',

    'README.md': r'''# Devour & Build Godot MVP

本项目是《Devour & Build（吞噬与构筑）》核心战斗循环的 **Godot 4 白盒 MVP**。当前实现目标不是美术成品，而是验证核心闭环：**拖拽移动、自动索敌攻击、双击吞噬、三格技能队列、满载吐星星、点击槽位粉碎、锁屏战状态机**。

## 运行环境

请使用 **Godot 4.2 或更高版本** 打开本目录中的 `project.godot`。主场景已设置为 `res://scenes/Main.tscn`，打开项目后直接运行即可。

| 项目 | 内容 |
| --- | --- |
| 引擎 | Godot 4.x |
| 视图 | 2D 竖屏，720×1280 |
| 主场景 | `scenes/Main.tscn` |
| 核心脚本 | `scripts/Player.gd`, `scripts/Main.gd`, `scripts/Enemy.gd` |
| UI | `ui/SkillQueueUI.tscn`, `scripts/SkillQueueUI.gd` |

## 操作方式

在移动端或 Godot 远程调试中，屏幕中/右侧拖拽会驱动玩家移动，快速双击会在索敌半径内吞噬最近敌人。左下角 1 至 3 号槽位用于粉碎技能。为了便于桌面调试，项目也提供了 **WASD 移动** 与 **鼠标左键拖拽/双击** 的输入兼容。

## 当前已实现的 GDD 对照

| GDD 模块 | MVP 实现状态 | 关键文件 |
| --- | --- | --- |
| 玩家基础属性与状态机 | 已实现 `IDLE_MOVING / DEVOURING / CRUSHING` | `scripts/Player.gd` |
| 敌人标签与技能载荷 | 已实现 `ElementTag / ActionType / CrushReward` | `scripts/Enemy.gd`, `scripts/SkillPayload.gd` |
| 拖拽移动 | 已实现触屏与鼠标拖拽 | `scripts/Player.gd` |
| 双击吞噬 | 已实现最近目标检测、冲刺、销毁与结算 | `scripts/Player.gd` |
| UI 技能队列 | 已实现 3 槽队列与点击粉碎 | `ui/SkillQueueUI.tscn`, `scripts/SkillQueueUI.gd` |
| 自动攻击 | 已实现定时索敌、元素叠加、伤害打印 | `scripts/Player.gd` |
| 满载吐星星 | 已实现贯穿投射物与元素伤害 | `scripts/OverchargeProjectile.gd` |
| 关卡推进/锁屏战 | 已实现推进、触发锁屏、刷两排怪、清场解锁 | `scripts/Main.gd` |

## 建议测试路径

运行后先用 WASD 或右侧拖拽靠近走廊敌人，观察控制台中的 `Auto attack` 日志。随后快速双击吞噬敌人，左下 UI 会加入元素技能。队列满 3 格后继续吞噬敌人，会触发高速贯穿投射物，即当前的“吐星星”机制。移动到更靠上的区域后会进入 `ARENA_LOCK`，场景刷出两排敌人，清空后恢复推进状态。

## 下一步建议

当前版本已经完成系统闭环。下一阶段可以把白盒表现升级为可感知的战斗反馈，包括吞噬冲刺残影、投射物特效、元素状态视觉化、敌人基础 AI、移动边界与受击反馈。待手感确认后，再进入数值表、关卡波次配置与移动端导出配置。
''',

    'docs/ARCHITECTURE.md': r'''# 核心战斗系统实现说明

本文档说明《Devour & Build》Godot MVP 的工程结构与主要运行逻辑，供后续程序员或代码 Agent 继续扩展。

## 模块边界

| 模块 | 职责 | 输入 | 输出 |
| --- | --- | --- | --- |
| `Player` | 处理输入、移动、索敌、自动攻击、吞噬结算与粉碎 Buff | 触屏/鼠标/WASD、敌人列表、UI 槽位点击 | 技能队列变化、满载投射物请求、敌人伤害 |
| `Enemy` | 提供敌人基础面板与载荷数据，响应伤害和吞噬 | 伤害、吞噬请求 | 死亡信号、技能载荷 |
| `SkillPayload` | 表示被吞噬后进入队列的技能数据 | 敌人标签 | 元素、粉碎收益 |
| `SkillQueueUI` | 展示 3 格技能队列并发出粉碎槽位请求 | 队列刷新 | 槽位点击信号 |
| `OverchargeProjectile` | 实现满载时的贯穿型吐星星实体 | 载荷、方向 | 对沿途敌人造成高额伤害 |
| `Main` | 负责连接模块、生成敌人、切换关卡状态机 | 玩家位置、敌人死亡 | 刷怪、锁屏、解锁 |

## 玩家状态机

`Player.gd` 中使用 `PlayerState` 枚举表达三个状态。`IDLE_MOVING` 是默认状态，可移动且可自动攻击；`DEVOURING` 由双击吞噬触发，期间玩家冲刺至目标并开启短暂无敌；`CRUSHING` 由 UI 粉碎触发，用于承载短暂 Buff 动画或表现窗口。

## 技能队列规则

技能队列最大长度为 3。吞噬敌人时会读取敌人的 `SkillPayload`。若队列未满，则追加到末尾并刷新 UI；若队列已满，则队列保持不变，转而发射 `OverchargeProjectile`。这严格对应 GDD 中的“常规吸取”和“满载过载”。

## 自动攻击规则

自动攻击以 `auto_attack_interval` 为周期运行，玩家会在 `target_detection_radius` 内寻找最近敌人。当前 MVP 采用直接伤害结算并打印日志。元素混合采用无视顺序的纯堆叠模式，队列中所有不重复元素会作为本次攻击的元素列表传入敌人伤害接口。

## 关卡状态机

`Main.gd` 中的 `LevelState` 包含 `SCROLLING`、`ARENA_LOCK` 与 `UNLOCK`。推进期相机会跟随玩家；当玩家越过 `arena_trigger_y` 时，相机锁定并刷出两排敌人；当锁屏战敌人全部死亡时进入解锁状态，短暂延迟后生成下一段走廊并恢复推进。

## 扩展建议

后续建议把敌人与技能从脚本硬编码迁移到 `Resource` 配置表，例如 `EnemyDefinition` 与 `SkillDefinition`。这样可以在不改代码的情况下配置敌人波次、元素组合、粉碎收益、投射物表现与数值曲线。移动端正式开发时，还应加入输入区域遮罩、屏幕安全区适配、对象池与导出预设。
'''
}

for relative_path, content in files.items():
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + '\n', encoding='utf-8')

print(f'Created {len(files)} files under {ROOT}')
for path in sorted(ROOT.rglob('*')):
    if path.is_file():
        print(path.relative_to(ROOT))
