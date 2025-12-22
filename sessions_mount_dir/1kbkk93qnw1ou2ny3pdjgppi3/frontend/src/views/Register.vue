<template>
  <div class="register-view">
    <v-container class="fill-height" fluid>
      <v-row align="center" justify="center">
        <v-col cols="12" sm="10" md="8" lg="6">
          <v-card class="elevation-12">
            <v-toolbar color="primary" dark flat>
              <v-toolbar-title>{{ $t('register.title') }}</v-toolbar-title>
              <v-spacer></v-spacer>
              <v-btn icon @click="toggleLocale">
                <v-icon>{{ $i18n.locale === 'en' ? 'mdi-translate' : 'mdi-translate-close' }}</v-icon>
              </v-btn>
            </v-toolbar>

            <!-- 注册表单 -->
            <v-form ref="form" v-model="valid" @submit.prevent="handleRegister" v-if="!isSuccess">
              <v-card-text>
                <v-text-field
                  :label="$t('register.name')"
                  name="name"
                  prepend-icon="mdi-account"
                  type="text"
                  v-model="form.name"
                  :placeholder="$t('register.name_placeholder')"
                  :rules="nameRules"
                  required
                  :disabled="isLoading"
                />
                <v-text-field
                  :label="$t('register.phone')"
                  name="phone"
                  prepend-icon="mdi-phone"
                  type="text"
                  v-model="form.phone"
                  :placeholder="$t('register.phone_placeholder')"
                  :rules="phoneRules"
                  required
                  :disabled="isLoading"
                />
                <v-text-field
                  :label="$t('register.id_card')"
                  name="id_card"
                  prepend-icon="mdi-card-account-details"
                  type="text"
                  v-model="form.id_card"
                  :placeholder="$t('register.id_card_placeholder')"
                  :rules="idCardRules"
                  required
                  :disabled="isLoading"
                />
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn
                  color="primary"
                  type="submit"
                  :disabled="!valid || isLoading"
                  :loading="isLoading"
                >
                  {{ isLoading ? $t('register.registering') : $t('register.register_btn') }}
                </v-btn>
              </v-card-actions>
            </v-form>

            <!-- 注册成功提示 -->
            <v-card-text v-if="isSuccess" class="text-center">
              <v-icon color="success" size="64">mdi-check-circle</v-icon>
              <v-card-title class="justify-center success-title">{{ $t('register.success') }}</v-card-title>
              <v-card-subtitle>
                {{ $t('register.check_your_info', { memberId: registeredMemberInfo.id, name: registeredMemberInfo.name }) }}
              </v-card-subtitle>
            </v-card-text>
            <v-card-actions v-if="isSuccess">
              <v-spacer />
              <v-btn color="secondary" @click="handleRegisterAnother">{{ $t('register.back_to_home') }}</v-btn>
            </v-card-actions>

             <!-- 错误提示 -->
            <v-alert v-if="isError" type="error" dismissible @input="dismissError">
              {{ errorMessage }}
            </v-alert>

          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMemberStore } from '@/stores/member';

// Store 和 I18n
const memberStore = useMemberStore();
const { t, locale } = useI18n();

// Form data and validation
const form = ref({
  name: '',
  phone: '',
  id_card: ''
});
const valid = ref(false);
const formComponent = ref(null); // 用于引用和重置表单

// Computed getters from store
const isLoading = computed(() => memberStore.isLoading);
const isSuccess = computed(() => memberStore.isSuccess);
const isError = computed(() => memberStore.isError);
const registeredMemberInfo = computed(() => memberStore.registeredMemberInfo);
const errorMessage = computed(() => memberStore.errorMessage);

// Validation Rules
// 注意：这里的验证规则应与后端 Pydantic 模型保持一致
const nameRules = [
  v => !!v || t('register.validation_errors.name_required'),
  v => (v && v.length >= 2 && v.length <= 50) || t('register.validation_errors.name_length')
];

// 简单的中国手机号验证，后端可能使用更复杂的短信验证，此处只做格式校验
const phoneRules = [
  v => !!v || t('register.validation_errors.phone_required'),
  v => /^1[3-9]\d{9}$/.test(v) || t('register.validation_errors.phone_format')
];

// 18位身份证号正则验证，与后端 `validate_id_card` 逻辑对应
const idCardRules = [
  v => !!v || t('register.validation_errors.id_card_required'),
  v => /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/.test(v) || t('register.validation_errors.id_card_format')
];

// Methods
const handleRegister = async () => {
  if (!formComponent.value.validate()) {
    return;
  }
  await memberStore.register(form.value);
};

const handleRegisterAnother = () => {
  memberStore.resetState();
  form.value = { name: '', phone: '', id_card: '' };
  // 确保表单的验证状态也被重置，以便下一次注册
  formComponent.value?.resetValidation();
};

const dismissError = () => {
  // 用户关闭错误提示后，可以选择性地清除错误状态
  // 这里暂时不做处理，让用户在下一次提交时自然覆盖
};

const toggleLocale = () => {
  const newLocale = locale.value === 'en' ? 'zh' : 'en';
  locale.value = newLocale;
  localStorage.setItem('locale', newLocale);
};

</script>

<style scoped>
.register-view {
  background-color: #f5f5f5;
}
.success-title {
  word-break: break-word; /* 防止长ID或名称换行问题 */
}
</style>
