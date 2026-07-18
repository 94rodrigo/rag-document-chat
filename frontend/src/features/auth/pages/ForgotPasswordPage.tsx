import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { KeyRound, Settings, LifeBuoy } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { useAuthStore } from '@/shared/stores/auth-store'

const SUPPORT_EMAIL = 'support@citenest.example'

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="mb-8 text-center">
        <div className="h-12 w-12 rounded-2xl bg-elevated border border-border flex items-center justify-center mx-auto mb-5">
          <KeyRound className="size-5 text-text-tertiary" />
        </div>
        <h1 className="font-display text-3xl text-text-primary mb-1.5">{t('auth.forgotPasswordPage.title')}</h1>
        <p className="text-sm text-text-secondary">{t('auth.forgotPasswordPage.body')}</p>
      </div>

      <div className="space-y-3">
        {isAuthenticated && (
          <div className="rounded-lg border border-border bg-surface p-4">
            <p className="text-xs text-text-secondary mb-3">{t('auth.forgotPasswordPage.loggedInHint')}</p>
            <Button variant="outline" size="sm" className="w-full" asChild>
              <Link to="/settings">
                <Settings className="size-3.5" />
                {t('auth.forgotPasswordPage.goToSettings')}
              </Link>
            </Button>
          </div>
        )}

        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="text-xs text-text-secondary mb-3">{t('auth.forgotPasswordPage.supportHint')}</p>
          <Button variant="outline" size="sm" className="w-full" asChild>
            <a href={`mailto:${SUPPORT_EMAIL}`}>
              <LifeBuoy className="size-3.5" />
              {t('auth.forgotPasswordPage.contactSupport')}
            </a>
          </Button>
        </div>
      </div>

      <div className="mt-6 text-center text-sm text-text-secondary">
        <Link to="/login" className="text-accent hover:underline">
          {t('auth.forgotPasswordPage.backToSignIn')}
        </Link>
      </div>
    </motion.div>
  )
}
