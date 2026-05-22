import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getProductReviews,
  createReview,
  updateReview,
  deleteReview,
  markReviewHelpful,
} from '../api/reviews'
import type { ReviewCreate, ReviewUpdate } from '../types'

export function useProductReviews(product_id: string, page = 1) {
  return useQuery({
    queryKey: ['reviews', product_id, page],
    queryFn: () => getProductReviews(product_id, page),
    enabled: !!product_id,
    staleTime: 60_000,
  })
}

export function useCreateReview(product_id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ReviewCreate) => createReview(product_id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews', product_id] })
      queryClient.invalidateQueries({ queryKey: ['product', product_id] })
    },
  })
}

export function useUpdateReview(product_id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ review_id, payload }: { review_id: string; payload: ReviewUpdate }) =>
      updateReview(product_id, review_id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews', product_id] }),
  })
}

export function useDeleteReview(product_id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (review_id: string) => deleteReview(product_id, review_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews', product_id] })
      queryClient.invalidateQueries({ queryKey: ['product', product_id] })
    },
  })
}

export function useMarkReviewHelpful() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (review_id: string) => markReviewHelpful(review_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews'] }),
  })
}
