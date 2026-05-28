# Tasks

- [x] Task 1: 后端 — 生成参数元数据持久化
  - [x] 修改 `free_image_gen` 和 `project_image_gen`，生成后在 `generated/_meta/<filename>.json` 写入元数据
  - [x] 元数据包含：prompt、negative_prompt、model、size、reference_urls、timestamp、mode
  - [x] 项目模式额外包含：project_name、character_names、scene_names、version

- [x] Task 2: 后端 — 历史 API 增强 + 参考图上传
  - [x] `GET /api/generated-history` 返回时附带每张图的元数据
  - [x] 新增 `GET /api/generated-history/{filename}` 返回单条完整元数据
  - [x] 新增 `POST /api/upload-reference` 接收图片文件，保存到 `generated/_refs/`，返回 URL

- [x] Task 3: 前端 — 自由模式参考图 UI
  - [x] FreeImageGenForm 增加参考图区域：拖拽上传 / 文件选择 / URL 粘贴
  - [x] 参考图列表显示缩略图，可删除
  - [x] 生成请求中携带 reference_urls

- [x] Task 4: 前端 — 历史展示增强 + 画同款
  - [x] 历史区域改为卡片布局，显示 prompt 摘要、模型、尺寸、时间
  - [x] 每张卡片增加「画同款」按钮 → 获取元数据 → 回填表单
  - [x] 回填包括参考图，自动加载到预览区

# Task Dependencies

- [Task 1] → [Task 2]
- [Task 3] 独立
- [Task 2] + [Task 3] → [Task 4]
