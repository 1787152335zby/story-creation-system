# 角色形象分组与变体识别 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生图需求清单按 `character_base` 分组展示，伪角色自动归并，一键生成分两步执行。

**Architecture:** 后端 `image_preparator.py` 在分镜解析阶段追加伪角色归并逻辑并输出 `character_groups` 字段；`projects.py` API 返回该字段；前端 `ProjectImageGenForm.tsx` 读 `character_groups` 渲染分组清单、拆分一键生成为两步。

**Tech Stack:** Python 3.12 (FastAPI), TypeScript/React

---

### Task 1: `image_preparator.py` — 伪角色归并 + `character_groups` 输出

**Files:**
- Modify: `agents/image_preparator.py`

#### Step 1: 在 `prepare()` 中添加伪角色归并函数

在 `prepare()` 方法开头（`def prepare` 之后，`storyboard_dir` 之前）插入伪角色归并辅助函数。同时在第49-50行收集角色时插入归并逻辑。

**读现有代码确认位置** `agents/image_preparator.py:22-61`，找到：

```python
    def prepare(self, project: ProjectManager, style: StyleConfig = None) -> dict:
        storyboard_dir = project.project_dir / "05_分镜脚本"
```

在第22行 `def prepare` 下插入 `_normalize_char_name` 方法：

```python
    PSEUDO_MARKERS = {
        '地上', '画中', '画面中', '画面内', '画外', '画外音',
        '远景', '近景', '中景', '特写', '背面', '正面', '侧面',
        '仰视', '俯视',
    }

    def _normalize_char_name(self, raw: str, known_bases: set) -> str:
        cleaned = re.sub(r'[（）()""''「」\[\]【】\s]', '', raw)
        for base in known_bases:
            base_clean = re.sub(r'[（）()""''「」\[\]【】\s]', '', base)
            if cleaned == base_clean:
                return base
            if cleaned.startswith(base_clean) and len(cleaned) > len(base_clean):
                rest = cleaned[len(base_clean):]
                if all(m in self.PSEUDO_MARKERS for m in re.findall(r'[\u4e00-\u9fff]+', rest)):
                    return base
        return raw
```

#### Step 2: 在角色收集循环中应用归并

修改第49-60行的角色收集逻辑：

```python
            for shot in shots:
                shot_counter += 1
                for char_name in shot.get("characters", []):
                    if char_name in ('无', '无人', '无角色', '空', '-', '—'):
                        continue
                    if char_name not in all_char_states:
                        known = set(all_char_states.keys())
                        normalized = self._normalize_char_name(char_name, known)
                        if normalized != char_name and normalized in all_char_states:
                            char_name = normalized
                    if char_name not in all_char_states:
                        all_char_states[char_name] = {
                            "name": char_name,
                            "shot_indices": [],
                            "episodes": [],
                        }
                    all_char_states[char_name]["shot_indices"].append(shot_counter)
                    if ep_name not in all_char_states[char_name]["episodes"]:
                        all_char_states[char_name]["episodes"].append(ep_name)
```

#### Step 3: 在 `prepare()` 末尾输出 `character_groups`

在第86-97行原有 `result` 构建处追加 `character_groups`：

```python
        character_groups = []
        group_map = {}
        for c in characters:
            base_name = c.get("character_base", c["name"])
            if base_name not in group_map:
                group_map[base_name] = {"name": base_name, "total_shots": 0, "members": []}
            member = {
                "name": c["name"],
                "is_base": c.get("is_base", True),
                "shots": len(c.get("shot_indices", [])),
                "variant_name": c.get("variant_name", "基础形象" if c.get("is_base", True) else c.get("variant_name", "")),
            }
            group_map[base_name]["members"].append(member)
        for gn, g in group_map.items():
            g["total_shots"] = max(m["shots"] for m in g["members"]) if g["members"] else 0
            g["members"].sort(key=lambda m: (0 if m["is_base"] else 1, m["name"]))
            character_groups.append(g)
        character_groups.sort(key=lambda g: g["name"])

        result = {
            "characters": characters,
            "character_groups": character_groups,
            "scenes": scenes,
            "key_props": key_props,
            "total_shots": shot_counter,
            "episodes": all_episodes,
        }
```

#### Step 4: 验证 Python 语法

Run: `python -c "import py_compile; py_compile.compile(r'e:\AI\Trae CN\book\story-creation-system1.2\agents\image_preparator.py', doraise=True); print('OK')"`

Expected: `OK`

#### Step 5: 重启后端 + 重新分析测试61

```bash
$pythonPath run_web.py  # 重启
```

然后调 API 验证：

```powershell
$uri = 'http://localhost:8000/api/projects/' + [uri]::EscapeDataString('测试61') + '/re-analyze-demands'
Invoke-RestMethod $uri -Method Post
```

