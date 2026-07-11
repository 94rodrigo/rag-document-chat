import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,    // 2 min
      gcTime: 1000 * 60 * 10,      // 10 min
      retry: (failureCount, error) => {
        const apiError = error as { statusCode?: number }
        if (apiError?.statusCode && apiError.statusCode < 500) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})
