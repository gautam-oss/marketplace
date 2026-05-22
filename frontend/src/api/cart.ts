import apiClient from './client'
import type { CartResponse } from '../types'

export const getCart = async (): Promise<CartResponse> => {
  const { data } = await apiClient.get<CartResponse>('/api/v1/cart')
  return data
}

export const addToCart = async (product_id: string, quantity = 1): Promise<CartResponse> => {
  const { data } = await apiClient.post<CartResponse>('/api/v1/cart/items', { product_id, quantity })
  return data
}

export const updateCartItem = async (product_id: string, quantity: number): Promise<CartResponse> => {
  const { data } = await apiClient.put<CartResponse>(`/api/v1/cart/items/${product_id}`, { quantity })
  return data
}

export const removeCartItem = async (product_id: string): Promise<CartResponse> => {
  const { data } = await apiClient.delete<CartResponse>(`/api/v1/cart/items/${product_id}`)
  return data
}

export const clearCart = async (): Promise<void> => {
  await apiClient.delete('/api/v1/cart')
}
