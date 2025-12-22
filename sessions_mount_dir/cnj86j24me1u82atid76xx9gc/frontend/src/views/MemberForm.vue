<template>
  <div class="member-form">
    <h2>{{ $t('member.title') }}</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="name">{{ $t('member.name') }}</label>
        <input
          id="name"
          v-model="form.name"
          type="text"
          :class="{ 'is-invalid': errors.name }"
          @blur="validateField('name')"
        />
        <span v-if="errors.name" class="error-message">{{ errors.name }}</span>
      </div>

      <div class="form-group">
        <label for="phone">{{ $t('member.phone') }}</label>
        <input
          id="phone"
          v-model="form.phone"
          type="tel"
          :class="{ 'is-invalid': errors.phone }"
          @blur="validateField('phone')"
        />
        <span v-if="errors.phone" class="error-message">{{ errors.phone }}</span>
      </div>

      <div class="form-group">
        <label for="email">{{ $t('member.email') }}</label>
        <input
          id="email"
          v-model="form.email"
          type="email"
          :class="{ 'is-invalid': errors.email }"
          @blur="validateField('email')"
        />
        <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
      </div>

      <div class="form-group">
        <label for="level">{{ $t('member.level') }}</label>
        <select
          id="level"
          v-model="form.level"
          :class="{ 'is-invalid': errors.level }"
          @blur="validateField('level')"
        >
          <option value="">{{ $t('member.selectLevel') }}</option>
          <option value="bronze">{{ $t('member.levels.bronze') }}</option>
          <option value="silver">{{ $t('member.levels.silver') }}</option>
          <option value="gold">{{ $t('member.levels.gold') }}</option>
          <option value="platinum">{{ $t('member.levels.platinum') }}</option>
        </select>
        <span v-if="errors.level" class="error-message">{{ errors.level }}</span>
      </div>

      <div class="form-group">
        <label for="membership">{{ $t('member.membership') }}</label>
        <input
          id="membership"
          v-model="form.membership"
          type="number"
          min="0"
          :class="{ 'is-invalid': errors.membership }"
          @blur="validateField('membership')"
        />
        <span v-if="errors.membership" class="error-message">{{ errors.membership }}</span>
      </div>

      <div class="form-actions">
        <button type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? $t('common.submitting') : $t('common.submit') }}
        </button>
        <button type="button" @click="handleReset">
          {{ $t('common.reset') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const router = useRouter()

const form = reactive({
  name: '',
  phone: '',
  email: '',
  level: '',
  membership: ''
})

const errors = reactive({})
const isSubmitting = ref(false)

const validateField = (field) => {
  errors[field] = ''

  switch (field) {
    case 'name':
      if (!form.name.trim()) {
        errors.name = t('validation.required', { field: t('member.name') })
      } else if (form.name.length < 2) {
        errors.name = t('validation.minLength', { field: t('member.name'), min: 2 })
      }
      break
    case 'phone':
      if (!form.phone.trim()) {
        errors.phone = t('validation.required', { field: t('member.phone') })
      } else if (!/^1[3-9]\d{9}$/.test(form.phone)) {
        errors.phone = t('validation.phone')
      }
      break
    case 'email':
      if (!form.email.trim()) {
        errors.email = t('validation.required', { field: t('member.email') })
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
        errors.email = t('validation.email')
      }
      break
    case 'level':
      if (!form.level) {
        errors.level = t('validation.required', { field: t('member.level') })
      }
      break
    case 'membership':
      if (!form.membership) {
        errors.membership = t('validation.required', { field: t('member.membership') })
      } else if (isNaN(form.membership) || form.membership < 0) {
        errors.membership = t('validation.positiveNumber')
      }
      break
  }
}

const validateForm = () => {
  Object.keys(form).forEach(field => validateField(field))
  return !Object.values(errors).some(error => error)
}

const handleSubmit = async () => {
  if (!validateForm()) return

  isSubmitting.value = true
  try {
    // TODO: API call to save member
    await new Promise(resolve => setTimeout(resolve, 1000))
    alert(t('member.saveSuccess'))
    router.push('/members')
  } catch (error) {
    console.error('Error saving member:', error)
    alert(t('member.saveError'))
  } finally {
    isSubmitting.value = false
  }
}

const handleReset = () => {
  Object.keys(form).forEach(key => {
    form[key] = ''
  })
  Object.keys(errors).forEach(key => {
    errors[key] = ''
  })
}
</script>

<style scoped>
.member-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

input,
select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

input.is-invalid,
select.is-invalid {
  border-color: #dc3545;
}

.error-message {
  display: block;
  margin-top: 5px;
  color: #dc3545;
  font-size: 12px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 30px;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

button[type="submit"] {
  background-color: #007bff;
  color: white;
}

button[type="submit"]:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button[type="button"] {
  background-color: #6c757d;
  color: white;
}

button:hover:not(:disabled) {
  opacity: 0.9;
}
</style>
