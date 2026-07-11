import { useTranslation } from 'react-i18next'
import { Button } from './ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu'
import { SUPPORTED_LANGUAGES, LANGUAGE_META, type SupportedLanguage } from '@/shared/i18n'

export function LanguageSelector({ className }: { className?: string }) {
  const { i18n, t } = useTranslation()
  const current = (i18n.resolvedLanguage ?? 'en') as SupportedLanguage

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className={className}
          aria-label={t('language.label')}
        >
          <span className="text-sm leading-none">{LANGUAGE_META[current].flag}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {SUPPORTED_LANGUAGES.map((code) => (
          <DropdownMenuItem
            key={code}
            onClick={() => i18n.changeLanguage(code)}
            className={code === current ? 'bg-elevated' : ''}
          >
            <span className="text-sm leading-none">{LANGUAGE_META[code].flag}</span>
            <span>{LANGUAGE_META[code].nativeName}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
