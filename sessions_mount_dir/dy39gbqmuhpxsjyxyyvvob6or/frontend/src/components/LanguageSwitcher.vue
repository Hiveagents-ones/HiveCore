<template>
  <div class="language-switcher">
    <select v-model="currentLocale" @change="changeLanguage" class="language-select">
      <option v-for="locale in availableLocales" :key="locale" :value="locale">
        {{ getLanguageName(locale) }}
,
      getFinancialTerm
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
    const financialTerms = {
      'en': {
        'payment': 'Payment',
        'amount': 'Amount',
        'date': 'Date',
        'method': 'Method'
      },
      'zh': {
        'payment': '支付',
        'amount': '金额',
        'date': '日期',
        'method': '方式'
      },
      'ja': {
        'payment': '支払い',
        'amount': '金額',
        'date': '日付',
        'method': '方法'
      },
      'ko': {
        'payment': '지불',
        'amount': '금액',
        'date': '날짜',
        'method': '방법'
      }
    };

    const changeLanguage = (event) => {
      locale.value = event.target.value;
      localStorage.setItem('userLocale', event.target.value);
    };

    const getLanguageName = (code) => {
      const languages = {
        'en': 'English',
        'zh': '中文',
        'ja': '日本語',
        'ko': '한국어'
      };
      return languages[code] || code;

    const getFinancialTerm = (term) => {
      return financialTerms[locale.value]?.[term] || term;
    };
    };
    };

    return {
      currentLocale: locale,
      availableLocales,
      changeLanguage,
      getLanguageName
    };
  }
};
</script>

<style scoped>
.language-switcher {
  margin-left: auto;
  padding: 0 20px;
}

.language-select {
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background-color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.language-select:focus {
  outline: none;
  border-color: #409eff;
}
</style>