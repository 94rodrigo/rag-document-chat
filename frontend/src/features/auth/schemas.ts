import { z } from 'zod'
import type { TFunction } from 'i18next'

export function makeLoginSchema(t: TFunction) {
  return z.object({
    email: z.string().email(t('auth.validation.invalidEmail')),
    password: z.string().min(1, t('auth.validation.passwordRequired')),
  })
}

export function makeRegisterSchema(t: TFunction) {
  return z.object({
    name: z.string().min(2, t('auth.validation.nameMin')),
    email: z.string().email(t('auth.validation.invalidEmail')),
    password: z
      .string()
      .min(8, t('auth.validation.passwordMin'))
      .regex(/[A-Z]/, t('auth.validation.passwordUppercase'))
      .regex(/[0-9]/, t('auth.validation.passwordNumber')),
    confirmPassword: z.string(),
  }).refine((d) => d.password === d.confirmPassword, {
    message: t('auth.validation.passwordsMismatch'),
    path: ['confirmPassword'],
  })
}

export function makeChangePasswordSchema(t: TFunction) {
  return z.object({
    currentPassword: z.string().min(1, t('auth.validation.currentPasswordRequired')),
    newPassword: z
      .string()
      .min(8, t('auth.validation.passwordMin'))
      .regex(/[A-Z]/, t('auth.validation.passwordUppercase'))
      .regex(/[0-9]/, t('auth.validation.passwordNumber')),
    confirmNewPassword: z.string(),
  }).refine((d) => d.newPassword === d.confirmNewPassword, {
    message: t('auth.validation.passwordsMismatch'),
    path: ['confirmNewPassword'],
  })
}

export type LoginFormData = z.infer<ReturnType<typeof makeLoginSchema>>
export type RegisterFormData = z.infer<ReturnType<typeof makeRegisterSchema>>
export type ChangePasswordFormData = z.infer<ReturnType<typeof makeChangePasswordSchema>>
