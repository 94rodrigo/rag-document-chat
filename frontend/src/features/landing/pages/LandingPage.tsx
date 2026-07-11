import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  FileText, Zap, Shield, Search, ArrowRight, Check, MessageSquare, ChevronRight
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { ThemeToggle } from '@/shared/components/ThemeToggle'
import { LanguageSelector } from '@/shared/components/LanguageSelector'

// ─── Animated components ─────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] },
  }),
}

// ─── Logo ─────────────────────────────────────────────────────────────────────

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <DocnaIcon className="h-7 w-7" />
      <span className="font-display text-xl text-text-primary tracking-tight">Docna</span>
    </div>
  )
}

function DocnaIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect x="3" y="2" width="13" height="16" rx="2" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
      <path d="M7 7h5M7 10h7M7 13h4" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="18" cy="18" r="4" className="fill-accent/20 stroke-accent" strokeWidth="1.5" />
      <path d="M16.5 18h3M18 16.5v3" className="stroke-accent" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

// ─── Mock chat visualization ──────────────────────────────────────────────────

function HeroVisual() {
  const { t } = useTranslation()
  const demoDocs = t('landing.demo.documents', { returnObjects: true }) as string[]

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      {/* Glow backdrop */}
      <div
        className="absolute inset-0 -z-10 rounded-2xl opacity-30 blur-3xl"
        style={{ background: 'radial-gradient(ellipse at center, hsl(var(--accent) / 0.3), transparent 70%)' }}
      />

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="rounded-xl border border-border bg-surface shadow-2xl overflow-hidden"
      >
        {/* Window chrome */}
        <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border bg-elevated">
          <div className="h-2.5 w-2.5 rounded-full bg-red-500/60" />
          <div className="h-2.5 w-2.5 rounded-full bg-amber-500/60" />
          <div className="h-2.5 w-2.5 rounded-full bg-green-500/60" />
          <span className="ml-3 text-xs text-text-tertiary font-mono">docna — annual-report-2024.pdf</span>
        </div>

        <div className="grid grid-cols-[200px_1fr] min-h-[360px]">
          {/* Left panel — doc list */}
          <div className="border-r border-border bg-base p-3 space-y-1">
            <p className="text-[10px] font-medium text-text-tertiary uppercase tracking-wider mb-2 px-2">{t('landing.demo.documentsLabel')}</p>
            {demoDocs.map((name, i) => (
              <div
                key={name}
                className={`flex items-center gap-2 rounded px-2 py-1.5 text-xs cursor-pointer ${
                  i === 0 ? 'bg-accent/10 text-accent' : 'text-text-secondary hover:bg-elevated'
                }`}
              >
                <FileText className="size-3 shrink-0" />
                <span className="truncate">{name}</span>
              </div>
            ))}
          </div>

          {/* Chat panel */}
          <div className="flex flex-col">
            <div className="flex-1 p-4 space-y-4 overflow-hidden">
              {/* User message */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 }}
                className="flex justify-end"
              >
                <div className="bg-accent/15 border border-accent/20 rounded-lg px-3 py-2 text-xs text-text-primary max-w-[80%]">
                  {t('landing.demo.question')}
                </div>
              </motion.div>

              {/* Assistant response */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.0 }}
              >
                <div className="flex items-start gap-2">
                  <div className="h-5 w-5 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-[8px] text-accent font-display font-bold">D</span>
                  </div>
                  <div className="bg-elevated border border-border rounded-lg px-3 py-2 text-xs text-text-primary max-w-[85%]">
                    {t('landing.demo.answer', { growth: '23.4%', current: '$4.2B', previous: '$3.4B' })}{' '}
                    <span className="citation-ref">1</span>{' '}
                    {t('landing.demo.answerContinued')}{' '}
                    <span className="citation-ref">2</span>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Query box */}
            <div className="p-3 border-t border-border">
              <div className="flex items-center gap-2 rounded-lg border border-border bg-elevated px-3 py-2">
                <span className="text-xs text-text-tertiary flex-1">{t('landing.demo.inputPlaceholder')}</span>
                <div className="h-5 w-5 rounded bg-accent/20 flex items-center justify-center">
                  <ArrowRight className="size-3 text-accent" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ─── Features ─────────────────────────────────────────────────────────────────

const featureIcons = [Search, MessageSquare, Zap, Shield]

// ─── Pricing ──────────────────────────────────────────────────────────────────

const planPricing = [
  { price: 0, highlighted: false },
  { price: 29, highlighted: true },
  { price: null, highlighted: false },
]

interface LandingFeature { title: string; desc: string }
interface LandingPlan { name: string; cta: string; features: string[] }

// ─── Page ─────────────────────────────────────────────────────────────────────

