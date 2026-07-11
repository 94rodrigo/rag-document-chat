import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'
import { Mail, Lock, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { makeLoginSchema, type LoginFormData } from '../schemas'
import { useLogin } from '../hooks/use-auth'

export function LoginPage() {
  const { t, i18n } = useTranslation()
  const login = useLogin()
  const loginSchema = useMemo(() => makeLoginSchema(t), [t, i18n.language])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({ resolver: zodResolver(loginSchema) })

  const onSubmit = (data: LoginFormData) => {
    login.mutate(data)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl text-text-primary mb-1.5">{t('auth.login.title')}</h1>
        <p className="text-sm text-text-secondary">{t('auth.login.subtitle')}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email">{t('auth.login.email')}</Label>
          <div className="relative">
            <Mail className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
            <Input
              id="email"
              type="email"
              placeholder={t('auth.login.emailPlaceholder')}
              className="ps-9"
              autoComplete="email"
              {...register('email')}
            />
          </div>
          {errors.email && (
            <p className="text-xs text-destructive">{errors.email.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">{t('auth.login.password')}</Label>
            <Link
              to="/forgot-password"
              className="text-xs text-text-tertiary hover:text-accent transition-colors"
            >
              {t('auth.login.forgotPassword')}
            </Link>
          </div>
          <div className="relative">
            <Lock className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              className="ps-9"
              autoComplete="current-password"
              {...register('password')}
            />
          </div>
          {errors.password && (
            <p className="text-xs text-destructive">{errors.password.message}</p>
          )}
        </div>

        {login.isError && (
          <p className="text-xs text-destructive text-center -mb-1" role="alert">
            {(login.error as { message?: string })?.message ?? t('auth.login.invalidCredentials')}
          </p>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={login.isPending}
        >
          {login.isPending ? (
            <><Loader2 className="size-4 animate-spin" /> {t('auth.login.signingIn')}</>
          ) : (
            t('auth.login.signIn')
          )}
        </Button>
      </form>

      <div className="mt-6 text-center text-sm text-text-secondary">
        {t('auth.login.noAccount')}{' '}
        <Link to="/register" className="text-accent hover:underline">
          {t('auth.login.createOne')}
        </Link>
      </div>
    </motion.div>
  )
}
