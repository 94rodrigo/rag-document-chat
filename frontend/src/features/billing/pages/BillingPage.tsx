import { Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Zap, Check, ExternalLink, AlertTriangle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Progress } from '@/shared/components/ui/progress'
import { Skeleton } from '@/shared/components/ui/skeleton'
import { billingApi } from '@/shared/lib/api-client'
import { useAuthStore } from '@/shared/stores/auth-store'

function UsageBar({ label, used, limit, unit = '' }: { label: string; used: number; limit: number; unit?: string }) {
  const unlimited = limit < 0
  const pct = unlimited ? 0 : Math.min((used / limit) * 100, 100)
  const critical = !unlimited && pct >= 90

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5 text-xs">
        <span className="text-text-secondary">{label}</span>
        <span className={critical ? 'text-destructive font-medium' : 'text-text-tertiary'}>
          {used.toLocaleString()}{unit} / {unlimited ? '∞' : `${limit.toLocaleString()}${unit}`}
        </span>
      </div>
      <Progress
        value={pct}
        className={critical ? '[&>div]:bg-destructive' : ''}
      />
    </div>
  )
}

export function BillingPage() {
  const { t, i18n } = useTranslation()
  const user = useAuthStore((s) => s.user)

  const { data: plansData, isLoading: plansLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: () => billingApi.getPlans(),
  })

  const { data: subscriptionData } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => billingApi.getSubscription(),
  })

  const { data: usageData } = useQuery({
    queryKey: ['usage'],
    queryFn: () => billingApi.getUsage(),
  })

  const checkout = useMutation({
    mutationFn: (planId: string) => billingApi.createCheckout(planId),
    onSuccess: ({ url }) => window.location.href = url,
    onError: () => toast.error(t('billing.toasts.checkoutFailed')),
  })

  const portal = useMutation({
    mutationFn: () => billingApi.getPortalUrl(),
    onSuccess: ({ url }) => window.open(url, '_blank'),
    onError: () => toast.error(t('billing.toasts.portalFailed')),
  })

  const planColors: Record<string, string> = {
    free: 'secondary',
    pro: 'default',
    enterprise: 'default',
  }

  return (
    <div className="min-h-screen bg-base">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center gap-4 px-8 py-4 border-b border-border bg-base/80 glass">
        <Button variant="ghost" size="icon-sm" asChild>
          <Link to="/dashboard"><ArrowLeft className="size-4" /></Link>
        </Button>
        <div>
          <h1 className="font-display text-lg text-text-primary">{t('billing.title')}</h1>
          <p className="text-xs text-text-tertiary">{t('billing.subtitle')}</p>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-8 py-8 space-y-8">

        {/* Current plan */}
        <section className="rounded-xl border border-border bg-surface p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs text-text-tertiary uppercase tracking-wider mb-1">{t('billing.currentPlan')}</p>
              <div className="flex items-center gap-3">
                <h2 className="font-display text-2xl text-text-primary capitalize">{user?.plan ?? 'Free'}</h2>
                <Badge variant={(planColors[user?.plan ?? 'free'] as 'default' | 'secondary') ?? 'secondary'}>
                  {subscriptionData?.status ?? t('billing.active')}
                </Badge>
              </div>
              {subscriptionData?.currentPeriodEnd && (
                <p className="text-xs text-text-secondary mt-1">
                  {subscriptionData.cancelAtPeriodEnd
                    ? t('billing.cancelsOn', { date: new Date(subscriptionData.currentPeriodEnd).toLocaleDateString(i18n.language, { month: 'long', day: 'numeric', year: 'numeric' }) })
                    : t('billing.renewsOn', { date: new Date(subscriptionData.currentPeriodEnd).toLocaleDateString(i18n.language, { month: 'long', day: 'numeric', year: 'numeric' }) })
                  }
                </p>
              )}
            </div>
            {subscriptionData && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => portal.mutate()}
                disabled={portal.isPending}
              >
                {portal.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <ExternalLink className="size-3.5" />}
                {t('billing.manageSubscription')}
              </Button>
            )}
          </div>

          {/* Usage */}
          {usageData && (
            <div className="mt-6 pt-6 border-t border-border space-y-4">
              <p className="text-xs font-medium text-text-secondary">{t('billing.usageTitle')}</p>
              <UsageBar
                label={t('billing.documents')}
                used={usageData.documentsUsed}
                limit={usageData.documentsLimit}
              />
              <UsageBar
                label={t('billing.queries')}
                used={usageData.queriesUsed}
                limit={usageData.queriesLimit}
              />
              <UsageBar
                label={t('billing.storage')}
                used={parseFloat(((usageData.storageUsedBytes ?? 0) / 1e6).toFixed(1))}
                limit={(usageData.storageLimitBytes ?? 0) < 0 ? -1 : parseFloat(((usageData.storageLimitBytes ?? 0) / 1e6).toFixed(1))}
                unit=" MB"
              />
            </div>
          )}
        </section>

        {/* Plans */}
        <section>
          <h2 className="font-display text-xl text-text-primary mb-4">{t('billing.plansHeading')}</h2>

          {plansLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-64 w-full" />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {plansData?.map((plan, i) => {
                const isCurrentPlan = plan.id === user?.plan
                const highlighted = plan.name.toLowerCase() === 'pro'

                return (
                  <motion.div
                    key={plan.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className={`rounded-xl border p-5 flex flex-col ${
                      isCurrentPlan
                        ? 'border-accent bg-accent/5'
                        : highlighted
                        ? 'border-border/60 bg-surface'
                        : 'border-border bg-surface'
                    }`}
                  >
                    {isCurrentPlan && (
                      <Badge className="self-start mb-3 text-[10px]">{t('billing.currentPlan')}</Badge>
                    )}
                    <h3 className="font-display text-lg text-text-primary mb-1">{plan.name}</h3>
                    <div className="mb-4">
                      <span className="text-2xl font-semibold text-text-primary">${plan.price}</span>
                      <span className="text-xs text-text-secondary">{t('billing.perInterval', { interval: plan.interval })}</span>
                    </div>
                    <ul className="space-y-2 mb-6 flex-1">
                      {plan.features.map((feat) => (
                        <li key={feat} className="flex items-center gap-1.5 text-xs text-text-secondary">
                          <Check className="size-3 text-accent shrink-0" />
                          {feat}
                        </li>
                      ))}
                    </ul>
                    <Button
                      variant={isCurrentPlan ? 'outline' : 'default'}
                      size="sm"
                      className="w-full"
                      disabled={isCurrentPlan || checkout.isPending}
                      onClick={() => !isCurrentPlan && checkout.mutate(plan.id)}
                    >
                      {checkout.isPending && !isCurrentPlan ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : isCurrentPlan ? (
                        t('billing.currentPlan')
                      ) : (
                        <>
                          <Zap className="size-3.5" />
                          {user?.plan === 'free' ? t('billing.upgrade') : t('billing.switchPlan')}
                        </>
                      )}
                    </Button>
                  </motion.div>
                )
              })}
            </div>
          )}
        </section>

        {/* Cancel warning */}
        {subscriptionData?.cancelAtPeriodEnd && (
          <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
            <AlertTriangle className="size-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-text-primary">{t('billing.endingWarning.title')}</p>
              <p className="text-xs text-text-secondary mt-0.5">
                {t('billing.endingWarning.body')}
              </p>
              <Button size="sm" variant="outline" className="mt-3" onClick={() => portal.mutate()}>
                {t('billing.endingWarning.resume')}
              </Button>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