export function LandingPage() {
  const { t } = useTranslation()
  const features = t('landing.features.items', { returnObjects: true }) as unknown as LandingFeature[]
  const plans = t('landing.pricing.plans', { returnObjects: true }) as unknown as LandingPlan[]

  return (
    <div className="min-h-screen bg-base">
      {/* Nav */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 lg:px-16 py-4 border-b border-border-subtle bg-base/80 glass">
        <Logo />
        <div className="hidden md:flex items-center gap-6 text-sm text-text-secondary">
          <a href="#features" className="hover:text-text-primary transition-colors">{t('landing.nav.features')}</a>
          <a href="#pricing" className="hover:text-text-primary transition-colors">{t('landing.nav.pricing')}</a>
        </div>
        <div className="flex items-center gap-2">
          <LanguageSelector />
          <ThemeToggle />
          <Button variant="ghost" size="sm" asChild>
            <Link to="/login">{t('landing.nav.signIn')}</Link>
          </Button>
          <Button size="sm" asChild>
            <Link to="/register">
              {t('landing.nav.startFree')} <ChevronRight className="size-3.5" />
            </Link>
          </Button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-6 lg:px-16 pt-24 pb-20 overflow-hidden">
        {/* Decorative grid */}
        <div
          className="absolute inset-0 -z-10 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(hsl(var(--text-primary)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--text-primary)) 1px, transparent 1px)`,
            backgroundSize: '60px 60px',
          }}
        />

        {/* Radial glow */}
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 -z-10 w-[600px] h-[400px] opacity-10 blur-3xl rounded-full"
          style={{ background: 'hsl(var(--accent))' }}
        />

        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={0}
            className="flex justify-center mb-6"
          >
            <Badge variant="default" className="text-xs px-3 py-1">
              <Zap className="size-3 mr-1" /> {t('landing.hero.badge')}
            </Badge>
          </motion.div>

          <motion.h1
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={1}
            className="font-display text-5xl lg:text-7xl text-center text-text-primary leading-[1.05] tracking-tight mb-6 text-balance"
          >
            {t('landing.hero.titlePart1')}{' '}
            <span className="italic gradient-text">{t('landing.hero.titleEmphasis')}</span>
            {' '}{t('landing.hero.titlePart2')}
          </motion.h1>

          <motion.p
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={2}
            className="text-center text-lg text-text-secondary max-w-xl mx-auto mb-10 text-balance"
          >
            {t('landing.hero.subtitle')}
          </motion.p>

          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={3}
            className="flex items-center justify-center gap-3 mb-20"
          >
            <Button size="lg" asChild>
              <Link to="/register">
                {t('landing.hero.getStarted')} <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/login">{t('landing.hero.signIn')}</Link>
            </Button>
          </motion.div>

          <HeroVisual />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 lg:px-16 py-24 border-t border-border-subtle">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            className="text-center mb-14"
          >
            <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">{t('landing.features.eyebrow')}</p>
            <h2 className="font-display text-4xl text-text-primary">
              {t('landing.features.heading')}
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border rounded-xl overflow-hidden border border-border">
            {features.map((f, i) => {
              const Icon = featureIcons[i]
              return (
                <motion.div
                  key={f.title}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true }}
                  variants={fadeUp}
                  custom={i * 0.5}
                  className="bg-surface p-8"
                >
                  <div className="h-10 w-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
                    <Icon className="size-5 text-accent" />
                  </div>
                  <h3 className="font-semibold text-text-primary mb-2">{f.title}</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">{f.desc}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-6 lg:px-16 py-24 border-t border-border-subtle bg-elevated/40">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            className="text-center mb-14"
          >
            <p className="text-xs font-mono text-accent uppercase tracking-widest mb-3">{t('landing.pricing.eyebrow')}</p>
            <h2 className="font-display text-4xl text-text-primary">{t('landing.pricing.heading')}</h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {plans.map((plan, i) => {
              const pricing = planPricing[i]
              return (
                <motion.div
                  key={plan.name}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true }}
                  variants={fadeUp}
                  custom={i * 0.5}
                  className={`rounded-xl border p-6 flex flex-col ${
                    pricing.highlighted
                      ? 'border-accent bg-accent/5 accent-glow'
                      : 'border-border bg-surface'
                  }`}
                >
                  {pricing.highlighted && (
                    <Badge className="self-start mb-4 text-[10px]">{t('landing.pricing.mostPopular')}</Badge>
                  )}
                  <h3 className="font-display text-xl text-text-primary mb-1">{plan.name}</h3>
                  <div className="mb-6">
                    {pricing.price !== null ? (
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-semibold text-text-primary">${pricing.price}</span>
                        <span className="text-sm text-text-secondary">{t('landing.pricing.perMonth')}</span>
                      </div>
                    ) : (
                      <span className="text-lg text-text-secondary">{t('landing.pricing.customPricing')}</span>
                    )}
                  </div>
                  <ul className="space-y-2.5 mb-8 flex-1">
                    {plan.features.map((feat) => (
                      <li key={feat} className="flex items-center gap-2 text-sm text-text-secondary">
                        <Check className="size-3.5 text-accent shrink-0" />
                        {feat}
                      </li>
                    ))}
                  </ul>
                  <Button
                    variant={pricing.highlighted ? 'default' : 'outline'}
                    className="w-full"
                    asChild
                  >
                    <Link to={pricing.price === null ? '/contact' : '/register'}>
                      {plan.cta}
                    </Link>
                  </Button>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 lg:px-16 py-24 border-t border-border-subtle text-center">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeUp}
          className="max-w-xl mx-auto"
        >
          <h2 className="font-display text-4xl text-text-primary mb-4">
            {t('landing.cta.heading')}
          </h2>
          <p className="text-text-secondary mb-8">
            {t('landing.cta.body')}
          </p>
          <Button size="lg" asChild>
            <Link to="/register">
              {t('landing.cta.button')} <ArrowRight className="size-4" />
            </Link>
          </Button>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="px-6 lg:px-16 py-8 border-t border-border-subtle flex flex-col md:flex-row items-center justify-between gap-4">
        <Logo />
        <p className="text-xs text-text-tertiary">{t('landing.footer.rights', { year: new Date().getFullYear() })}</p>
        <div className="flex items-center gap-4 text-xs text-text-tertiary">
          <Link to="/privacy" className="hover:text-text-secondary transition-colors">{t('landing.footer.privacy')}</Link>
          <Link to="/terms" className="hover:text-text-secondary transition-colors">{t('landing.footer.terms')}</Link>
        </div>
      </footer>
    </div>
  )
}
