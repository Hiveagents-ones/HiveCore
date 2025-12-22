<template>
  <v-menu offset-y>
    <template v-slot:activator="{ on, attrs }">
      <v-btn
        color="primary"
        dark
        v-bind="attrs"
        v-on="on"
        icon
      >
        <v-icon>mdi-translate</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
        v-for="(lang, i) in availableLocales"
        :key="i"
        @click="switchLanguage(lang.code)"
      >
        <v-list-item-title>{{ lang.name }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
import { useI18n } from 'vue-i18n';

export default {
  name: 'LanguageSwitcher',
  setup() {
    const { locale } = useI18n();
    
    const availableLocales = [
      { code: 'en', name: 'English' },
      { code: 'zh', name: '中文' }
    ];
    
    const switchLanguage = (newLocale) => {
      locale.value = newLocale;
      localStorage.setItem('userLocale', newLocale);
    };
    
    return {
      availableLocales,
      switchLanguage
    };
  }
};
</script>

<style scoped>
/* 可以根据需要添加样式 */
</style>