Expected: `characters=7 scenes=14 shots=143`（7含变体但无伪角色，伪角色已归并到基础角色）

---

### Task 2: `projects.py` — `get_image_demands` 返回 `character_groups`

**Files:**
- Modify: `server/routes/projects.py:290-305`

#### Step 1: 修改 `get_image_demands`

在返回 data 前增加分组构建：

```python
@router.get("/projects/{name}/image-demands")
def get_image_demands(name: str):
    project_dir = PROJECTS_DIR / name
    demand_file = project_dir / "06_生图需求" / "生图清单.json"
    if not demand_file.exists():
        demand_file = project_dir / "07_生图需求" / "生图清单.json"
    if demand_file.exists():
        data = json.loads(demand_file.read_text(encoding="utf-8"))
        confirmed_file = demand_file.parent / "_confirmed.json"
        if confirmed_file.exists():
            try:
                data["_confirmed"] = json.loads(confirmed_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return data
    return {"characters": [], "scenes": [], "key_props": [], "total_shots": 0, "episodes": [], "character_groups": []}
```

**注意**：API 本身已直接返回 `data`（`生图清单.json` 的完整内容），所以 `character_groups` 已经包含在内，无需额外构建。只需在 fallback 返回中补齐 `character_groups: []` 即可。

#### Step 2: 验证语法

Run: `python -c "import py_compile; py_compile.compile(r'e:\AI\Trae CN\book\story-creation-system1.2\server\routes\projects.py', doraise=True); print('OK')"`

Expected: `OK`

---

### Task 3: `ProjectImageGenForm.tsx` — 分组渲染生图需求清单

**Files:**
- Modify: `src/components/ProjectImageGenForm.tsx`

#### Step 1: 修改 `imageDemands` 标准化逻辑，追加 `character_groups` 标准化

在 `useEffect`（L215-238）中追加：

```typescript
        if (data && !data._normalized) {
          data.characters = (data.characters || []).map((c: any) => ({
            ...c,
            shots: (c.shot_indices || []).map((si: number, idx: number) => ({
              shot_id: si,
              episode: c.episodes ? c.episodes[Math.min(idx, (c.episodes.length - 1) || 0)] : '',
            }))
          }))
          data.scenes = (data.scenes || []).map((s: any) => ({ /* ...existing... */ }))
          if (data.character_groups) {
            data.character_groups = data.character_groups.map((g: any) => ({
              ...g,
              members: (g.members || []).map((m: any) => ({
                ...m,
                shots: m.shots,
              }))
            }))
          }
          data._normalized = true
        }
```

#### Step 2: 替换生图需求清单角色渲染（L540-565 原有平铺角色部分）

把整个 `(imageDemands.characters || []).map(...)` 角色循环替换为分组渲染：

```tsx
                    {(imageDemands.character_groups || []).map((group: any) => {
                      const expanded = expandedDemandChars[group.name]
                      const members = group.members || []
                      const baseConfirmed = imageDemands._confirmed && imageDemands._confirmed[group.name]
                      return (
                        <div key={group.name}>
                          <div onClick={() => setExpandedDemandChars(prev => ({ ...prev, [group.name]: !prev[group.name] }))}
                            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer text-[11px] hover:bg-muted text-muted-foreground transition-all">
                            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                            <span className="truncate">{group.name}</span>
                            <span className="text-[9px] bg-primary/10 text-primary/70 px-1.5 py-0.5 rounded-full ml-auto flex-shrink-0">{group.total_shots} 镜头</span>
                          </div>
                          {expanded && members.map((member: any) => {
                            const isConfirmed = imageDemands._confirmed && imageDemands._confirmed[member.name]
                            const isVariant = !member.is_base
                            return (
                              <div key={member.name} className={`ml-4 flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] ${isConfirmed ? 'bg-green-500/5' : ''} ${isVariant && !isConfirmed ? 'text-muted-foreground/40' : 'text-muted-foreground/70'} border-b border-border/10 last:border-b-0`}>
                                {member.is_base ? <span className="text-[10px]">👤</span> : <span className="text-[10px]">🔄</span>}
                                <span>{member.variant_name || member.name}</span>
                                <span className="text-[9px] bg-primary/10 text-primary/70 px-1 py-0 rounded-full ml-auto">{member.shots} 镜</span>
                                {isConfirmed && <span className="text-green-400 text-[9px]" title="已确认">✓</span>}
                                {isVariant && !isConfirmed && <span className="text-amber-400 text-[9px]" title="需基础形象确认后生成">⚠</span>}
                              </div>
                            )
                          })}
                        </div>
                      )
                    })}
```

#### Step 3: 修改一键生成所有角色按钮（L645-677）

把原有的单按钮替换为两步按钮：

