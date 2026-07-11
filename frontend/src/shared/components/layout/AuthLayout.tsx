import { Link, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ThemeToggle } from '../ThemeToggle'
import { LanguageSelector } from '../LanguageSelector'

export function AuthLayout() {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-base flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
        <Link to="/" className="flex items-center gap-2.5">
          <DocnaLogo className="h-6 w-6" />
          <span className="font-display text-lg text-text-primary">Docna</span>
        </Link>
        <div className="flex items-center gap-1">
          <LanguageSelector />
          <ThemeToggle />
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <Outlet />
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 text-center text-xs text-text-tertiary">
        {t('authLayout.rights', { year: new Date().getFullYear() })} · <Link to="/privacy" className="hover:text-text-secondary transition-colors">{t('authLayout.privacy')}</Link>
        {' · '}
        <Link to="/terms" className="hover:text-text-secondary transition-colors">{t('authLayout.terms')}</Link>
      </div>
    </div>
  )
}

function DocnaLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
      <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="18" cy="18" r="4" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
      <path d="M16.5 18h3M18 16.5v3" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
