# Checklist

- [x] `/api/projects/{name}/asset-library` 端点返回包含 `props` 字段
- [x] `props` 字段结构与 `characters`/`scenes` 一致（confirmed_versions, all_versions, latest_confirmed）
- [x] 项目无道具素材时 `props` 返回空对象而非缺失字段
- [x] VideoProjectPanel 在角色/场景选择区下方有道具勾选 UI
- [x] VideoProjectPanel 道具为空时显示"点击「视觉提取」获取"提示（而非什么都不显示）
- [x] VideoProjectPanel 道具选择可与角色/场景一样正常勾选/取消
- [x] ImageGenPage 项目模式在数据为空时显示"视觉提取"按钮
- [x] 点击视觉提取按钮后能正常调用后端接口并刷新数据
- [x] 生图自由模式不受影响（回归验证）
- [x] 视频自由模式不受影响（回归验证）
