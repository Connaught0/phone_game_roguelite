class_name OverchargeProjectile
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
