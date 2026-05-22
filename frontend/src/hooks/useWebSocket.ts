import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { useNotificationStore } from '../store/notificationStore'
import { useToast } from '../components/Toast'

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const MAX_RETRIES = 5

export function useWebSocket() {
  const { isAuthenticated } = useAuthStore()
  const addNotification = useNotificationStore((s) => s.addNotification)
  const toast = useToast()
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const token = localStorage.getItem('access_token')
    if (!token) return

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string)
        addNotification({
          type: msg.type,
          order_id: msg.order_id,
          message: msg.message,
          timestamp: msg.timestamp,
        })
        const toastType = msg.type === 'order.cancelled' ? 'error' : 'success'
        toast(msg.message, toastType)
        queryClient.invalidateQueries({ queryKey: ['orders'] })
        if (msg.order_id) {
          queryClient.invalidateQueries({ queryKey: ['order', msg.order_id] })
        }
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = (event) => {
      if (!mountedRef.current) return
      if (event.code === 4008) return  // auth failure — don't retry
      if (retriesRef.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30_000)
        retriesRef.current++
        timeoutRef.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => ws.close()
  }, [isAuthenticated, addNotification, toast, queryClient])

  useEffect(() => {
    mountedRef.current = true
    if (isAuthenticated) connect()

    return () => {
      mountedRef.current = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      wsRef.current?.close()
    }
  }, [isAuthenticated, connect])
}
