import apiClient from './client'
import type { CategoryResponse } from '../types'

export const getCategories = async (): Promise<CategoryResponse[]> => {
  const { data } = await apiClient.get<CategoryResponse[]>('/api/v1/categories')
  return data
}

export const getCategoryBySlug = async (slug: string): Promise<CategoryResponse> => {
  const { data } = await apiClient.get<CategoryResponse>(`/api/v1/categories/${slug}`)
  return data
}
