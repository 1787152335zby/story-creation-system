const BASE = '/api'

export interface StyleConfig {
  story_type: string
  genre: string
  writing_style: string
  visual_style: string
  art_style: string
  screen_aspect: string
  script_style: string
  duration_mode: string
  episode_count: string
  episode_duration: string
  custom_requirements: string
  visual_reference: string
  action_reference: string
}

export interface CreateProjectPayload {
  name: string
  story_idea: string
  style: StyleConfig
  duration_line: string
}

export interface AggConfig {
  id: string
  name: string
  base_url: string
  api_key: string
  type: string
  model: string
  active: boolean
}

export interface ProviderConfig {
  id: string
  name: string
  provider_id: string
  api_key: string
  model: string
  base_url: string
  type: string
  active: boolean
}

export interface SettingsData {
  llm_backend: string
  deepseek_api_key: string
  deepseek_model: string
  openai_api_key: string
  openai_model: string
  claude_api_key: string
  claude_model: string
  seedance_api_key: string
  image_backend: string
  custom_image_base_url: string
  custom_image_model: string
  banana2_api_key: string
  banana2_base_url: string
  banana2_model: string
}

export async function fetchProjects(): Promise<any[]> {
  const res = await fetch(`${BASE}/projects`)
  if (!res.ok) throw new Error('Failed to fetch projects')
  return res.json()
}

export async function fetchProject(name: string): Promise<any> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error('Project not found')
  return res.json()
}

export async function fetchPhaseContent(name: string, phase: string): Promise<{ content: string; is_split: boolean; file_list: string[] }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/${encodeURIComponent(phase)}/content`)
  if (!res.ok) return { content: '', is_split: false, file_list: [] }
  return res.json()
}

export async function createProject(payload: CreateProjectPayload): Promise<{ name: string }> {
  const res = await fetch(`${BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to create project')
  return res.json()
}

export async function deleteProject(name: string): Promise<void> {
  await fetch(`${BASE}/projects/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

export async function generateRandomIdea(style: StyleConfig): Promise<string> {
  const res = await fetch(`${BASE}/projects/random-idea`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(style),
  })
  if (!res.ok) throw new Error('Failed to generate random idea')
  const data = await res.json()
  return data.idea
}

export async function openProjectFolder(name: string): Promise<{ opened: boolean; path?: string }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/open`, { method: 'POST' })
  return res.json()
}

export async function fetchSettings(): Promise<SettingsData> {
  const res = await fetch(`${BASE}/settings`)
  if (!res.ok) throw new Error('Failed to fetch settings')
  return res.json()
}

export async function updateSettings(data: Partial<SettingsData>): Promise<void> {
  await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function testLLM(backend: string, apiKey: string, model: string): Promise<{ success: boolean; response?: string; error?: string }> {
  const res = await fetch(`${BASE}/settings/test-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ backend, api_key: apiKey, model }),
  })
  return res.json()
}

export async function fetchVisualAssets(name: string): Promise<{ characters: { name: string; file: string }[]; scenes: { name: string; file: string }[] }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-assets`)
  if (!res.ok) return { characters: [], scenes: [] }
  return res.json()
}

export async function fetchCharacters(name: string): Promise<any[]> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/characters`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchScenes(name: string): Promise<any[]> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/scenes`)
  if (!res.ok) return []
  return res.json()
}

export async function generateSelectionPrompt(name: string, characterNames: string[], sceneNames: string[]): Promise<string> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/prompts`)
  if (!res.ok) return ''
  const data = await res.json()

  const parts: string[] = []
  for (const cName of characterNames) {
    if (data.character_prompts?.[cName]) {
      parts.push(`### ${cName}\n${data.character_prompts[cName]}`)
    }
  }
  for (const sName of sceneNames) {
    if (data.scene_prompts?.[sName]) {
      parts.push(`### ${sName}\n${data.scene_prompts[sName]}`)
    }
  }
  if (data.storyboard_prompt) {
    parts.push(`\n---\n${data.storyboard_prompt.substring(0, 2000)}`)
  }
  return parts.join('\n\n') || ''
}

export async function fetchVideoClips(name: string): Promise<{ clips: { name: string; file: string }[]; final: { name: string; file: string } | null }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/video-clips`)
  if (!res.ok) return { clips: [], final: null }
  return res.json()
}

export function getMediaUrl(name: string, subpath: string): string {
  return `${BASE}/projects/${encodeURIComponent(name)}/media/${encodeURIComponent(subpath)}`
}

export async function freeImageGen(prompt: string, negativePrompt: string = '', size: string = '1024x1024', n: number = 1, model: string = ''): Promise<{ images: { url: string; local: string }[] }> {
  const res = await fetch(`${BASE}/image-gen/free`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, negative_prompt: negativePrompt, size, n, model }),
  })
  if (!res.ok) {
    const text = await res.text()
    try {
      const json = JSON.parse(text)
      throw new Error(json.detail || json.message || text)
    } catch {
      throw new Error(text)
    }
  }
  return res.json()
}

export async function freeVideoGen(prompt: string, files?: File[], model?: string, resolution?: string, duration?: number, generate_audio?: boolean): Promise<{ video_url?: string; local?: string; error?: string; task_id?: string }> {
  const form = new FormData()
  form.append('prompt', prompt)
  if (files && files.length > 0) files.forEach(f => form.append('files', f))
  if (model) form.append('model', model)
  if (resolution) form.append('resolution', resolution)
  if (duration) form.append('duration', String(duration))
  if (generate_audio) form.append('generate_audio', 'true')
  const res = await fetch(`${BASE}/video-gen/free`, {
    method: 'POST',
    body: form,
  })
  return res.json()
}

export async function fetchProjectVisualAssets(projectName: string): Promise<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(projectName)}/visual-assets`)
  if (!res.ok) return { characters: {}, scenes: {} }
  return res.json()
}

