<template>
  <div class="register-view">
    <div class="container">
      <h1>{{ $t('register.title') }}</h1>
      <form @submit.prevent="handleSubmit" class="register-form">
        <!-- 姓名 -->
        <div class="form-group">
          <label for="name">{{ $t('register.form.name.label') }}</label>
          <input
            type="text"
            id="name"
            v-model="formData.name"
            :placeholder="$t('register.form.name.placeholder')"
            @blur="validateField('name')"
            :class="{ 'is-invalid': errors.name }"
          />
          <div v-if="errors.name" class="error-message">{{ errors.name }}</div>
        </div>

        <!-- 手机号 -->
        <div class="form-group">
          <label for="phone">{{ $t('register.form.phone.label') }}</label>
          <input
            type="tel"
            id="phone"
            v-model="formData.phone"
            :placeholder="$t('register.form.phone.placeholder')"
            @blur="validateField('phone')"
            :class="{ 'is-invalid': errors.phone }"
          />
          <div v-if="errors.phone" class="error-message">{{ errors.phone }}</div>
        </div>

        <!-- 身份证号 -->
        <div class="form-group">
          <label for="idCard">{{ $t('register.form.idCard.label') }}</label>
          <input
            type="text"
            id="idCard"
            v-model="formData.idCard"
            :placeholder="$t('register.form.idCard.placeholder')"
            @blur="validateField('idCard')"
            :class="{ 'is-invalid': errors.idCard }"
          />
          <div v-if="errors.idCard" class="error-message">{{ errors.idCard }}</div>
        </div>

        <!-- 会员卡类型 -->
        <div class="form-group">
          <label for="membershipType">{{ $t('register.form.membershipType.label') }}</label>
          <select
            id="membershipType"
            v-model="formData.membershipType"
            @blur="validateField('membershipType')"
            :class="{ 'is-invalid': errors.membershipType }"
          >
            <option value="">{{ $t('register.form.membershipType.placeholder') }}</option>
            <option
              v-for="type in membershipTypes"
              :key="type.id"
              :value="type.id"
            >
              {{ $t(`register.form.membershipType.options.${type.type}`) }}
            </option>
          </select>
          <div v-if="errors.membershipType" class="error-message">
            {{ errors.membershipType }}
          </div>
        </div>

        <!-- 隐私政策 -->
        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input
              type="checkbox"
              v-model="formData.privacyAccepted"
              @change="validateField('privacyAccepted')"
              :class="{ 'is-invalid': errors.privacyAccepted }"
            />
            <span>
              {{ $t('register.form.agreement.label') }}
              <a
                href="#"
                @click.prevent="showPrivacyPolicy"
                class="privacy-link"
              >
                {{ $t('register.form.agreement.privacyPolicy') }}
              </a>
            </span>
          </label>
          <div v-if="errors.privacyAccepted" class="error-message">
            {{ errors.privacyAccepted }}
          </div>
        </div>

        <!-- 提交按钮 -->
        <button
          type="submit"
          class="submit-btn"
          :disabled="loading || !isFormValid"
        >
          <span v-if="loading">{{ $t('common.loading') }}</span>
          <span v-else>{{ $t('register.submit') }}</span>
        </button>

        <!-- 错误信息 -->
        <div v-if="submitError" class="alert alert-error">
          {{ submitError }}
        </div>
      </form>

      <!-- 成功消息 -->
      <div v-if="registrationResult" class="alert alert-success">
        <h3>{{ $t('register.success.title') }}</h3>
        <p>
          {{ $t('register.success.message', { memberId: registrationResult.memberId }) }}
        </p>
      </div>
    </div>

    <!-- 隐私政策弹窗 -->
    <div v-if="showPrivacyModal" class="modal-overlay" @click="closePrivacyPolicy">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ $t('register.privacyPolicy.title') }}</h2>
          <button class="close-btn" @click="closePrivacyPolicy">&times;</button>
        </div>
        <div class="modal-body">
          <pre>{{ $t('register.privacyPolicy.content') }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="closePrivacyPolicy">
            {{ $t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRegisterStore } from '../stores/register';

const { t } = useI18n();
const registerStore = useRegisterStore();

// 表单数据
const formData = computed(() => registerStore.formData);
const membershipTypes = computed(() => registerStore.membershipTypes);
const loading = computed(() => registerStore.loading);
const registrationResult = computed(() => registerStore.registrationResult);
const submitError = computed(() => registerStore.error);

// 本地验证错误
const errors = ref({
  name: '',
  phone: '',
  idCard: '',
  membershipType: '',
  privacyAccepted: ''
});

// 隐私政策弹窗
const showPrivacyModal = ref(false);

// 表单验证状态
const isFormValid = computed(() => {
  return (
    formData.value.name.trim() !== '' &&
    formData.value.phone.trim() !== '' &&
    formData.value.idCard.trim() !== '' &&
    formData.value.membershipType !== '' &&
    formData.value.privacyAccepted &&
    !Object.values(errors.value).some(error => error !== '')
  );
});

// 验证单个字段
const validateField = (field) => {
  switch (field) {
    case 'name':
      if (!formData.value.name.trim()) {
        errors.value.name = t('register.form.name.error.required');
      } else if (!/^[一-龥a-zA-Z\s]{2,20}$/.test(formData.value.name)) {
        errors.value.name = t('register.form.name.error.invalid');
      } else {
        errors.value.name = '';
      }
      break;

    case 'phone':
      if (!formData.value.phone.trim()) {
        errors.value.phone = t('register.form.phone.error.required');
      } else if (!/^1[3-9]\d{9}$/.test(formData.value.phone)) {
        errors.value.phone = t('register.form.phone.error.invalid');
      } else {
        errors.value.phone = '';
      }
      break;

    case 'idCard':
      if (!formData.value.idCard.trim()) {
        errors.value.idCard = t('register.form.idCard.error.required');
      } else if (!/^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/.test(formData.value.idCard)) {
        errors.value.idCard = t('register.form.idCard.error.invalid');
      } else {
        errors.value.idCard = '';
      }
      break;

    case 'membershipType':
      if (!formData.value.membershipType) {
        errors.value.membershipType = t('register.form.membershipType.error.required');
      } else {
        errors.value.membershipType = '';
      }
      break;

    case 'privacyAccepted':
      if (!formData.value.privacyAccepted) {
        errors.value.privacyAccepted = t('register.form.agreement.error.required');
      } else {
        errors.value.privacyAccepted = '';
      }
      break;
  }
};

// 验证整个表单
const validateForm = () => {
  validateField('name');
  validateField('phone');
  validateField('idCard');
  validateField('membershipType');
  validateField('privacyAccepted');
  
  return !Object.values(errors.value).some(error => error !== '');
};

// 显示隐私政策
const showPrivacyPolicy = () => {
  showPrivacyModal.value = true;
};

// 关闭隐私政策
const closePrivacyPolicy = () => {
  showPrivacyModal.value = false;
};

// 提交表单
const handleSubmit = async () => {
  if (!validateForm()) {
    return;
  }

  try {
    await registerStore.submitRegistration();
  } catch (error) {
    console.error('Registration failed:', error);
  }
};

// 组件挂载时获取会员卡类型
onMounted(() => {
  registerStore.fetchMembershipTypes();
});
</script>

<style scoped>
.register-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.container {
  background: white;
  padding: 40px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 500px;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 28px;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

input,
select {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
  transition: border-color 0.3s;
}

input:focus,
select:focus {
  outline: none;
  border-color: #667eea;
}

input.is-invalid,
select.is-invalid {
  border-color: #e74c3c;
}

.error-message {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 5px;
}

.checkbox-group {
  flex-direction: row;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  margin-bottom: 0;
}

.checkbox-label input[type="checkbox"] {
  margin-right: 8px;
  width: auto;
}

.privacy-link {
  color: #667eea;
  text-decoration: none;
  margin-left: 5px;
}

.privacy-link:hover {
  text-decoration: underline;
}

.submit-btn {
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.3s;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.alert {
  padding: 15px;
  border-radius: 5px;
  margin-top: 20px;
}

.alert-error {
  background: #fee;
  color: #e74c3c;
  border: 1px solid #fcc;
}

.alert-success {
  background: #efe;
  color: #27ae60;
  border: 1px solid #cfc;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 10px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-body pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  line-height: 1.6;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5a67d8;
}

@media (max-width: 600px) {
  .container {
    padding: 20px;
  }
  
  h1 {
    font-size: 24px;
  }
}
</style>