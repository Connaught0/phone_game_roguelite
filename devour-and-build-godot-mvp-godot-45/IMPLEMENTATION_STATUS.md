# Devour & Build Godot MVP 交付说明

本次交付已经基于你提供的核心战斗系统设计文档，创建了一个可由 Godot 4.x 打开的白盒 MVP 工程。工程重点验证玩法闭环，而非最终美术表现。

## 已完成范围

| 阶段 | 完成内容 | 主要文件 |
| --- | --- | --- |
| Phase 1 | 基础玩家控制器、触屏/鼠标拖拽移动、WASD 调试移动、索敌半径、自动攻击日志与伤害结算 | `scripts/Player.gd`, `scenes/Player.tscn` |
| Phase 2 | 三格技能队列、双击吞噬、敌人载荷读取、UI 队列刷新、点击槽位粉碎并获得 Buff | `scripts/Player.gd`, `scripts/SkillQueueUI.gd`, `ui/SkillQueueUI.tscn` |
| Phase 3 | 队列满载时触发吐星星机制，生成高速贯穿投射物并附带元素伤害 | `scripts/OverchargeProjectile.gd`, `scenes/OverchargeProjectile.tscn` |
| Phase 4 | 推进期、锁屏战、两排敌人刷怪、清场解锁、相机跟随与锁定 | `scripts/Main.gd`, `scenes/Main.tscn` |

## 运行方式

请使用 **Godot 4.2 或更高版本** 打开项目根目录中的 `project.godot`，主场景已经配置为 `res://scenes/Main.tscn`。运行后可使用屏幕中/右侧拖拽或桌面端 WASD 控制玩家，快速双击吞噬索敌半径内最近敌人，点击左下 1 至 3 号槽位粉碎技能。

## 验证结果

沙盒环境未预装 Godot 可执行文件，因此未执行引擎内运行测试。本次已完成静态工程验证，检查项目必需文件、`res://` 资源引用、场景属性常见拼写错误与核心实现标记，结果为：`VALIDATION PASSED`。

## 推荐下一步

建议下一步在本地 Godot 编辑器中打开工程并进行一次真实运行测试。若确认核心循环可用，后续可以继续推进敌人 AI、对象池、元素状态效果、移动边界、数值配置表、移动端安全区 UI 适配与导出预设。
