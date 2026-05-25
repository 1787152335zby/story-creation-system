export interface PhaseInfo {
  name: string
  done: boolean
}

export interface ProjectInfo {
  name: string
  genre?: string
  updated_at?: string
  created_at?: string
  phases?: PhaseInfo[]
  pending_approval?: number | null
  pending_version?: number | null
  auto_approve?: boolean
  pending_episode?: boolean
  running?: boolean
  total_phases?: number
  style_type?: string
  status?: string
  [key: string]: unknown
}

export interface VisualAsset {
  name: string
  file: string
  from_generated?: boolean
}

export interface VisualAssetsData {
  characters: VisualAsset[]
  scenes: VisualAsset[]
  props: VisualAsset[]
}

export interface EntityImage {
  name: string
  url: string
}

export interface EntityImagesMap {
  characters: Record<string, EntityImage[]>
  scenes: Record<string, EntityImage[]>
  props: Record<string, EntityImage[]>
}

export interface ReferenceUrlsByType {
  style: string[]
  character: string[]
  scene: string[]
  prop: string[]
}

export interface AnalyzeStyleResult {
  render_style: string
  tone: string
  material: string
  proportion: string
  raw_keywords: string
}

export interface FreeImageResult {
  images: { url: string; local: string }[]
  task_id?: string
  seed?: number
}

export interface ProjectImageGenResult {
  images: { url: string; local: string }[]
  project_images: { folder: string; images: { url: string; local: string }[] }[]
  versions?: Record<string, number>
  task_id?: string
  seed?: number
}

export interface FreeVideoResult {
  video_url?: string
  local?: string
  error?: string
  task_id?: string
}

export interface HistoryEntry {
  name: string
  url: string
  mode?: 'free' | 'project'
  prompt?: string
  negative_prompt?: string
  model?: string
  size?: string
  count?: number
  reference_urls?: string[]
  timestamp?: string
  project_name?: string
  character_names?: string[]
  scene_names?: string[]
  version?: string
}

export interface GenerationHistory {
  images_free: HistoryEntry[]
  images_project: HistoryEntry[]
  videos_free: HistoryEntry[]
  videos_project: HistoryEntry[]
  videos: HistoryEntry[]
}

export interface Template {
  name: string
  genre?: string
  [key: string]: unknown
}

export interface CharacterInfo {
  name: string
  type: string
  appearance?: string
  clothing?: string
  expression?: string
  pose?: string
  accessories?: string[]
  key_features?: string[]
  status?: string
  is_base?: boolean
  variant_name?: string
  character_base?: string
  character_id?: string
  variant_tag?: string
  feature_desc?: string
  based_on?: string | null
  variants?: string[]
  appearance_change?: string
  clothing_change?: string
  trigger_event?: string
  applies_from?: string
  applies_to?: string
  _file?: string
  age?: string
  gender?: string
}

export interface SceneInfo {
  name: string
  environment?: string
  lighting?: string
  color_tone?: string
  props?: string[]
  status?: string
  is_base?: boolean
  variant_name?: string
  scene_base?: string
  scene_id?: string
  variant_tag?: string
  feature_desc?: string
  based_on?: string | null
  variants?: string[]
  change?: string
  trigger_event?: string
  _file?: string
}

export interface PropInfo {
  name: string
  prop_id?: string
  type?: string
  prop_class?: string
  description?: string
  owner?: string | null
  owner_character_id?: string
  mount_position?: string
  appearance?: string
  category?: string
  bind_scene_id?: string
  bind_plot_node?: string
  status?: string
  _file?: string
}

export interface AssetLibraryVersion {
  version: string
  confirmed: boolean
  images: { url: string; name: string }[]
}

export interface AssetLibraryEntity {
  confirmed_versions: AssetLibraryVersion[]
  all_versions: AssetLibraryVersion[]
  latest_confirmed: AssetLibraryVersion | null
}

export interface AssetLibrary {
  characters: Record<string, AssetLibraryEntity>
  scenes: Record<string, AssetLibraryEntity>
  props: Record<string, AssetLibraryEntity>
}
