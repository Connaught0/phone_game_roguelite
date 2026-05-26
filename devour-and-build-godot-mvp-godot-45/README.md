# Devour & Build Godot MVP

本项目是《Devour & Build（吞噬与构筑）》核心战斗循环的 **Godot 4 白盒 MVP**。当前实现目标不是美术成品，而是验证核心闭环：**WASD 移动、自动索敌攻击、空格吞噬、三格技能队列、满载吐星星、数字键粉碎、锁屏战状态机**。

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

当前版本采用 **PC 原型版操作**。玩家使用 **WASD** 移动，靠近敌人后会自动索敌攻击；当敌人进入可吞噬状态后，按 **空格键** 吞噬最近的可吞噬敌人；技能队列中的 1 至 3 号槽位可用 **数字键 1/2/3** 粉碎并获得对应 Buff。UI 槽位仍保留鼠标点击，便于调试。

## 当前已实现的 GDD 对照

| GDD 模块 | MVP 实现状态 | 关键文件 |
| --- | --- | --- |
| 玩家基础属性与状态机 | 已实现 `IDLE_MOVING / DEVOURING / CRUSHING` | `scripts/Player.gd` |
| 敌人标签与技能载荷 | 已实现 `ElementTag / ActionType / CrushReward` | `scripts/Enemy.gd`, `scripts/SkillPayload.gd` |
| PC 键盘移动 | 已实现 WASD 移动，松键后停止 | `scripts/Player.gd` |
| 空格吞噬 | 已实现最近目标检测、冲刺、销毁与结算 | `scripts/Player.gd` |
| UI 技能队列 | 已实现 3 槽队列、数字键粉碎与点击粉碎 | `ui/SkillQueueUI.tscn`, `scripts/SkillQueueUI.gd` |
| 自动攻击 | 已实现定时索敌、元素叠加、伤害打印 | `scripts/Player.gd` |
| 满载吐星星 | 已实现贯穿投射物与元素伤害 | `scripts/OverchargeProjectile.gd` |
| 关卡推进/锁屏战 | 已实现推进、触发锁屏、刷两排怪、清场解锁 | `scripts/Main.gd` |

## 建议测试路径

运行后先用 WASD 靠近走廊敌人，观察控制台中的 `Auto attack` 日志。敌人被打到可吞噬状态后，按空格键吞噬最近的可吞噬敌人，左下 UI 会加入元素技能。按数字键 1/2/3 可以粉碎对应技能槽；队列满 3 格后继续按空格吞噬敌人，会触发高速贯穿投射物，即当前的“吐星星”机制。移动到更靠上的区域后会进入 `ARENA_LOCK`，场景刷出两排敌人，清空后恢复推进状态。

## 下一步建议

当前版本已经完成系统闭环。下一阶段可以把白盒表现升级为可感知的战斗反馈，包括吞噬冲刺残影、投射物特效、元素状态视觉化、敌人基础 AI、移动边界与受击反馈。待手感确认后，再进入数值表、关卡波次配置与移动端导出配置。
