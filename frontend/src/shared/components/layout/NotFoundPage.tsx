import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Compass } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { ThemeToggle } from '../ThemeToggle'
import { LanguageSelector } from '../LanguageSelector'

function CitenestLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
      <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="18" cy="18" r="4" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
      <path d="M16.5 18h3M18 16.5v3" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-base flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
        <Link to="/" className="flex items-center gap-2.5">
          <CitenestLogo className="h-6 w-6" />
          <span className="font-display text-lg text-text-primary">Citenest</span>
        </Link>
        <div className="flex items-center gap-1">
          <LanguageSelector />
          <ThemeToggle />
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-16 text-center">
        <div className="h-14 w-14 rounded-2xl bg-elevated border border-border flex items-center justify-center mb-6">
          <Compass className="size-6 text-text-tertiary" />
        </div>
        <p className="font-mono text-xs text-accent uppercase tracking-widest mb-3">404</p>
        <h1 className="font-display text-3xl text-text-primary mb-2">{t('errors.notFound.title')}</h1>
        <p className="text-sm text-text-secondary max-w-sm mb-8">{t('errors.notFound.body')}</p>
        <Button asChild>
          <Link to="/">{t('errors.notFound.backHome')}</Link>
        </Button>
      </div>
    </div>
  )
}
