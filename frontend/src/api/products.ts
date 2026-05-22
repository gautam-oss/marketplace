import apiClient from './client'
import type {
  ProductListItem,
  ProductResponse,
  ProductCreate,
  ProductUpdate,
  ProductFilters,
  PaginatedResponse,
} from '../types'

export const getProducts = async (
  filters: ProductFilters = {}
): Promise<PaginatedResponse<ProductListItem>> => {
  const { data } = await apiClient.get<PaginatedResponse<ProductListItem>>('/api/v1/products', {
    params: filters,
  })
  return data
}

export const getProductBySlug = async (slug: string): Promise<ProductResponse> => {
  const { data } = await apiClient.get<ProductResponse>(`/api/v1/products/${slug}`)
  return data
}

export const createProduct = async (
  payload: ProductCreate,
  images?: File[]
): Promise<ProductResponse> => {
  const form = new FormData()
  form.append('title', payload.title)
  if (payload.description) form.append('description', payload.description)
  form.append('price', String(payload.price))
  if (payload.compare_at_price) form.append('compare_at_price', String(payload.compare_at_price))
  form.append('stock', String(payload.stock))
  if (payload.category_id) form.append('category_id', payload.category_id)
  if (payload.sku) form.append('sku', payload.sku)
  payload.tags?.forEach((tag) => form.append('tags', tag))
  images?.forEach((f) => form.append('images', f))
  const { data } = await apiClient.post<ProductResponse>('/api/v1/products', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const updateProduct = async (
  slug: string,
  payload: ProductUpdate
): Promise<ProductResponse> => {
  const { data } = await apiClient.patch<ProductResponse>(`/api/v1/products/${slug}`, payload)
  return data
}

export const deleteProduct = async (slug: string): Promise<void> => {
  await apiClient.delete(`/api/v1/products/${slug}`)
}

export const getMyProducts = async (
  page = 1,
  per_page = 20
): Promise<PaginatedResponse<ProductListItem>> => {
  const { data } = await apiClient.get<PaginatedResponse<ProductListItem>>(
    '/api/v1/products/my',
    { params: { page, per_page } }
  )
  return data
}
