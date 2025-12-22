<template>
  <div class="member-form-container">
    <h2>会员注册</h2>
    <form @submit.prevent="handleSubmit" class="member-form">
      <div class="form-group">
        <label for="name">姓名 *</label>
        <input
          type="text"
          id="name"
          v-model="form.name"
          :class="{ 'error': errors.name }"
          @blur="validateField('name')"
        />
        <span class="error-message" v-if="errors.name">{{ errors.name }}</span>
      </div>

      <div class="form-group">
        <label for="phone">手机号 *</label>
        <input
          type="tel"
          id="phone"
          v-model="form.phone"
          :class="{ 'error': errors.phone }"
          @blur="validateField('phone')"
        />
        <span class="error-message" v-if="errors.phone">{{ errors.phone }}</span>
      </div>

      <div class="form-group">
        <label for="idCard">身份证号 *</label>
        <input
          type="text"
          id="idCard"
          v-model="form.idCard"
          :class="{ 'error': errors.idCard }"
          @blur="validateField('idCard')"
        />
        <span class="error-message" v-if="errors.idCard">{{ errors.idCard }}</span>
      </div>

      <div class="form-group">
        <label for="email">邮箱</label>
        <input
          type="email"
          id="email"
          v-model="form.email"
          :class="{ 'error': errors.email }"
          @blur="validateField('email')"
        />
        <span class="error-message" v-if="errors.email">{{ errors.email }}</span>
      </div>

      <div class="form-group">
        <label for="birthDate">出生日期</label>
        <input
          type="date"
          id="birthDate"
          v-model="form.birthDate"
          :class="{ 'error': errors.birthDate }"
          @blur="validateField('birthDate')"
        />
        <span class="error-message" v-if="errors.birthDate">{{ errors.birthDate }}</span>
      </div>

      <div class="form-group checkbox-group">
        <input
          type="checkbox"
          id="agreePrivacy"
          v-model="form.agreePrivacy"
          :class="{ 'error': errors.agreePrivacy }"
          @change="validateField('agreePrivacy')"
        />
        <label for="agreePrivacy">我已阅读并同意 <a href="#" @click.prevent="showPrivacyPolicy">隐私政策</a> *</label>
        <span class="error-message" v-if="errors.agreePrivacy">{{ errors.agreePrivacy }}</span>
      </div>

      <div class="form-actions">
        <button type="submit" :disabled="isSubmitting" class="submit-btn">
          {{ isSubmitting ? '提交中...' : '注册' }}
        </button>
        <button type="button" @click="resetForm" class="reset-btn">重置</button>
      </div>
    </form>

    <div v-if="successMessage" class="success-message">
      {{ successMessage }}
    </div>

    <div v-if="showPrivacyModal" class="privacy-modal" @click.self="closePrivacyModal">
      <div class="modal-content">
        <h3>隐私政策</h3>
        <div class="policy-content">
          <p>感谢您选择成为我们的会员。我们非常重视您的隐私保护，本隐私政策说明了我们如何收集、使用、存储和保护您的个人信息。</p>
          <h4>1. 信息收集</h4>
          <p>我们收集您的姓名、手机号、身份证号、邮箱和出生日期等信息，用于会员身份识别和联系。</p>
          <h4>2. 信息使用</h4>
          <p>您的个人信息仅用于会员服务、身份验证和紧急情况联系，不会用于其他目的。</p>
          <h4>3. 信息保护</h4>
          <p>我们采用行业标准的安全措施保护您的个人信息，防止未经授权的访问、使用或泄露。</p>
          <h4>4. 信息共享</h4>
          <p>除非获得您的明确同意或法律要求，我们不会与第三方共享您的个人信息。</p>
          <h4>5. 联系我们</h4>
          <p>如果您对本隐私政策有任何疑问，请通过客服电话或邮箱联系我们。</p>
        </div>
        <button @click="closePrivacyModal" class="close-btn">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'

const router = useRouter()
const memberStore = useMemberStore()

const isSubmitting = ref(false)
const successMessage = ref('')
const showPrivacyModal = ref(false)

const form = reactive({
  name: '',
  phone: '',
  idCard: '',
  email: '',
  birthDate: '',
  agreePrivacy: false
})

const errors = reactive({
  name: '',
  phone: '',
  idCard: '',
  email: '',
  birthDate: '',
  agreePrivacy: ''
})

