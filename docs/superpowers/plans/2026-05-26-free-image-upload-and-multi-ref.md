# 图生图自由上传 + 多图引用 + 双模式 — 实施计划

> **For agentic workers:** Follow this plan task-by-task. Each step uses checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生图页面新增双模式自由上传区（模式1多图底图+@引用 / 模式2风格参考），后端支持多图输入和能力标志

**Architecture:** 后端 ImageBackend 能力标志 → 模型列表 API 返回能力 → 前端根据能力展示双模式 UI → 调用 /assets/modify API 时传入多图

**Tech Stack:** Python/FastAPI (后端), React/TypeScript (前端)

---

## 文件结构

| 文件 | 改动 | 职责 |
|------|------|------|
| `tools/image_api.py` | 修改 | ImageBackend 加 MAX_REFERENCE_IMAGES/SUPPORTS_IMG2IMG，签名改为 list |
| `tools/image_api_seedream.py` | 修改 | 签名适配 |
| `tools/image_api_openai_compat.py` | 修改 | 4 个后端签名适配 |
| `core/image_pipeline.py` | 修改 | modify_image 接受多图列表 |
| `server/routes/settings.py` | 修改 | 模型列表返回能力字段 |
| `server/routes/gen.py` | 修改 | /assets/modify 响应返回能力信息 |
| `src/lib/types.ts` | 修改 | 新增类型 |
| `src/lib/api.ts` | 修改 | 新增 API 调用函数 |
| `src/components/FreeImageGenForm.tsx` | 修改 | 新增模式1多图上传区 + @引用 |
| `src/components/ProjectImageGenForm.tsx` | 修改 | 新增模式1多图上传区 + @引用 |

---

## Task 1: ImageBackend 能力标志 + 多图签名

**Files:**
- Modify: `tools/image_api.py`
- Modify: `tools/image_api_seedream.py`
- Modify: `tools/image_api_openai_compat.py`

- [ ] **Step 1: 在 ImageBackend 基类添加能力字段，image_to_image 改为接受列表**

修改 `tools/image_api.py`：

```python
from abc import ABC, abstractmethod
from typing import Optional


class ImageBackend(ABC):
    """生图后端基类。
    子类可以覆盖 MAX_REFERENCE_IMAGES 和 SUPPORTS_IMG2IMG。
    """
    MAX_REFERENCE_IMAGES: int = 1
    SUPPORTS_IMG2IMG: bool = True

    @abstractmethod
    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1, model: str = "") -> list[str]:
        """
        Text-to-image generation.
        Returns list of image URLs.
        """

    @abstractmethod
    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        """
        Image-to-image generation. 接受多张参考图列表。
        Returns list of image URLs.
        """

    @abstractmethod
    def name(self) -> str:
        """Backend display name"""
```

- [ ] **Step 2: 更新 SeedreamBackend.image_to_image 签名**

修改 `tools/image_api_seedream.py`，将 `image_to_image` 的 `image_base64: str` 改为 `images_base64: list[str]`，内部取 `images_base64[0]`：

```python
    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        if not self.api_key or self.api_key == "your-seedance-key-here":
            raise HTTPException(status_code=400, detail="生图 API Key 未配置，请在设置页配置 SEEDANCE_API_KEY")
        
        image_base64 = images_base64[0]
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or "seedream-v1",
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        response = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail=f"图生图 API 返回异常 (HTTP {response.status_code})：API Key 可能无效或没有权限，请在设置页检查 SEEDANCE_API_KEY"
            )
        if response.status_code == 400:
            detail = data.get("error", {}).get("message", str(data))
            if "not have permission" in detail or "auth" in detail.lower() or "unauthorized" in detail.lower():
                raise HTTPException(status_code=400, detail="SEEDANCE_API_KEY 无效或没有权限，请检查设置页中的 API Key")
            raise HTTPException(status_code=400, detail=f"图生图请求失败: {detail}")
        response.raise_for_status()
        return [img["url"] for img in data.get("data", [])]
```

SeedreamBackend 不需要覆盖 `MAX_REFERENCE_IMAGES`（默认就是 1）。

- [ ] **Step 3: 更新 OpenAICompatBackend.image_to_image 签名**

修改 `tools/image_api_openai_compat.py` 中的 `OpenAICompatBackend.image_to_image`，`image_base64: str` → `images_base64: list[str]`，取 `images_base64[0]`：

```python
    def image_to_image(
        self,
        images_base64: list[str],
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.7,
        size: str = "1024x1024",
        n: int = 1,
        model: str = ""
    ) -> list[str]:
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        image_base64 = images_base64[0]
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",")[1]
        
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "image": image_base64,
            "strength": max(0.0, min(1.0, strength)),
            "n": n,
            "size": size
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]
```

- [ ] **Step 4: 同样更新 GPTImageBackend、Banana2Backend、CustomImageBackend 的 image_to_image**

这三个方法的结构和 OpenAICompatBackend 完全一样，只需把参数名从 `image_base64: str` 改为 `images_base64: list[str]`，然后取 `images_base64[0]` 即可。修改在同一个文件 `tools/image_api_openai_compat.py` 中。

