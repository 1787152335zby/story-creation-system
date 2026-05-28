# Checklist

- [x] 短剧管线从7阶段缩减为6阶段（视觉提取仅小说运行）
- [x] 新管线语法运行不出错
- [x] 小说/网文模式不受影响（阶段4视觉提取正常）
- [x] `06_生图需求/生图清单.json` 包含完整的角色+场景+提示词
- [x] 生图 UI 正确加载新路径的生图清单（fallback 兼容旧 `07_` 路径）
- [x] `🔄 分析需求` 按钮仍然可用（改为调 `ImagePreparator`）
- [x] 旧项目兼容（已有 `07_生图需求/` 的旧项目仍可通过 fallback 读取）
- [x] 前端工作区/首页/时间线显示正确的6阶段
- [x] `prompt_factory.py` 仍可作为工具类被生图 API 调用
- [x] `image_demand_analyzer.py` 保留，`re-analyze-demands` 不再引用
