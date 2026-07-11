import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/shared/components/ui/tooltip'
import { queryClient } from '@/shared/lib/query-client'
import { useThemeStore } from '@/shared/stores/theme-store'

export function Providers({ children }: { children: React.ReactNode }) {
  const { resolvedTheme } = useThemeStore()

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={400}>
        {children}
        <Toaster
          theme={resolvedTheme}
          position="bottom-right"
          toastOptions={{
            classNames: {
              toast: 'bg-surface border-border text-text-primary font-sans text-sm',
              title: 'text-text-primary',
              description: 'text-text-secondary',
              actionButton: 'bg-accent text-accent-foreground',
              cancelButton: 'bg-elevated text-text-secondary',
              closeButton: 'bg-elevated border-border',
            },
          }}
        />
      </TooltipProvider>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
