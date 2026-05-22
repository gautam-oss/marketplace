import apiClient from './client'
import type { OrderResponse, OrderCreate, CheckoutResponse, PaginatedResponse, MessageResponse } from '../types'

export const getOrders = async (page = 1, per_page = 20): Promise<PaginatedResponse<OrderResponse>> => {
  const { data } = await apiClient.get<PaginatedResponse<OrderResponse>>('/api/v1/orders', {
    params: { page, per_page },
  })
  return data
}

export const getOrder = async (id: string): Promise<OrderResponse> => {
  const { data } = await apiClient.get<OrderResponse>(`/api/v1/orders/${id}`)
  return data
}

export const checkout = async (payload: OrderCreate): Promise<CheckoutResponse> => {
  const { data } = await apiClient.post<CheckoutResponse>('/api/v1/orders/checkout', payload)
  return data
}

export const cancelOrder = async (id: string): Promise<MessageResponse> => {
  const { data } = await apiClient.post<MessageResponse>(`/api/v1/orders/${id}/cancel`)
  return data
}
