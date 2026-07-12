import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { useMemo, useState } from 'react'
import { ArrowLeft, Moon, Sun, Monitor, Loader2, Trash2, AlertTriangle } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { useAuthStore } from '@/shared/stores/auth-store'
import { useThemeStore } from '@/shared/stores/theme-store'
import { usersApi } from '@/shared/lib/api-client'
import { makeChangePasswordSchema, type ChangePasswordFormData } from '@/features/auth/schemas'
import { DeleteAccountDialog } from '../components/DeleteAccountDialog'
import type { User } from '@/shared/types'

type NotificationField = 'notifyDocumentProcessing' | 'notifyWeeklySummary' | 'notifyProductUpdates'

const notificationFields: NotificationField[] = [
  'notifyDocumentProcessing',
  'notifyWeeklySummary',
  'notifyProductUpdates',
]

type Theme = 'dark' | 'light' | 'system'

const themeIcons: Record<Theme, typeof Moon> = { dark: Moon, light: Sun, system: Monitor }

function Section({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section className="grid grid-cols-1 md:grid-cols-[240px_1fr] gap-8 py-8 border-b border-border">
      <div>
        <h2 className="text-sm font-semibold text-text-primary mb-1">{title}</h2>
        {description && <p className="text-xs text-text-secondary">{description}</p>}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  )
}

