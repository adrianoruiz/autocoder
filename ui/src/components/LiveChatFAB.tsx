import { MessageSquare, X } from 'lucide-react'

interface LiveChatFABProps {
  onClick: () => void
  isOpen: boolean
}

export function LiveChatFAB({ onClick, isOpen }: LiveChatFABProps) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-24 right-6 z-40 neo-btn bg-[var(--color-neo-accent)] text-white border-4 border-[var(--color-neo-border)] shadow-[8px_8px_0px_rgba(0,0,0,1)] hover:shadow-[4px_4px_0px_rgba(0,0,0,1)] hover:translate-x-[4px] hover:translate-y-[4px] transition-all p-4 group"
      title={isOpen ? 'Close Live Chat (Press C)' : 'Open Live Chat (Press C)'}
    >
      {isOpen ? (
        <X size={24} className="group-hover:rotate-90 transition-transform" />
      ) : (
        <MessageSquare size={24} className="group-hover:scale-110 transition-transform" />
      )}
    </button>
  )
}
