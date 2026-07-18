import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'dark' | 'light' | 'system'

interface ThemeState {
  theme: Theme
  resolvedTheme: 'dark' | 'light'
  setTheme: (theme: Theme) => void
}

function getSystemTheme(): 'dark' | 'light' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(resolved: 'dark' | 'light') {
  const root = document.documentElement
  root.classList.remove('dark', 'light')
  root.classList.add(resolved)
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'dark',
      resolvedTheme: 'dark',

      setTheme: (theme) => {
        const resolved = theme === 'system' ? getSystemTheme() : theme
        applyTheme(resolved)
        set({ theme, resolvedTheme: resolved })
      },
    }),
    {
      name: 'citenest-theme',
      onRehydrateStorage: () => (state) => {
        if (!state) return
        const resolved =
          state.theme === 'system' ? getSystemTheme() : state.theme
        applyTheme(resolved)
        state.resolvedTheme = resolved
      },
    },
  ),
)

// initialize on first load
const initial = useThemeStore.getState()
applyTheme(initial.resolvedTheme)