export function SettingsPage() {
  const { t, i18n } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const { theme, setTheme } = useThemeStore()

  const themes: { value: Theme; label: string }[] = [
    { value: 'dark', label: t('settings.appearance.dark') },
    { value: 'light', label: t('settings.appearance.light') },
    { value: 'system', label: t('settings.appearance.system') },
  ]

  const updateProfile = useMutation({
    mutationFn: (data: { name: string }) => usersApi.updateProfile(data),
    onSuccess: (updatedUser) => {
      setUser(updatedUser)
      toast.success(t('settings.toasts.profileUpdated'))
    },
    onError: () => toast.error(t('settings.toasts.profileUpdateFailed')),
  })

  // i18n.language rebuilds the schema with translated error messages on a language switch.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const changePasswordSchema = useMemo(() => makeChangePasswordSchema(t), [t, i18n.language])

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<ChangePasswordFormData>({
      resolver: zodResolver(changePasswordSchema),
    })

  const changePassword = useMutation({
    mutationFn: (data: { currentPassword: string; newPassword: string }) =>
      usersApi.changePassword(data.currentPassword, data.newPassword),
    onSuccess: () => toast.success(t('settings.toasts.passwordChanged')),
    onError: () => toast.error(t('settings.toasts.passwordChangeFailed')),
  })

  const onPasswordSubmit = (data: ChangePasswordFormData) => {
    changePassword.mutate({
      currentPassword: data.currentPassword,
      newPassword: data.newPassword,
    })
  }

  // Separate from `updateProfile` so flipping a switch doesn't fire the
  // "Profile updated" toast meant for the explicit Save button.
  const updateNotificationPref = useMutation({
    mutationFn: (data: Partial<Pick<User, NotificationField>>) => usersApi.updateProfile(data),
    onSuccess: (updatedUser) => setUser(updatedUser),
    onError: () => toast.error(t('settings.toasts.profileUpdateFailed')),
  })

  const notificationItems = t('settings.notifications.items', { returnObjects: true }) as { label: string; desc: string }[]

  const [deleteAccountOpen, setDeleteAccountOpen] = useState(false)

  return (
    <div className="min-h-screen bg-base">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center gap-4 px-8 py-4 border-b border-border bg-base/80 glass">
        <Button variant="ghost" size="icon-sm" asChild>
          <Link to="/dashboard"><ArrowLeft className="size-4" /></Link>
        </Button>
        <div>
          <h1 className="font-display text-lg text-text-primary">{t('settings.title')}</h1>
          <p className="text-xs text-text-tertiary">{t('settings.subtitle')}</p>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-8 pb-16">

        {/* Profile */}
        <Section
          title={t('settings.profile.title')}
          description={t('settings.profile.desc')}
        >
          <div className="space-y-1.5">
            <Label>{t('settings.profile.fullName')}</Label>
            <Input defaultValue={user?.name} id="name" />
          </div>
          <div className="space-y-1.5">
            <Label>{t('settings.profile.email')}</Label>
            <Input value={user?.email} disabled />
            <p className="text-[11px] text-text-tertiary">{t('settings.profile.emailHint')}</p>
          </div>
          <Button
            size="sm"
            onClick={() => {
              const nameEl = document.getElementById('name') as HTMLInputElement
              if (nameEl?.value) updateProfile.mutate({ name: nameEl.value })
            }}
            disabled={updateProfile.isPending}
          >
            {updateProfile.isPending ? <><Loader2 className="size-3.5 animate-spin" /> {t('settings.profile.saving')}</> : t('settings.profile.save')}
          </Button>
        </Section>

        {/* Appearance */}
        <Section
          title={t('settings.appearance.title')}
          description={t('settings.appearance.desc')}
        >
          <div className="flex items-center gap-2">
            {themes.map(({ value, label }) => {
              const Icon = themeIcons[value]
              return (
                <button
                  key={value}
                  onClick={() => setTheme(value)}
                  className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm transition-colors ${
                    theme === value
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border bg-surface text-text-secondary hover:bg-elevated'
                  }`}
                >
                  <Icon className="size-4" />
                  {label}
                </button>
              )
            })}
          </div>
        </Section>

        {/* Password */}
        <Section
          title={t('settings.password.title')}
          description={t('settings.password.desc')}
        >
          <form onSubmit={handleSubmit(onPasswordSubmit)} className="space-y-3">
            <div className="space-y-1.5">
              <Label>{t('settings.password.current')}</Label>
              <Input type="password" placeholder="••••••••" {...register('currentPassword')} />
              {errors.currentPassword && (
                <p className="text-xs text-destructive">{errors.currentPassword.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('settings.password.new')}</Label>
              <Input type="password" placeholder={t('settings.password.newPlaceholder')} {...register('newPassword')} />
              {errors.newPassword && (
                <p className="text-xs text-destructive">{errors.newPassword.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('settings.password.confirm')}</Label>
              <Input type="password" placeholder={t('settings.password.confirmPlaceholder')} {...register('confirmNewPassword')} />
              {errors.confirmNewPassword && (
                <p className="text-xs text-destructive">{errors.confirmNewPassword.message}</p>
              )}
            </div>
            <Button size="sm" type="submit" disabled={isSubmitting || changePassword.isPending}>
              {changePassword.isPending ? <><Loader2 className="size-3.5 animate-spin" /> {t('settings.password.changing')}</> : t('settings.password.change')}
            </Button>
          </form>
        </Section>

        {/* Notifications */}
        <Section
          title={t('settings.notifications.title')}
          description={t('settings.notifications.desc')}
        >
          {notificationItems.map(({ label, desc }, i) => {
            const field = notificationFields[i]
            return (
              <div key={label} className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-text-primary">{label}</p>
                  <p className="text-xs text-text-secondary mt-0.5">{desc}</p>
                </div>
                <Switch
                  checked={user?.[field] ?? false}
                  onCheckedChange={(checked) => updateNotificationPref.mutate({ [field]: checked })}
                />
              </div>
            )
          })}
        </Section>

        {/* Danger zone */}
        <section className="pt-8">
          <h2 className="text-sm font-semibold text-destructive mb-4">{t('settings.danger.title')}</h2>
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 flex items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="size-4 text-destructive shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-text-primary">{t('settings.danger.deleteAccount')}</p>
                <p className="text-xs text-text-secondary mt-0.5">
                  {t('settings.danger.warning')}
                </p>
              </div>
            </div>
            <Button variant="destructive" size="sm" onClick={() => setDeleteAccountOpen(true)}>
              <Trash2 className="size-3.5" />
              {t('settings.danger.delete')}
            </Button>
          </div>
        </section>
      </div>

      <DeleteAccountDialog open={deleteAccountOpen} onOpenChange={setDeleteAccountOpen} />
    </div>
  )
}
