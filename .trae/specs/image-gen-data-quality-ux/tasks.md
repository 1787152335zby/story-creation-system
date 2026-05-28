# Tasks

- [x] Task 1: 场景提取 prompt 增加关联关系指引
  - [x] `SEGMENT_EXTRACT_PROMPT` scenes 示例 JSON 增加 `parent_scene` 字段
  - [x] 提示词末尾增加场景关联规则说明
  - [x] `extract_all` 场景合并时保留 `parent_scene`

- [x] Task 2: 道具保存时去重
  - [x] `_save_to_files` 保存前根据名称包含关系去重
  - [x] 保留 `appearance` 更详细的版本
  - [x] 同步更新场景 `props` 数组引用

- [x] Task 3: 移除场景提示词默认视角
  - [x] `generate_scene_prompt` angle 参数默认值改为 `""`
  - [x] angle 为空时不输出视角描述

- [x] Task 4: 道具提示词增加外观细节
  - [x] `appearance` 为空时 fallback 到 `description`

- [x] Task 5: 角色/场景树折叠展开
  - [x] 移除未使用的 `renderCharTree`/`renderSceneTree` 死代码
  - [x] 内联树渲染已支持折叠/展开（ChevronDown/ChevronRight）

- [x] Task 6: 新增自由参考图模式
  - [x] 新增 `generalRefUrls`/`generalRefEnabled` state
  - [x] 新增"🖼️ 通用"toggle 按钮 + 上传区
  - [x] 所有生成路径合并 `generalRefUrls` 到参考图

- [x] Task 7: 修复项目历史不显示
  - [x] 全部 `setHistoryProject(h.images_project)` 改为 `setHistoryProject(h?.images_project || [])`
  - [x] ImageGenPage.tsx 中相同修复（2处）

- [x] Task 8: 修复勾选框和图片预览交互
  - [x] 已确认 `toggleChar`/`toggleScene`/`toggleProp` 均正确绑定 `onClick` 且使用 `e.stopPropagation`
  - [x] 自由参考图缩略图支持删除

# Task Dependencies
- Task 1, 2, 3, 4 是后端修改，相互独立
- Task 5, 6, 7, 8 是前端修改，相互独立
