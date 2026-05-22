import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { login, register, getMe } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import type { RegisterRequest } from '../types'

export function useMe() {
  const { isAuthenticated } = useAuthStore()
  return useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  const { setAuth } = useAuthStore()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: async (tokens) => {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const user = await getMe()
      setAuth(user, tokens)
      queryClient.setQueryData(['me'], user)
      navigate('/')
    },
  })
}

export function useRegister() {
  const { setAuth } = useAuthStore()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (payload: RegisterRequest) => register(payload),
    onSuccess: async (tokens) => {
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const user = await getMe()
      setAuth(user, tokens)
      queryClient.setQueryData(['me'], user)
      navigate('/')
    },
  })
}

export function useLogout() {
  const { logout } = useAuthStore()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return () => {
    logout()
    queryClient.clear()
    navigate('/login')
  }
}
