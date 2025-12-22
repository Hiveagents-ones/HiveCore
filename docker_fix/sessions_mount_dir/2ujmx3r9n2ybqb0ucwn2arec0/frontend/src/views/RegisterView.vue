<template>
  <div class="register-view">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>{{ $t('register.title') }}</h2>
        </div>
      </template>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="rules"
        label-width="120px"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item :label="$t('register.name')" prop="name">
          <el-input
            v-model="registerForm.name"
            :placeholder="$t('register.namePlaceholder')"
            clearable
          />
        </el-form-item>

        <el-form-item :label="$t('register.phone')" prop="phone">
          <el-input
            v-model="registerForm.phone"
            :placeholder="$t('register.phonePlaceholder')"
            clearable
          />
        </el-form-item>

        <el-form-item :label="$t('register.idCard')" prop="idCard">
          <el-input
            v-model="registerForm.idCard"
            :placeholder="$t('register.idCardPlaceholder')"
            clearable
          />
        </el-form-item>

        <el-form-item :label="$t('register.membershipPlan')" prop="plan">
          <el-select
            v-model="registerForm.plan"
            :placeholder="$t('register.planRequired')"
            style="width: 100%"
          >
            <el-option
              :label="$t('register.basicPlan')"
              value="basic"
            />
            <el-option
              :label="$t('register.premiumPlan')"
              value="premium"
            />
            <el-option
              :label="$t('register.vipPlan')"
              value="vip"
            />
          </el-select>
        </el-form-item>

        <el-form-item prop="agreedToPolicy">
          <el-checkbox v-model="registerForm.agreedToPolicy">
            {{ $t('register.agreeToTerms') }}
            <el-link
              type="primary"
              @click="showPrivacyPolicy"
            >
              {{ $t('register.privacyPolicy') }}
            </el-link>
          </el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            style="width: 100%"
          >
            {{ $t('common.submit') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Privacy Policy Dialog -->
    <PrivacyPolicyDialog
      v-model:visible="privacyDialogVisible"
      @confirm="handlePolicyAgreed"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import PrivacyPolicyDialog from '@/components/PrivacyPolicyDialog.vue'
import { registerMember } from '@/api/member'

const { t } = useI18n()

const registerFormRef = ref(null)
const loading = ref(false)
const privacyDialogVisible = ref(false)

const registerForm = reactive({
  name: '',
  phone: '',
  idCard: '',
  plan: '',
  agreedToPolicy: false
})

const validatePhone = (rule, value, callback) => {
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!value) {
    callback(new Error(t('register.phoneRequired')))
  } else if (!phoneRegex.test(value)) {
    callback(new Error(t('register.phoneInvalid')))
  } else {
    callback()
  }
}

const validateIdCard = (rule, value, callback) => {
  const idCardRegex = /(^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}$)/
  if (!value) {
    callback(new Error(t('register.idCardRequired')))
  } else if (!idCardRegex.test(value)) {
    callback(new Error(t('register.idCardInvalid')))
  } else {
    callback()
  }
}

const rules = reactive({
  name: [
    { required: true, message: t('register.nameRequired'), trigger: 'blur' }
  ],
  phone: [
    { validator: validatePhone, trigger: 'blur' }
  ],
  idCard: [
    { validator: validateIdCard, trigger: 'blur' }
  ],
  plan: [
    { required: true, message: t('register.planRequired'), trigger: 'change' }
  ],
  agreedToPolicy: [
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error(t('register.agreeToTerms') + ' ' + t('register.privacyPolicy')))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
})

const showPrivacyPolicy = () => {
  privacyDialogVisible.value = true
}

const handlePolicyAgreed = () => {
  registerForm.agreedToPolicy = true
}

const handleSubmit = async () => {
  if (!registerFormRef.value) return

  try {
    await registerFormRef.value.validate()
    loading.value = true

    const response = await registerMember(registerForm)
    
    if (response.success) {
      ElMessage.success(t('register.registerSuccess', { id: response.data.memberId }))
      // Reset form
      registerFormRef.value.resetFields()
    } else {
      ElMessage.error(t('register.registerFailed'))
    }
  } catch (error) {
    console.error('Registration error:', error)
    ElMessage.error(t('register.registerFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 500px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #303133;
  font-weight: 600;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input__wrapper) {
  border-radius: 6px;
}

:deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-checkbox__label) {
  font-size: 14px;
  color: #606266;
}
</style>