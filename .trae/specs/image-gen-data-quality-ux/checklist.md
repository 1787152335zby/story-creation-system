# Checklist

### 数据层
- [x] 场景 JSON 包含 `parent_scene` 字段标识空间归属
- [x] 道具 JSON 无重复项（去重逻辑在 `_save_to_files`）
- [x] 场景 JSON 中的 `props` 引用指向去重后的道具
- [x] 场景提示词不再默认拼接"正面视角，从正前方观看"（angle 默认 ""）
- [x] 道具提示词包含明确的外观描述（`appearance` 空时 fallback `description`）

### 生图项目模式 UI
- [x] 角色列表显示折叠图标 `▸`/`▾`，变体子列表默认折叠
- [x] 场景列表同上
- [x] 存在"🖼️ 通用"参考图上传区，不强制分类
- [x] 勾选角色/场景/道具按钮正常响应（`e.stopPropagation` 正确使用）
- [x] 参考图缩略图可删除
- [x] 项目模式生成的图片出现在历史区（`h?.images_project || []` null-safe）
- [x] 视频模式不受影响（回归）
- [x] 自由生图模式不受影响（回归）
