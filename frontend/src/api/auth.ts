import apiClient from './client'
import type { TokenResponse, User, RegisterRequest } from '../types'

export const login = async (email: string, password: string): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/api/v1/auth/login', { email, password })
  return data
}

export const register = async (payload: RegisterRequest): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/api/v1/auth/register', payload)
  return data
}

export const getMe = async (): Promise<User> => {
  const { data } = await apiClient.get<User>('/api/v1/auth/me')
  return data
}

export const refreshToken = async (refresh_token: string): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', { refresh_token })
  return data
}
