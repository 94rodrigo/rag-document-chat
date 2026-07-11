import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'
import { Mail, Lock, User, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { makeRegisterSchema, type RegisterFormData } from '../schemas'
import { useRegister } from '../hooks/use-auth'

export function RegisterPage() {
  const { t, i18n } = useTranslation()
  const register_ = useRegister()
  const registerSchema = useMemo(() => makeRegisterSchema(t), [t, i18n.language])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({ resolver: zodResolver(registerSchema) })

  const onSubmit = (data: RegisterFormData) => {
    register_.mutate({ name: data.name, email: data.email, password: data.password })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl text-text-primary mb-1.5">{t('auth.register.title')}</h1>
        <p className="text-sm text-text-secondary">{t('auth.register.subtitle')}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="name">{t('auth.register.fullName')}</Label>
          <div className="relative">
            <User className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
            <Input
              id="name"
              placeholder={t('auth.register.fullNamePlaceholder')}
              className="ps-9"
              autoComplete="name"
              {...register('name')}
            />
          </div>
          {errors.name && (
            <p className="text-xs text-destructive">{errors.name.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email">{t('auth.register.email')}</Label>
          <div className="relative">
            <Mail className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
            <Input
              id="email"
              type="email"
              placeholder={t('auth.register.emailPlaceholder')}
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
          <Label htmlFor="password">{t('auth.register.password')}</Label>
          <div className="relative">
            <Lock className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
            <Input
              id="password"
              type="password"
              placeholder={t('auth.register.passwordPlaceholder')}
              className="ps-9"
              autoComplete="new-password"
              {...register('password')}
            />
          </div>
          {errors.password && (
            <p className="text-xs text-destructive">{errors.password.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="confirmPassword">{t('auth.register.confirmPassword')}</Label>
          <div className="relative">
            <Lock className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-text-tertiary" />
            <Input
              id="confirmPassword"
              type="password"
              placeholder={t('auth.register.confirmPasswordPlaceholder')}
              className="ps-9"
              autoComplete="new-password"
              {...register('confirmPassword')}
            />
          </div>
          {errors.confirmPassword && (
            <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
          )}
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={register_.isPending}
        >
          {register_.isPending ? (
            <><Loader2 className="size-4 animate-spin" /> {t('auth.register.creatingAccount')}</>
          ) : (
            t('auth.register.createAccount')
          )}
        </Button>

        <p className="text-[11px] text-text-tertiary text-center">
          {t('auth.register.agreementPrefix')}{' '}
          <Link to="/terms" className="text-text-secondary hover:text-text-primary underline">{t('auth.register.terms')}</Link>
          {' '}{t('auth.register.agreementAnd')}{' '}
          <Link to="/privacy" className="text-text-secondary hover:text-text-primary underline">{t('auth.register.privacyPolicy')}</Link>
        </p>
      </form>

      <div className="mt-6 text-center text-sm text-text-secondary">
        {t('auth.register.haveAccount')}{' '}
        <Link to="/login" className="text-accent hover:underline">
          {t('auth.register.signIn')}
        </Link>
      </div>
    </motion.div>
  )
}
