import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCart, addToCart, updateCartItem, removeCartItem, clearCart } from '../api/cart'
import { useCartStore } from '../store/cartStore'
import { useAuthStore } from '../store/authStore'

export function useCart() {
  const { isAuthenticated } = useAuthStore()
  const { setCart } = useCartStore()

  return useQuery({
    queryKey: ['cart'],
    queryFn: async () => {
      const cart = await getCart()
      setCart(cart)
      return cart
    },
    enabled: isAuthenticated,
    staleTime: 30_000,
  })
}

export function useAddToCart() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ product_id, quantity }: { product_id: string; quantity?: number }) =>
      addToCart(product_id, quantity),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ product_id, quantity }: { product_id: string; quantity: number }) =>
      updateCartItem(product_id, quantity),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })
}

export function useRemoveCartItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (product_id: string) => removeCartItem(product_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })
}

export function useClearCart() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clearCart,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cart'] }),
  })
}
