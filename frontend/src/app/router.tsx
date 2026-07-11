import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '@/shared/components/layout/AppLayout'
import { AuthLayout } from '@/shared/components/layout/AuthLayout'
import { SimpleLayout } from '@/shared/components/layout/SimpleLayout'
import { ErrorPage } from '@/shared/components/layout/ErrorPage'
import { NotFoundPage } from '@/shared/components/layout/NotFoundPage'
import { LandingPage } from '@/features/landing/pages/LandingPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { RegisterPage } from '@/features/auth/pages/RegisterPage'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { DocumentsPage } from '@/features/documents/pages/DocumentsPage'
import { DocumentViewerPage } from '@/features/documents/pages/DocumentViewerPage'
import { SettingsPage } from '@/features/settings/pages/SettingsPage'
import { BillingPage } from '@/features/billing/pages/BillingPage'
import { PrivacyPage } from '@/features/legal/pages/PrivacyPage'
import { TermsPage } from '@/features/legal/pages/TermsPage'
import { ContactPage } from '@/features/legal/pages/ContactPage'

export const router = createBrowserRouter([
  // Public landing
  { path: '/', element: <LandingPage />, errorElement: <ErrorPage /> },

  // Public content pages
  {
    element: <SimpleLayout />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/privacy', element: <PrivacyPage /> },
      { path: '/terms', element: <TermsPage /> },
      { path: '/contact', element: <ContactPage /> },
    ],
  },

  // Auth routes
  {
    element: <AuthLayout />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
    ],
  },

  // Protected app routes
  {
    element: <AppLayout />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/dashboard', element: <DashboardPage /> },
      { path: '/documents', element: <DocumentsPage /> },
      { path: '/documents/:id', element: <DocumentViewerPage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '/billing', element: <BillingPage /> },
    ],
  },

  // Catch-all
  { path: '*', element: <NotFoundPage /> },
])
