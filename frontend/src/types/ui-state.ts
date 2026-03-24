export type UIStateType = 'loading' | 'empty' | 'error' | 'offline' | 'retry'

export interface UIStateProps {
  type: UIStateType
  title: string
  description?: string
  actionText?: string
  onAction?: () => void
}
