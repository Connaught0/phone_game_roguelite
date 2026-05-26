class_name Enemy
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
