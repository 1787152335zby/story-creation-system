# Tasks

- [x] Task 1: 修复后端 asset-library 端点，新增道具扫描
  - [x] 在 [projects.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/server/routes/projects.py#L901-L939) 的 `get_project_asset_library()` 中，参考 characters/scenes 的遍历逻辑，新增对 `07_生成素材/道具/` 目录的扫描
  - [x] 将扫描结果写入 `result["props"]`，结构与 `characters` 和 `scenes` 一致
  - [x] 验证：调用 `/api/projects/{name}/asset-library` 返回的 JSON 中包含 `props` 字段

- [x] Task 2: VideoProjectPanel 新增道具选择 UI
  - [x] 在 [VideoProjectPanel.tsx](file:///e:/AI/Trae CN/book/story-creation-system1.2/src/components/VideoProjectPanel.tsx) 中新增 `propsList` state、`selectedProp` state
  - [x] 新增 `fetchProps` 调用（在 `useEffect` 的 `Promise.all` 中添加）
  - [x] 在角色和场景选择区下方新增道具勾选区域（UI 参照 ProjectImageGenForm 的道具区）
  - [x] 道具为空时显示"暂无道具数据，点击「视觉提取」获取"提示

- [x] Task 3: ImageGenPage 项目模式新增视觉提取按钮
  - [x] 在 [ImageGenPage.tsx](file:///e:/AI/Trae CN/book/story-creation-system1.2/src/pages/ImageGenPage.tsx) 中新增 `extracting` state 和 `extractLog` state
  - [x] 新增 `handleExtract` 函数，调用 `/api/projects/{name}/re-extract-visual`
  - [x] 当 `characters` 和 `scenes` 均为空数组时，在项目选择区显示"🔄 视觉提取"按钮
  - [x] 提取完成后自动调用 `fetchCharacters/fetchScenes/fetchProps` 刷新数据

# Task Dependencies
- Task 1, Task 2, Task 3 相互独立，可以并行处理
