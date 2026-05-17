# 系统审查文档

> 创建日期：2026-06-11
> 目的：记录系统审查发现的问题和改进方案，按优先级推进修复

## 一、配置系统割裂（架构问题）

### 现状

两套配置系统并行：

| 存储 | 存什么 | 读取方式 |
|:-----|:-------|:---------|
| `.env` | DeepSeek/OpenAI/Claude Key、聚合平台旧配置 | `os.getenv()` |
| `aggregated_configs.json` | 聚合平台配置、追加的官网 Key | `_read_agg_configs()` |

### 具体问题

1. `gen.py` 中 `_call_seedream()` 直接读 `SEEDANCE_API_KEY`（`.env`），不读 JSON
2. `free_image_gen` 读 `_get_active_agg_config("image")`（JSON），不读 `.env`
3. 设置页主卡片 Key 存 `.env`，追加 Key 存 JSON，**互不知道对方存在**
4. 追加的官网 Key 只存在数据里，没有任何生成接口会用到它们

### 修复目标

- 所有生成入口统一读 `_get_active_agg_config(type)`
- 追加的官网 Key 能真正用于生成
- 逐步淘汰 `.env` 中的 API Key

### 涉及文件

- `server/routes/gen.py`
- `server/routes/settings.py`
- `server/app.py`（迁移逻辑）
- `src/pages/SettingsPage.tsx`（追加 Key 的使用按钮）

---

## 二、前端无用户反馈系统

### 现状

全站没有任何 Toast/通知组件，错误仅 `console.error`。

```typescript
// HomePage.tsx L24
catch (e) { console.error(e) }  // 用户看不到
```

### 具体位置

| 文件 | 位置 | 问题 |
|:-----|:-----|:------|
| `src/pages/HomePage.tsx` | L24 | 加载项目失败静默 |
| `src/pages/Workspace.tsx` | 多处 | 操作失败静默 |
| `src/pages/ImageGenPage.tsx` | 多处 | 生图失败静默 |
| `src/pages/VideoGenPage.tsx` | 多处 | 视频生成失败静默 |
| `src/components/ModelSelector.tsx` | catch | 模型加载失败静默 |

### 修复目标

- 创建通用 Toast 组件
- 替换所有 `console.error` 为用户可见通知
- 提供成功/失败/加载中和已设置状态

### 参考实现

```tsx
// 轻量级 Toast，无需第三方库
function Toast({ message, type }: { message: string; type: 'success' | 'error' | 'info' }) {
  // 自动消失，可叠加多条
}
```

---

## 三、追加的官网 Key 无法用于生成

### 现状

设置页「+ 添加官网 API」添加的 Key 通过 `createProviderConfig` 存入 JSON，但：

1. 没有生成接口读取 `type === "provider"` 的配置
2. `gen.py` 只读 `type === "llm"/"image"/"video"` 的配置

### 修复目标

- `setActive` 存 `provider_config` 时，也写一份到聚合配置里（`type: "llm"/"image"/"video"`）
- 或者 `_get_active_agg_config` 同时检查 `type === "provider"` 中激活的那个

---

## 四、图片/视频页与设置页联动缺失

### 现状

- `ImageGenPage.tsx` 有自己的 `ModelSelector`，但**没读设置页选中的配置**
- `VideoGenPage.tsx` 同理
- 用户在设置页选了 DeepSeek+聚合，到图片页还是默认配置

### 修复目标

- 生成页从后端 `/api/settings` 读取当前选中的 backend + model
- 默认选中设置页的配置，用户仍可手动切换

---

## 五、无 Error Boundary

### 现状

如果 `/api/settings/models` 报错，整个设置页白屏。React 默认无错误边界。

### 需要 Error Boundary 的位置

- `SettingsPage.tsx`
- `Workspace.tsx`
- `ImageGenPage.tsx` / `VideoGenPage.tsx`
- `HomePage.tsx`

---

## 六、TypeScript 类型不严格

### 现状

```typescript
const [aggConfigs, setAggConfigs] = useState<any[]>([])
const [providerConfigMap, setProviderConfigMap] = useState<Record<string, any[]>>({})
```

### 影响

- 失去 IDE 自动补全
- 运行时可能访问不存在的字段
- 重构时无法靠类型系统发现问题

### 修复目标

为 `AggregatedConfig` 和 `ProviderConfig` 定义明确的 interface。

---

## 七、Workspace.tsx 过于庞大

### 现状

单个文件数百行，20+ 状态变量，逻辑非常集中。

### 建议拆分

- `PhasePanel.tsx` — 单个阶段的展示
- `PhaseTimeline.tsx` — 阶段时间线
- `ContentEditor.tsx` — markdown 编辑/预览
- `FeedbackInput.tsx` — 反馈输入
- `TemplateModal.tsx` — 模板保存弹窗

---

## 八、后续规划（低优先级）

- 图片/视频生成加入队列系统，避免并发
- 生图/视频的历史记录
- 多语言支持
- 迁移到 pnpm
