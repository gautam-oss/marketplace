import apiClient from './client'
import type { ReviewResponse, ReviewListResponse, ReviewCreate, ReviewUpdate, MessageResponse } from '../types'

export const getProductReviews = async (
  product_id: string,
  page = 1,
  per_page = 10
): Promise<ReviewListResponse> => {
  const { data } = await apiClient.get<ReviewListResponse>(
    `/api/v1/products/${product_id}/reviews`,
    { params: { page, per_page } }
  )
  return data
}

export const createReview = async (
  product_id: string,
  payload: ReviewCreate
): Promise<ReviewResponse> => {
  const { data } = await apiClient.post<ReviewResponse>(
    `/api/v1/products/${product_id}/reviews`,
    payload
  )
  return data
}

export const updateReview = async (
  product_id: string,
  review_id: string,
  payload: ReviewUpdate
): Promise<ReviewResponse> => {
  const { data } = await apiClient.put<ReviewResponse>(
    `/api/v1/products/${product_id}/reviews/${review_id}`,
    payload
  )
  return data
}

export const deleteReview = async (
  product_id: string,
  review_id: string
): Promise<MessageResponse> => {
  const { data } = await apiClient.delete<MessageResponse>(
    `/api/v1/products/${product_id}/reviews/${review_id}`
  )
  return data
}

export const markReviewHelpful = async (review_id: string): Promise<MessageResponse> => {
  const { data } = await apiClient.post<MessageResponse>(`/api/v1/reviews/${review_id}/helpful`)
  return data
}