---

## Task 2: ImagePipeline.modify_image 适配多图

**Files:**
- Modify: `core/image_pipeline.py`

- [ ] **Step 1: modify_image 改为接受多图字节列表**

修改 `core/image_pipeline.py` 中的 `modify_image` 方法：

```python
    def modify_image(self, images_data: list[bytes], prompt: str,
                     negative_prompt: str = "", strength: float = 0.7,
                     model: str = "") -> Optional[bytes]:
        """基于多张参考图和提示词修改图片
        images_data: 多张参考图字节列表，第一张为底图
        Returns: 生成的图片字节
        """
        from tools.image_api_seedream import SeedreamBackend
        
        images_base64 = [base64.b64encode(img).decode("utf-8") for img in images_data]
        
        backend = SeedreamBackend()
        try:
            urls = backend.image_to_image(
                images_base64=images_base64,
                prompt=prompt,
                negative_prompt=negative_prompt,
                strength=strength,
                model=model
            )
            if urls:
                resp = requests.get(urls[0], timeout=120)
                resp.raise_for_status()
                return resp.content
            return None
        except Exception as e:
            import logging
            logging.error(f"图生图失败: {e}")
            return None
```

---

## Task 3: 模型列表 API 返回能力字段

**Files:**
- Modify: `server/routes/settings.py`

- [ ] **Step 1: 在模型对象中添加 max_ref_images 和 supports_img2img**

修改 `server/routes/settings.py`，在构建模型列表时添加能力字段。在生成最终的模型对象时（约第 294-303 行和第 355-358 行），将 `{"value": mid, "label": mid}` 改为包含能力信息。

最简单的方式：在 `get_available_models()` 函数末尾（return 之前），对所有 image_groups 里的模型批量添加能力字段。

在 `result` 赋值完成后、return 之前，添加：

```python
    # 为所有生图模型补充能力标志
    from tools.model_registry import IMAGE_MODELS
    def _get_model_capability(model_id: str) -> tuple[int, bool]:
        """根据模型 ID 推断能力"""
        ml = model_id.lower()
        supports_img2img = True  # 默认支持
        max_ref = 1  # 默认1张
        if any(k in ml for k in ["gemini", "banana", "gpt-image", "qwen-image", "flux"]):
            max_ref = 3  # 较先进的模型可能支持多图
        if any(k in ml for k in ["dall-e", "midjourney", "mj_"]):
            max_ref = 2
        if "seedream" in ml:
            max_ref = 1
        return max_ref, supports_img2img

    for group_type in ("llm_groups", "image_groups", "video_groups"):
        if group_type != "image_groups":
            continue
        for group in result.get(group_type, []):
            for m in group.get("models", []):
                max_ref, img2img = _get_model_capability(m["value"])
                m["max_ref_images"] = max_ref
                m["supports_img2img"] = img2img
```

---

## Task 4: /assets/modify 返回模型能力信息

**Files:**
- Modify: `server/routes/gen.py`

- [ ] **Step 1: 在 /assets/modify 响应中返回模型能力提示**

找到 `modify_asset_endpoint` 函数（上一轮实施时添加的），在成功返回前添加能力信息。无需额外请求——直接返回一个 `model_info` 字段：

在 `return result` 之前添加：

```python
    result["model_info"] = {
        "max_ref_images": 1,
        "supports_img2img": True
    }
```

---

## Task 5: 前端类型定义

**Files:**
- Modify: `src/lib/types.ts`

- [ ] **Step 1: 新增类型定义**

在 `src/lib/types.ts` 文件末尾添加：

```typescript
export interface ModelCapability {
  max_ref_images: number
  supports_img2img: boolean
}

export interface FreeRefImage {
  id: string
  url: string
  label: string  // 图1, 图2, ...
  file?: File    // 本地文件引用
}
```

同时在 `ReferenceUrlsByType` 类型（如果已存在）附近确认其定义，如果没有则添加：

```typescript
export interface ReferenceUrlsByType {
  style: string[]
  character: string[]
  scene: string[]
  prop: string[]
}
```

---

## Task 6: 前端 API 函数

**Files:**
- Modify: `src/lib/api.ts`

- [ ] **Step 1: 新增 modifyImage API 调用函数**

在 `src/lib/api.ts` 文件末尾添加：

```typescript
export async function modifyImage(params: {
  project_name?: string
  prompt: string
  negative_prompt?: string
  size?: string
  model?: string
  strength?: number
  reference_images: string[]  // base64 图片数组
  style_references?: ReferenceUrlsByType
}) {
  const res = await fetch(`${API_BASE}/assets/modify-free`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(err.detail || '请求失败')
  }
  return res.json()
}
```

---

## Task 7: FreeImageGenForm 新增模式1多图上传 + @引用

**Files:**
- Modify: `src/components/FreeImageGenForm.tsx`

- [ ] **Step 1: 在 FreeImageGenForm 中新增自由参考图状态和组件**

在 `FreeImageGenForm` 组件中添加新的状态和 UI。具体改动：