```tsx
              {charTree.length > 0 && (
                <div className="space-y-1 mt-2">
                  <button onClick={async () => {
                    const groups = imageDemands?.character_groups || []
                    const bases = groups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base))
                    const names = bases.length > 0 ? bases.map((m: any) => m.name) : charTree.map(c => c.name)
                    if (names.length === 0) return
                    setProjectGenerating(true)
                    let idx = 0
                    for (const name of names) {
                      idx++
                      setGeneratingStatus(`基础形象 ${idx}/${names.length}: ${name}`)
                      try {
                        await projectDemandBatchGen({
                          project_name: selectedProject,
                          prompt: projectPrompt,
                          negative_prompt: projectNegative,
                          size: projectSize,
                          n: 1,
                          model: projectModel,
                          character_names: [name],
                          scene_names: [],
                          reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                          reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
                        })
                      } catch {}
                    }
                    fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                    fetchProjectImages(selectedProject).then(setGeneratedImages)
                    setProjectGenerating(false)
                    setGeneratingStatus('')
                  }} disabled={projectGenerating}
                    className="w-full px-3 py-2 rounded-lg text-[10px] border border-primary/20 text-primary/70 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-40">
                    ⚡ 第一步：生成所有基础形象 ({(() => {
                      const groups = imageDemands?.character_groups || []
                      const bases = groups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base))
                      return bases.length || charTree.length
                    })()}个)
                  </button>
                  <button onClick={async () => {
                    const groups = imageDemands?.character_groups || []
                    const variants = groups.flatMap((g: any) => (g.members || []).filter((m: any) => !m.is_base))
                    const names = variants.map((m: any) => m.name)
                    if (names.length === 0) return
                    setProjectGenerating(true)
                    let idx = 0
                    for (const name of names) {
                      idx++
                      setGeneratingStatus(`变体 ${idx}/${names.length}: ${name}`)
                      try {
                        await projectDemandBatchGen({
                          project_name: selectedProject,
                          prompt: projectPrompt,
                          negative_prompt: projectNegative,
                          size: projectSize,
                          n: 1,
                          model: projectModel,
                          character_names: [name],
                          scene_names: [],
                          reference_urls: [...autoRefUrls, ...manualRefUrls, ...generalRefUrls],
                          reference_urls_by_type: autoRefUrlsByType || ({} as ReferenceUrlsByType),
                        })
                      } catch {}
                    }
                    fetchGenerationHistory().then(h => setHistoryProject(h?.images_project || []))
                    fetchProjectImages(selectedProject).then(setGeneratedImages)
                    setProjectGenerating(false)
                    setGeneratingStatus('')
                  }} disabled={projectGenerating || (() => {
                    const groups = imageDemands?.character_groups || []
                    const bases = groups.flatMap((g: any) => (g.members || []).filter((m: any) => m.is_base))
                    return bases.some((m: any) => !(imageDemands?._confirmed && imageDemands._confirmed[m.name]))
                  })()}
                    className="w-full px-3 py-2 rounded-lg text-[10px] border border-border/30 text-muted-foreground/40 hover:bg-muted/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                    ⚡ 第二步：生成所有变体 ({(() => {
                      const groups = imageDemands?.character_groups || []
                      const variants = groups.flatMap((g: any) => (g.members || []).filter((m: any) => !m.is_base))
                      return variants.length
                    })()}个)
                  </button>
                </div>
              )}
```

#### Step 4: 构建验证

```bash
npm run build
```

Expected: 构建成功，无 TS/JS 错误。

---

### Task 4: 重启 + 验收

#### Step 1: 重启所有服务

```powershell
# Kill 8000 and 5173
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Start-Sleep -Seconds 1

# Start backend
& $pythonPath run_web.py  (background)

# Start frontend
npm run dev  (background)
```

#### Step 2: 验收检查项

| # | 检查点 | 方法 |
|---|--------|------|
| 1 | 测试61 生图清单 3 组（林深/苏晚/系统盖亚） | 前端切换项目模式，看清单 |
| 2 | 林深组展开显示基础+受伤 | 点开林深组 |
| 3 | 一键生成按钮显示「第一步：生成所有基础形象 (N个)」 | 看按钮文字 |
| 4 | 第二步灰显直到基础全确认 | 检查 disabled 状态 |
| 5 | 伪角色不出现在清单中 | 检查无"地上的林深""林深（画面中）"等条目 |

---

### 文件清单

| 文件 | 改动类型 | 要点 |
|------|---------|------|
| `agents/image_preparator.py` | Modify | `_normalize_char_name` 方法 + `prepare()` 角色收集循环 + `character_groups` 输出 |
| `server/routes/projects.py` | Modify | Fallback 返回补齐 `character_groups: []` |
| `src/components/ProjectImageGenForm.tsx` | Modify | 分组渲染 + 两步按钮 |
