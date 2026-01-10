import { useTranslation } from 'react-i18next'
import { Globe } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'

const languages = [
  { code: 'en', label: 'English', flag: '🇺🇸' },
  { code: 'pt-BR', label: 'Português (BR)', flag: '🇧🇷' },
]

export function LanguageSelector() {
  const { i18n, t } = useTranslation()

  const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0]

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode)
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          className="neo-btn neo-btn-secondary text-sm flex items-center gap-2"
          title={t('language.select')}
        >
          <Globe size={16} />
          <span className="hidden sm:inline">{currentLanguage.flag}</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="neo-card p-1 min-w-[160px] z-50"
          sideOffset={5}
          align="end"
        >
          {languages.map((lang) => (
            <DropdownMenu.Item
              key={lang.code}
              className={`flex items-center gap-2 px-3 py-2 cursor-pointer outline-none hover:bg-[var(--color-neo-bg)] ${
                i18n.language === lang.code ? 'bg-[var(--color-neo-bg)] font-bold' : ''
              }`}
              onClick={() => handleLanguageChange(lang.code)}
            >
              <span>{lang.flag}</span>
              <span>{lang.label}</span>
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
