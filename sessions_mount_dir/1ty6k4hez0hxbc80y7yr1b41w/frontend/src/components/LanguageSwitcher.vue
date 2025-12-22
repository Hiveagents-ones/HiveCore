<template>
  <div class="language-switcher">
    <select v-model="currentLocale" @change="changeLanguage" class="language-select">
      <option v-for="locale in availableLocales" :key="locale" :value="locale">
        {{ getLanguageName(locale) }}
      </option>
    </select>
  </div>
</template>

<script>
import { useI18n } from 'vue-i18n';

export default {
  name: 'LanguageSwitcher',
  setup() {
    const { locale, availableLocales, t } = useI18n();

    const changeLanguage = (event) => {
      locale.value = event.target.value;
      localStorage.setItem('userLocale', event.target.value);
    };

    const getLanguageName = (code) => {
      const languages = {
        en: 'English',
        zh: '中文',
        ja: '日本語',
        ko: '한국어',
        fr: 'Français',
        de: 'Deutsch',
        es: 'Español'
      };
      return languages[code] || code;
    };

    return {
      currentLocale: locale,
      availableLocales,
      changeLanguage,
      getLanguageName
    };
  },
  created() {
    const savedLocale = localStorage.getItem('userLocale');
    if (savedLocale && this.availableLocales.includes(savedLocale)) {
      this.currentLocale = savedLocale;
    }
  }
};
</script>

<style scoped>
.language-switcher {
  margin-left: auto;
  padding: 0 20px;
  display: flex;
  align-items: center;
}

.language-select {
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background-color: white;
  font-size: 14px;
  cursor: pointer;
  min-width: 120px;
  transition: all 0.3s ease;
}

.language-select:focus {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  outline: none;
  border-color: #409eff;
}
</style>