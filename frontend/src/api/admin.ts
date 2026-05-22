import apiClient from './client'
import type {
  AdminStats,
  User,
  ProductListItem,
  OrderResponse,
  PaginatedResponse,
  MessageResponse,
} from '../types'

export const getAdminStats = async (): Promise<AdminStats> => {
  const { data } = await apiClient.get<AdminStats>('/api/v1/admin/stats')
  return data
}

export const adminListUsers = async (
  page = 1,
  per_page = 20,
  role?: string,
  q?: string
): Promise<PaginatedResponse<User>> => {
  const { data } = await apiClient.get<PaginatedResponse<User>>('/api/v1/admin/users', {
    params: { page, per_page, role, q },
  })
  return data
}

export const adminUpdateUser = async (
  user_id: string,
  payload: { role?: string; is_active?: boolean }
): Promise<User> => {
  const { data } = await apiClient.patch<User>(`/api/v1/admin/users/${user_id}`, payload)
  return data
}

export const adminListProducts = async (
  page = 1,
  per_page = 20,
  status?: string
): Promise<PaginatedResponse<ProductListItem>> => {
  const { data } = await apiClient.get<PaginatedResponse<ProductListItem>>(
    '/api/v1/admin/products',
    { params: { page, per_page, status } }
  )
  return data
}

export const adminUpdateProductStatus = async (
  product_id: string,
  status: string
): Promise<ProductListItem> => {
  const { data } = await apiClient.patch<ProductListItem>(
    `/api/v1/admin/products/${product_id}/status`,
    { status }
  )
  return data
}

export const adminListOrders = async (
  page = 1,
  per_page = 20,
  status?: string
): Promise<PaginatedResponse<OrderResponse>> => {
  const { data } = await apiClient.get<PaginatedResponse<OrderResponse>>(
    '/api/v1/admin/orders',
    { params: { page, per_page, status } }
  )
  return data
}

export const adminDeleteReview = async (review_id: string): Promise<MessageResponse> => {
  const { data } = await apiClient.delete<MessageResponse>(
    `/api/v1/admin/reviews/${review_id}`
  )
  return data
}