export async function fetchImageResolutions(model?: string): Promise<{ resolutions: string[]; groups: Record<string, string[]> }> {
  const params = model ? `?model=${encodeURIComponent(model)}` : ''
  const res = await fetch(`${BASE}/image-gen/resolutions${params}`)
  if (!res.ok) return { resolutions: ['1024x1024', '768x1344', '1344x768'], groups: { '1:1': ['1024x1024'], '4:3': ['768x1344'], '3:4': ['1344x768'] } }
  const data = await res.json()
  return { resolutions: data.resolutions, groups: data.groups }
}

export async function fetchVideoResolutions(model?: string): Promise<{ resolutions: string[]; groups: Record<string, string[]> }> {
  const params = model ? `?model=${encodeURIComponent(model)}` : ''
  const res = await fetch(`${BASE}/video-gen/resolutions${params}`)
  if (!res.ok) return { resolutions: ['1024x1024', '1280x720', '1920x1080'], groups: { '1:1': ['1024x1024'], '16:9': ['1280x720', '1920x1080'] } }
  const data = await res.json()
  return { resolutions: data.resolutions, groups: data.groups }
}

export async function fetchImageBackends(): Promise<{ value: string; label: string; desc: string }[]> {
  const res = await fetch(`${BASE}/image-gen/backends`)
  if (!res.ok) return []
  const data = await res.json()
  return data.backends
}

export async function fetchAvailableModels(): Promise<any> {
  const res = await fetch(`${BASE}/settings/models`)
  if (!res.ok) return { llm_groups: [], image_groups: [], video_groups: [] }
  return res.json()
}

