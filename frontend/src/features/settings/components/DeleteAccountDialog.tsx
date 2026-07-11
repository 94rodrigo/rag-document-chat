import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Trash2, TriangleAlert, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { usersApi, clearTokens } from '@/shared/lib/api-client'
import { useAuthStore } from '@/shared/stores/auth-store'

const CONFIRM_WORD = 'DELETE'

interface DeleteAccountDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DeleteAccountDialog({ open, onOpenChange }: DeleteAccountDialogProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const [confirmText, setConfirmText] = useState('')

  const deleteAccount = useMutation({
    mutationFn: () => usersApi.deleteAccount(),
    onSuccess: () => {
      clearTokens()
      clearAuth()
      qc.clear()
      toast.success(t('settings.toasts.accountDeleted'))
      navigate('/login')
    },
    onError: () => toast.error(t('settings.toasts.accountDeleteFailed')),
  })

  const isConfirmed = confirmText.trim().toUpperCase() === CONFIRM_WORD

  const handleOpenChange = (v: boolean) => {
    if (!deleteAccount.isPending) {
      if (!v) setConfirmText('')
      onOpenChange(v)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="h-9 w-9 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center justify-center shrink-0">
              <TriangleAlert className="size-4 text-destructive" />
            </div>
            <DialogTitle>{t('settings.deleteAccountDialog.title')}</DialogTitle>
          </div>

          <DialogDescription className="mt-2">
            {t('settings.deleteAccountDialog.body')}{' '}
            <span className="text-text-primary font-medium">{t('settings.deleteAccountDialog.bodyEmphasis')}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label htmlFor="delete-account-confirm">
            {t('settings.deleteAccountDialog.confirmLabel', { word: CONFIRM_WORD })}
          </Label>
          <Input
            id="delete-account-confirm"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={CONFIRM_WORD}
            autoComplete="off"
            disabled={deleteAccount.isPending}
          />
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleOpenChange(false)}
            disabled={deleteAccount.isPending}
          >
            {t('common.cancel')}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => deleteAccount.mutate()}
            disabled={!isConfirmed || deleteAccount.isPending}
            className="gap-1.5"
          >
            {deleteAccount.isPending ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                {t('common.deleting')}
              </>
            ) : (
              <>
                <Trash2 className="size-3.5" />
                {t('settings.danger.delete')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
