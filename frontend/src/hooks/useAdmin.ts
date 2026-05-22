import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAdminStats,
  adminListUsers,
  adminUpdateUser,
  adminListProducts,
  adminUpdateProductStatus,
  adminListOrders,
  adminUpdateOrderStatus,
  adminCancelOrder,
  adminDeleteReview,
} from '../api/admin'

export function useAdminStats() {
  return useQuery({
    queryKey: ['admin-stats'],
    queryFn: getAdminStats,
    staleTime: 60_000,
  })
}

export function useAdminUsers(page = 1, per_page = 20, role?: string, q?: string) {
  return useQuery({
    queryKey: ['admin-users', page, per_page, role, q],
    queryFn: () => adminListUsers(page, per_page, role, q),
  })
}

export function useAdminUpdateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ user_id, payload }: { user_id: string; payload: { role?: string; is_active?: boolean } }) =>
      adminUpdateUser(user_id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })
}

export function useAdminProducts(page = 1, per_page = 20, status?: string) {
  return useQuery({
    queryKey: ['admin-products', page, per_page, status],
    queryFn: () => adminListProducts(page, per_page, status),
  })
}

export function useAdminUpdateProductStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ product_id, status }: { product_id: string; status: string }) =>
      adminUpdateProductStatus(product_id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-products'] }),
  })
}

export function useAdminOrders(page = 1, per_page = 20, status?: string) {
  return useQuery({
    queryKey: ['admin-orders', page, per_page, status],
    queryFn: () => adminListOrders(page, per_page, status),
  })
}

export function useAdminUpdateOrderStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ order_id, status }: { order_id: string; status: string }) =>
      adminUpdateOrderStatus(order_id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-orders'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
    },
  })
}

export function useAdminCancelOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (order_id: string) => adminCancelOrder(order_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-orders'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
    },
  })
}

export function useAdminDeleteReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (review_id: string) => adminDeleteReview(review_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-stats'] }),
  })
}
