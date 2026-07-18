import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import pt from './locales/pt.json'
import es from './locales/es.json'
import fr from './locales/fr.json'
import de from './locales/de.json'
import ar from './locales/ar.json'

export const SUPPORTED_LANGUAGES = ['en', 'pt', 'es', 'fr', 'de', 'ar'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

export const RTL_LANGUAGES: SupportedLanguage[] = ['ar']

export const LANGUAGE_META: Record<SupportedLanguage, { nativeName: string; flag: string }> = {
  en: { nativeName: 'English', flag: '🇬🇧' },
  pt: { nativeName: 'Português', flag: '🇵🇹' },
  es: { nativeName: 'Español', flag: '🇪🇸' },
  fr: { nativeName: 'Français', flag: '🇫🇷' },
  de: { nativeName: 'Deutsch', flag: '🇩🇪' },
  ar: { nativeName: 'العربية', flag: '🇸🇦' },
}

function applyDirection() {
  // i18n.language keeps the raw detected/selected code (e.g. "ar-SA"); resolvedLanguage
  // is the stripped code actually used for resource lookup (e.g. "ar") — direction must
  // follow the resolved code, not the raw one.
  const resolved = (i18n.resolvedLanguage ?? i18n.language.split('-')[0]) as SupportedLanguage
  const isRtl = RTL_LANGUAGES.includes(resolved)
  document.documentElement.dir = isRtl ? 'rtl' : 'ltr'
  document.documentElement.lang = i18n.language
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      pt: { translation: pt },
      es: { translation: es },
      fr: { translation: fr },
      de: { translation: de },
      ar: { translation: ar },
    },
    supportedLngs: [...SUPPORTED_LANGUAGES],
    fallbackLng: 'en',
    load: 'languageOnly',
    nonExplicitSupportedLngs: true,
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'citenest-language',
      caches: ['localStorage'],
    },
    interpolation: {
      escapeValue: false,
    },
  })

applyDirection()
i18n.on('languageChanged', applyDirection)

export default i18n
