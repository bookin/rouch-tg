import type {Practice, PracticeProgress, PracticeRecommendation} from '@/api/client'

export interface PracticeDetails {
  id: string
  name: string
  category?: string
  description?: string
  duration?: number
  steps?: string[]
  benefits?: string
  contraindications?: string[]
  tags?: string[]
}

export const buildPracticeCatalogMap = (practices: Practice[]) =>
  practices.reduce<Record<string, Practice>>((acc, practice) => {
    acc[practice.id] = practice
    return acc
  }, {})

export const practiceDetailsFromCatalog = (practice: Practice): PracticeDetails => ({
  id: practice.id,
  name: practice.name,
  category: practice.category,
  description: practice.description || undefined,
  duration: practice.duration,
  steps: practice.steps || [],
  benefits: practice.benefits || undefined,
  contraindications: practice.contraindications || [],
  tags: practice.tags || []
})

export const practiceDetailsFromRecommendation = (
  recommendation: PracticeRecommendation
): PracticeDetails => ({
  id: recommendation.id,
  name: recommendation.name,
  category: recommendation.category,
  description: recommendation.description || recommendation.content,
  duration: recommendation.duration,
  steps: recommendation.steps || [],
  benefits: recommendation.benefits,
  contraindications: recommendation.contraindications || [],
  tags: recommendation.tags || []
})

export const practiceDetailsFromProgress = (
  progress: PracticeProgress,
  catalogMap: Record<string, Practice>
): PracticeDetails => {
  const catalogPractice = catalogMap[progress.practice_id]
  if (catalogPractice) {
    return practiceDetailsFromCatalog(catalogPractice)
  }

  return {
    id: progress.practice_id,
    name: progress.practice_name,
    category: progress.practice_category,
    duration: progress.practice_duration,
    steps: []
  }
}
