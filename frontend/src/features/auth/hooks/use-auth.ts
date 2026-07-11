import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import i18n from '@/shared/i18n'
import { authApi, clearTokens, setTokens } from '@/shared/lib/api-client'
import { useAuthStore } from '@/shared/stores/auth-store'

export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore()
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => authApi.me(),   // returns User directly, no .data wrapper
    enabled: isAuthenticated,
  })
}

export function useLogin() {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (response) => {
      // Backend returns { user, tokens } directly — no ApiResponse wrapper
      setTokens(response.tokens)
      setUser(response.user)
      navigate('/dashboard')
    },
    onError: (err: { message?: string }) => {
      toast.error(err.message ?? i18n.t('auth.toasts.loginFailed'))
    },
  })
}

export function useRegister() {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)

  return useMutation({
    mutationFn: ({ name, email, password }: { name: string; email: string; password: string }) =>
      authApi.register(name, email, password),
    onSuccess: (response) => {
      setTokens(response.tokens)
      setUser(response.user)
      navigate('/dashboard')
    },
    onError: (err: { message?: string }) => {
      toast.error(err.message ?? i18n.t('auth.toasts.registrationFailed'))
    },
  })
}

export function useLogout() {
  const navigate = useNavigate()
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const qc = useQueryClient()

  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearTokens()
      clearAuth()
      qc.clear()
      navigate('/login')
    },
  })
}
