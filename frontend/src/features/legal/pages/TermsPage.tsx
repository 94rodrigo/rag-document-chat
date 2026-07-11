import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

interface LegalSection {
  heading: string
  body: string
}

export function TermsPage() {
  const { t, i18n } = useTranslation()
  const sections = t('legal.terms.sections', { returnObjects: true }) as LegalSection[]
  const lastUpdated = new Intl.DateTimeFormat(i18n.language, { year: 'numeric', month: 'long', day: 'numeric' }).format(
    new Date(2026, 0, 1),
  )

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <h1 className="font-display text-4xl text-text-primary mb-2">{t('legal.terms.title')}</h1>
      <p className="text-xs text-text-tertiary mb-8">{t('legal.lastUpdated', { date: lastUpdated })}</p>

      <p className="text-sm text-text-secondary leading-relaxed mb-10">{t('legal.terms.intro')}</p>

      <div className="space-y-8">
        {sections.map((section) => (
          <section key={section.heading}>
            <h2 className="text-sm font-semibold text-text-primary mb-2">{section.heading}</h2>
            <p className="text-sm text-text-secondary leading-relaxed">{section.body}</p>
          </section>
        ))}
      </div>

      <p className="text-sm text-text-secondary mt-12 pt-8 border-t border-border-subtle">
        {t('legal.terms.contactPrompt')}{' '}
        <Link to="/contact" className="text-accent hover:underline">{t('legal.terms.contactLink')}</Link>
      </p>
    </div>
  )
}
