import { createI18n } from 'vue-i18n';
import en from '../lang/en.json';
import zh from '../lang/zh.json';

const messages = {
  en,
  zh
};

const i18n = createI18n({
  legacy: false,
  locale: 'en', // default locale
  fallbackLocale: 'en', // fallback locale
  messages,
  globalInjection: true,
  silentTranslationWarn: true
});

export default i18n;