import { Moon, Sun } from 'lucide-react'
import { Button } from './ui/button'
import { useThemeStore } from '@/shared/stores/theme-store'

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useThemeStore()

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className={className}
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      aria-label="Toggle theme"
    >
      {resolvedTheme === 'dark' ? (
        <Sun className="size-4" />
      ) : (
        <Moon className="size-4" />
      )}
    </Button>
  )
}
