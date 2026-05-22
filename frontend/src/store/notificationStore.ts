import { create } from 'zustand'

export interface WsNotification {
  id: string
  type: string
  order_id: string
  message: string
  timestamp: string
  read: boolean
}

interface NotificationState {
  notifications: WsNotification[]
  unreadCount: number
  addNotification: (n: Omit<WsNotification, 'id' | 'read'>) => void
  markAllRead: () => void
  clear: () => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (n) => {
    const notification: WsNotification = {
      ...n,
      id: Math.random().toString(36).slice(2),
      read: false,
    }
    set((state) => ({
      notifications: [notification, ...state.notifications].slice(0, 50),
      unreadCount: state.unreadCount + 1,
    }))
  },

  markAllRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  clear: () => set({ notifications: [], unreadCount: 0 }),
}))
