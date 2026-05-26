class_name SkillPayload
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
