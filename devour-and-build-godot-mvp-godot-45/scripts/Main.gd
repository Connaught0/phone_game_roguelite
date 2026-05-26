extends Node2D

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
	state_label.text = "Level: %s\nArena trigger Y: %d" % [level_state_text, int(arena_trigger_y)]