export async function reExtractVisual(name: string): Promise<{ characters: number; scenes: number }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/re-extract-visual`, { method: 'POST' })
  return res.json()
}

export async function saveProjectTemplate(name: string, templateName: string): Promise<{ saved: boolean }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/save-template?template_name=${encodeURIComponent(templateName)}`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchTemplates(): Promise<any[]> {
  const res = await fetch(`${BASE}/templates`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchAggConfigs(type: string): Promise<{ configs: AggConfig[] }> {
  const res = await fetch(`${BASE}/settings/aggregated-configs?type=${type}`)
  if (!res.ok) return { configs: [] }
  return res.json()
}

export async function createAggConfig(data: { name: string; base_url: string; api_key: string; type: string; model?: string }): Promise<AggConfig> {
  const res = await fetch(`${BASE}/settings/aggregated-configs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateAggConfig(id: string, data: any): Promise<any> {
  const res = await fetch(`${BASE}/settings/aggregated-configs/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteAggConfig(id: string): Promise<any> {
  const res = await fetch(`${BASE}/settings/aggregated-configs/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function activateAggConfig(id: string): Promise<any> {
  const res = await fetch(`${BASE}/settings/aggregated-configs/${id}/activate`, { method: 'POST' })
  return res.json()
}

export async function deactivateAggType(type: string): Promise<any> {
  const res = await fetch(`${BASE}/settings/aggregated-configs/type/${type}/deactivate`, { method: 'POST' })
  return res.json()
}

export async function testAggConfig(data: { base_url: string; api_key: string }): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${BASE}/settings/test-aggregated`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.json()
}

export async function fetchAggConfigModels(configId: string): Promise<{ families: ModelFamily[] }> {
  const res = await fetch(`${BASE}/settings/aggregated-configs/${encodeURIComponent(configId)}/models`)
  if (!res.ok) return { families: [] }
  return res.json()
}

export interface ModelFamily {
  id: string
  name: string
  versions: { value: string; label: string }[]
}

export async function fetchModelsFamilies(type: 'image' | 'video'): Promise<{ families: ModelFamily[] }> {
  const res = await fetch(`${BASE}/settings/models/families?type=${type}`)
  if (!res.ok) return { families: [] }
  return res.json()
}

export async function fetchActiveConfig(configType: string): Promise<any> {
  const res = await fetch(`${BASE}/settings/active-config/${configType}`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchGenerationHistory(): Promise<{ images_free: { name: string; url: string }[]; images_project: { name: string; url: string }[]; videos: { name: string; url: string }[] }> {
  const res = await fetch(`${BASE}/generated-history`)
  if (!res.ok) return { images_free: [], images_project: [], videos: [] }
  return res.json()
}

export async function projectImageGen(params: {
  project_name: string
  prompt: string
  negative_prompt?: string
  size?: string
  n?: number
  model?: string
  character_names?: string[]
  scene_names?: string[]
  reference_url?: string
  reference_urls?: string[]
  version?: string
}): Promise<{ images: { url: string; local: string }[]; project_images: { folder: string; images: { url: string; local: string }[] }[]; versions?: Record<string, number> }> {
  const res = await fetch(`${BASE}/image-gen/project`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '请求失败') }
  return res.json()
}

export async function stitchImages(imagePaths: string[], saveTo: string = ''): Promise<{ url: string; local: string; name: string; saved_to?: string }> {
  const res = await fetch(`${BASE}/image-gen/stitch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_paths: imagePaths, save_to: saveTo }),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '拼图失败') }
  return res.json()
}

export async function fetchProjectImages(projectName: string): Promise<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }> {
  const res = await fetch(`${BASE}/image-gen/project-images/${encodeURIComponent(projectName)}`)
  if (!res.ok) return { characters: {}, scenes: {} }
  return res.json()
}

export async function fetchConfirmedImages(projectName: string): Promise<{ characters: Record<string, { name: string; url: string }[]>; scenes: Record<string, { name: string; url: string }[]> }> {
  const res = await fetch(`${BASE}/image-gen/confirmed-images/${encodeURIComponent(projectName)}`)
  if (!res.ok) return { characters: {}, scenes: {} }
  return res.json()
}

export async function deleteGeneratedFile(filePath: string): Promise<void> {
  const res = await fetch(`${BASE}/image-gen/delete?file_path=${encodeURIComponent(filePath)}`, { method: 'DELETE' })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '删除失败') }
}

export async function clearProjectFolder(projectName: string, subfolder: string): Promise<{ deleted: number }> {
  const res = await fetch(`${BASE}/image-gen/clear-folder?project_name=${encodeURIComponent(projectName)}&subfolder=${encodeURIComponent(subfolder)}`, { method: 'POST' })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '清空失败') }
  return res.json()
}

export async function confirmVersion(projectName: string, entityType: string, entityName: string, version: string): Promise<{ confirmed: boolean; version: string }> {
  const res = await fetch(`${BASE}/image-gen/confirm-version?project_name=${encodeURIComponent(projectName)}&entity_type=${encodeURIComponent(entityType)}&entity_name=${encodeURIComponent(entityName)}&version=${encodeURIComponent(version)}`, { method: 'POST' })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '确认失败') }
  return res.json()
}

export async function deleteVersion(projectName: string, entityType: string, entityName: string, version: string): Promise<{ deleted: boolean; version: string }> {
  const res = await fetch(`${BASE}/image-gen/delete-version?project_name=${encodeURIComponent(projectName)}&entity_type=${encodeURIComponent(entityType)}&entity_name=${encodeURIComponent(entityName)}&version=${encodeURIComponent(version)}`, { method: 'POST' })
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '删除版本失败') }
  return res.json()
}

export async function fetchProviderConfigs(providerId: string): Promise<{ configs: ProviderConfig[] }> {
  const res = await fetch(`${BASE}/settings/provider-configs?provider_id=${providerId}`)
  if (!res.ok) return { configs: [] }
  return res.json()
}

export async function createProviderConfig(data: { provider_id: string; api_key: string; model?: string }): Promise<any> {
  const res = await fetch(`${BASE}/settings/provider-configs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateProviderConfig(id: string, data: any): Promise<any> {
  const res = await fetch(`${BASE}/settings/provider-configs/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteProviderConfig(id: string): Promise<any> {
  const res = await fetch(`${BASE}/settings/provider-configs/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function activateProviderConfig(id: string): Promise<any> {
  const res = await fetch(`${BASE}/settings/provider-configs/${id}/activate`, { method: 'POST' })
  return res.json()
}

export async function deleteTemplate(templateName: string): Promise<void> {
  await fetch(`${BASE}/templates/${encodeURIComponent(templateName)}`, { method: 'DELETE' })
}

export async function runVisualExtract(name: string): Promise<{ characters: number; scenes: number }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-extract`, { method: 'POST' })
  return res.json()
}

export async function confirmVisualExtract(name: string): Promise<void> {
  await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-extract/confirm`, { method: 'POST' })
}

export async function addVisualCharacter(name: string, characterName: string): Promise<{ character: any }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-extract/characters?character_name=${encodeURIComponent(characterName)}`, { method: 'POST' })
  return res.json()
}

export async function updateVisualCharacter(name: string, charName: string, data: any): Promise<void> {
  await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-extract/characters/${encodeURIComponent(charName)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
}

export async function deleteVisualCharacter(name: string, charName: string): Promise<void> {
  await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-extract/characters/${encodeURIComponent(charName)}`, { method: 'DELETE' })
}

export async function generateCombinedPrompt(projectName: string, characterNames: string[], sceneNames: string[], storyboardChunk: string = ''): Promise<{ prompt: string }> {
  const res = await fetch(`${BASE}/prompt-gen/combined`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName, character_names: characterNames, scene_names: sceneNames, storyboard_chunk: storyboardChunk }),
  })
  return res.json()
}