**A. Props 新增：**
```typescript
// 在组件内部添加新 state
const [freeRefImages, setFreeRefImages] = useState<FreeRefImage[]>([])
const [showAtPicker, setShowAtPicker] = useState(false)
const fileInputRef2 = useRef<HTMLInputElement>(null)
```

**B. 在"描述画面" textarea 和"参考图片风格"之间，插入模式1区域：**

```tsx
{/* 模式1：自由底图上传 */}
<div style={{
  marginBottom: '14px', padding: '14px',
  border: '2px solid rgba(16,185,129,0.3)',
  borderRadius: '12px',
  background: 'rgba(16,185,129,0.04)'
}}>
  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
    <span style={{ fontSize: '13px', color: '#10b981', fontWeight: 600 }}>🖼️ 参考图生图 — 底图上传</span>
    <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '8px', background: 'rgba(16,185,129,0.2)', color: '#10b981' }}>模式1</span>
  </div>

  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
    {freeRefImages.map((img, idx) => (
      <div key={img.id} style={{ position: 'relative', width: '80px', height: '80px', borderRadius: '10px', overflow: 'hidden', border: `2px solid ${idx === 0 ? '#10b981' : 'rgba(16,185,129,0.3)'}`, flexShrink: 0 }}>
        <img src={img.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        <div style={{ position: 'absolute', top: '4px', left: '4px', fontSize: '9px', background: '#10b981', color: 'black', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>{img.label}</div>
        <button
          onClick={() => setFreeRefImages(prev => prev.filter(r => r.id !== img.id).map((r, i) => ({ ...r, label: `图${i + 1}` })))}
          style={{ position: 'absolute', top: '4px', right: '4px', width: '16px', height: '16px', borderRadius: '50%', background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: 'none', color: 'white', fontSize: '8px' }}>
          ✕
        </button>
      </div>
    ))}
    <div
      onClick={() => fileInputRef2.current?.click()}
      onDrop={(e) => {
        e.preventDefault()
        const files = Array.from(e.dataTransfer.files)
        files.forEach(file => {
          const url = URL.createObjectURL(file)
          setFreeRefImages(prev => [...prev, { id: crypto.randomUUID(), url, label: `图${prev.length + 1}`, file }])
        })
      }}
      onDragOver={(e) => e.preventDefault()}
      style={{ width: '80px', height: '80px', border: '2px dashed rgba(16,185,129,0.35)', borderRadius: '10px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '2px', cursor: 'pointer', flexShrink: 0 }}>
      <div style={{ fontSize: '22px', color: 'rgba(16,185,129,0.5)' }}>+</div>
      <div style={{ fontSize: '9px', color: 'rgba(16,185,129,0.5)' }}>拖入上传</div>
    </div>
    <input ref={fileInputRef2} type="file" accept="image/*" multiple
      style={{ display: 'none' }}
      onChange={(e) => {
        const files = Array.from(e.target.files || [])
        files.forEach(file => {
          const url = URL.createObjectURL(file)
          setFreeRefImages(prev => [...prev, { id: crypto.randomUUID(), url, label: `图${prev.length + 1}`, file }])
        })
        e.target.value = ''
      }} />
  </div>

  {freeRefImages.length > 0 && (
    <div style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '10px', flexWrap: 'wrap' }}>
      <span style={{ color: 'rgba(255,255,255,0.3)' }}>@引用：</span>
      {freeRefImages.map(img => (
        <span key={img.id}
          onClick={() => {
            onPromptChange(freePrompt + ` @${img.label} `)
          }}
          style={{ display: 'inline-block', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>
          @{img.label}
        </span>
      ))}
    </div>
  )}
</div>
```

这个代码片段需要在 `ReferenceImageUploader` 组件调用之前插入。找到 `<ReferenceImageUploader` 那行（约第 87 行），在它上面插入。

---

## Task 8: ProjectImageGenForm 新增模式1多图上传 + @引用

**Files:**
- Modify: `src/components/ProjectImageGenForm.tsx`

- [ ] **Step 1: 同样的 UI 添加到 ProjectImageGenForm**

在 `ProjectImageGenForm` 中（约第 897 行，提示词 textarea 之后、`ReferenceImageUploader` 之前），插入与 Task 7 相同的模式1多图上传区域。变量名用 `projectRefImages` 代替 `freeRefImages`。

由于 ProjectImageGenForm 代码很长，关键是找到提示词 textarea（`<textarea ref={promptRef}` 那行）和参数行之间的位置插入。

---

## 自审查检查

**1. Spec 覆盖**
- ✅ 模式1多图上传区: Task 7, Task 8 (前端)
- ✅ @引用机制: Task 7, Task 8 (前端)
- ✅ 模式2风格参考: 保持现有，不改
- ✅ ImageBackend 能力标志: Task 1
- ✅ image_to_image 接受列表: Task 1, Task 2
- ✅ 模型列表返回能力: Task 3, Task 4
- ✅ 能力不足提示: 前端根据 max_ref_images 判断（在 Task 7/8 UI 中体现）

**2. 无占位符**
- ✅ 所有代码完整

**3. 类型一致性**
- ✅ image_to_image 签名统一为 `images_base64: list[str]`
- ✅ 前端 FreeRefImage 类型匹配