const validateField = (field) => {
  switch (field) {
    case 'name':
      if (!form.name.trim()) {
        errors.name = '请输入姓名'
      } else if (form.name.length < 2 || form.name.length > 20) {
        errors.name = '姓名长度应在2-20个字符之间'
      } else {
        errors.name = ''
      }
      break
    case 'phone':
      const phoneRegex = /^1[3-9]\d{9}$/
      if (!form.phone.trim()) {
        errors.phone = '请输入手机号'
      } else if (!phoneRegex.test(form.phone)) {
        errors.phone = '请输入有效的手机号'
      } else {
        errors.phone = ''
      }
      break
    case 'idCard':
      const idCardRegex = /(^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}$)/
      if (!form.idCard.trim()) {
        errors.idCard = '请输入身份证号'
      } else if (!idCardRegex.test(form.idCard)) {
        errors.idCard = '请输入有效的身份证号'
      } else {
        errors.idCard = ''
      }
      break
    case 'email':
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
      if (form.email && !emailRegex.test(form.email)) {
        errors.email = '请输入有效的邮箱地址'
      } else {
        errors.email = ''
      }
      break
    case 'birthDate':
      if (form.birthDate) {
        const birthDate = new Date(form.birthDate)
        const today = new Date()
        const age = today.getFullYear() - birthDate.getFullYear()
        if (age < 16 || age > 100) {
          errors.birthDate = '年龄应在16-100岁之间'
        } else {
          errors.birthDate = ''
        }
      } else {
        errors.birthDate = ''
      }
      break
    case 'agreePrivacy':
      if (!form.agreePrivacy) {
        errors.agreePrivacy = '请同意隐私政策'
      } else {
        errors.agreePrivacy = ''
      }
      break
  }
}

const validateForm = () => {
  validateField('name')
  validateField('phone')
  validateField('idCard')
  validateField('email')
  validateField('birthDate')
  validateField('agreePrivacy')
  
  return !Object.values(errors).some(error => error)
}

const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }
  
  isSubmitting.value = true
  successMessage.value = ''
  
  try {
    const memberData = {
      name: form.name,
      phone: form.phone,
      id_card: form.idCard,
      email: form.email || null,
      birth_date: form.birthDate || null
    }
    
    await memberStore.registerMember(memberData)
    successMessage.value = '注册成功！您的会员ID已生成。'
    
    setTimeout(() => {
      router.push('/members')
    }, 2000)
  } catch (error) {
    console.error('注册失败:', error)
    if (error.response && error.response.data && error.response.data.detail) {
      alert(`注册失败: ${error.response.data.detail}`)
    } else {
      alert('注册失败，请稍后重试')
    }
  } finally {
    isSubmitting.value = false
  }
}

const resetForm = () => {
  form.name = ''
  form.phone = ''
  form.idCard = ''
  form.email = ''
  form.birthDate = ''
  form.agreePrivacy = false
  
  Object.keys(errors).forEach(key => {
    errors[key] = ''
  })
  
  successMessage.value = ''
}

const showPrivacyPolicy = () => {
  showPrivacyModal.value = true
}

const closePrivacyModal = () => {
  showPrivacyModal.value = false
}
</script>

<style scoped>
.member-form-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

.member-form {
  background: #f9f9f9;
  padding: 25px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #555;
}

input[type="text"],
input[type="tel"],
input[type="email"],
input[type="date"] {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.3s;
}

input[type="text"]:focus,
input[type="tel"]:focus,
input[type="email"]:focus,
input[type="date"]:focus {
  border-color: #4CAF50;
  outline: none;
}

input.error {
  border-color: #f44336;
}

.error-message {
  color: #f44336;
  font-size: 14px;
  margin-top: 5px;
  display: block;
}

.checkbox-group {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20px;
}

.checkbox-group input[type="checkbox"] {
  margin-right: 10px;
  margin-top: 5px;
}

.checkbox-group label {
  margin-bottom: 0;
  font-weight: normal;
}

.checkbox-group a {
  color: #2196F3;
  text-decoration: none;
}

.checkbox-group a:hover {
  text-decoration: underline;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 30px;
}

.submit-btn,
.reset-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn {
  background-color: #4CAF50;
  color: white;
  flex: 2;
  margin-right: 10px;
}

.submit-btn:hover:not(:disabled) {
  background-color: #45a049;
}

.submit-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.reset-btn {
  background-color: #f44336;
  color: white;
  flex: 1;
}

.reset-btn:hover {
  background-color: #d32f2f;
}

.success-message {
  margin-top: 20px;
  padding: 15px;
  background-color: #dff0d8;
  color: #3c763d;
  border-radius: 4px;
  text-align: center;
}

.privacy-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  width: 90%;
}

.modal-content h3 {
  margin-top: 0;
  color: #333;
}

.policy-content {
  margin: 20px 0;
  line-height: 1.6;
}

.policy-content h4 {
  margin-top: 15px;
  margin-bottom: 10px;
  color: #555;
}

.close-btn {
  background-color: #2196F3;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  display: block;
  margin: 0 auto;
}

.close-btn:hover {
  background-color: #0b7dda;
}
</style>