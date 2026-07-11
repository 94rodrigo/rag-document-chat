import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Mail, Briefcase, LifeBuoy } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'

const SALES_EMAIL = 'sales@docna.example'
const SUPPORT_EMAIL = 'support@docna.example'

function ContactCard({
  icon: Icon,
  title,
  body,
  cta,
  email,
}: {
  icon: typeof Mail
  title: string
  body: string
  cta: string
  email: string
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-6 flex flex-col">
      <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
        <Icon className="size-5 text-accent" />
      </div>
      <h2 className="font-semibold text-text-primary mb-2">{title}</h2>
      <p className="text-sm text-text-secondary leading-relaxed mb-5 flex-1">{body}</p>
      <Button variant="outline" asChild className="w-full">
        <a href={`mailto:${email}`}>
          <Mail className="size-3.5" />
          {cta}
        </a>
      </Button>
    </div>
  )
}

export function ContactPage() {
  const { t } = useTranslation()

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <div className="text-center mb-12">
        <h1 className="font-display text-4xl text-text-primary mb-3">{t('contact.title')}</h1>
        <p className="text-sm text-text-secondary max-w-md mx-auto">{t('contact.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ContactCard
          icon={Briefcase}
          title={t('contact.sales.title')}
          body={t('contact.sales.body')}
          cta={t('contact.sales.cta')}
          email={SALES_EMAIL}
        />
        <ContactCard
          icon={LifeBuoy}
          title={t('contact.support.title')}
          body={t('contact.support.body')}
          cta={t('contact.support.cta')}
          email={SUPPORT_EMAIL}
        />
      </div>

      <div className="text-center mt-10">
        <Link to="/" className="text-sm text-accent hover:underline">{t('contact.backHome')}</Link>
      </div>
    </div>
  )
}
