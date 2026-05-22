import { create } from 'zustand'
import type { CartResponse } from '../types'

interface CartState {
  cart: CartResponse | null;
  setCart: (cart: CartResponse) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()((set) => ({
  cart: null,
  setCart: (cart) => set({ cart }),
  clearCart: () => set({ cart: null }),
}))
