# Workspace 交互流畅性重构

## 问题

当前 Workspace 在逐集生成时，用户点击侧边栏查看已完成内容会导致严重卡顿，原因是 `suppressStream` 状态变量控制条件渲染，每次切换会完整卸载/挂载包含 ReactMarkdown 的大组件树。

具体问题清单：
1. 点击侧边栏卡顿（DOM 树卸载+重挂载）
2. 查看历史时完全看不到生成进度
3. 逐集生成时侧边栏无进度显示
4. 30 个本地状态 + 29 个 WS 状态互相联锁
5. streamContent 的 4 个 useEffect 级联执行

## 方案

### 原则
- 只改前端 Workspace.tsx 和 PhaseTimeline.tsx
- 不动后端和 WebSocket 协议
- 用 CSS display 替代条件渲染，不卸载组件

### 改动

1. **删除 `suppressStream`，改为 `viewMode: 'stream' | 'history'`**
   - 流式区域和历史区域始终挂载，CSS 控制显隐
   - 切换不触发 un/mount，消除卡顿

2. **viewMode='history' 时，流式区折叠为顶部迷你进度条**
   - 显示"剧本第5集正在生成…1284字"
   - 点进度条可切回流式视图

3. **PhaseTimeline 侧边栏显示逐集进度**
   - 复用现有 `chunksCompleted` 数据
   - 展开阶段时显示各集状态（已完成/生成中/待生成）

4. **streamContent 的 useEffect 加防抖**
   - useRef 记录上次更新时间，300ms 内不重复触发

5. **生成中点击侧边栏直接 HTTP 加载文件**
   - 不依赖状态同步，秒开已完成内容

### 不改的部分
- 所有 API 路由
- WebSocket 消息协议
- 后端 async_orch.py
- 审批/版本选择逻辑
