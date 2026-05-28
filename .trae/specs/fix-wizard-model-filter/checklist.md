# 验证清单

## Task 1: 后端 active_llm_source
- [x] 有活跃 LLM 聚合配置时返回 `{type: "aggregated", name, base_url}`
- [x] 无活跃 LLM 聚合配置时返回 `{type: "official", backend}`

## Task 2: 前端过滤
- [x] 官方 API 只显示对应提供商模型
- [x] 聚合平台只显示该平台模型

## Task 3: 构建验证
- [x] Python 语法验证通过
- [x] 前端构建成功
- [x] 服务器重启成功
