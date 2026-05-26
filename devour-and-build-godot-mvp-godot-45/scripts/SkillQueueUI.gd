extends CanvasLayer

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
	help_label.text = "WASD 移动 / 空格吞噬\n数字键 1/2/3 粉碎技能槽"

func refresh_queue(queue: Array) -> void:
	for i in range(slots.size()):
		var button: Button = slots[i]
		if i < queue.size():
			var payload: SkillPayload = queue[i]
			button.text = "%d\n%s\n%s" % [i + 1, payload.element, payload.crush_reward]
			button.disabled = false
			button.modulate = _element_color(payload.element)
		else:
			button.text = "%d\n空" % [i + 1]
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
