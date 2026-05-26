class_name Player
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
	status_label.text = "HP %d/%d\n%s\nQueue %d/3" % [int(current_health), int(max_health), state_text, skill_queue.size()]

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
