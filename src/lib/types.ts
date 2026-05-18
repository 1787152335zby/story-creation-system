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
}

export interface EntityImage {
  name: string
  url: string
}

export interface EntityImagesMap {
  characters: Record<string, EntityImage[]>
  scenes: Record<string, EntityImage[]>
}

export interface FreeImageResult {
  images: { url: string; local: string }[]
}

export interface ProjectImageGenResult {
  images: { url: string; local: string }[]
  project_images: { folder: string; images: { url: string; local: string }[] }[]
  versions?: Record<string, number>
}

export interface FreeVideoResult {
  video_url?: string
  local?: string
  error?: string
  task_id?: string
}

export interface GenerationHistory {
  images_free: { name: string; url: string }[]
  images_project: { name: string; url: string }[]
  videos: { name: string; url: string }[]
}

export interface Template {
  name: string
  genre?: string
  [key: string]: unknown
}
