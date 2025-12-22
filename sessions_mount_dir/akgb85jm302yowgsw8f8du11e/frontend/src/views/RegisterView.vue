<template>
  <div class="register-view">
    <div class="container">
      <h1>{{ $t('register.title') }}</h1>
      
      <form @submit.prevent="handleSubmit" class="register-form">
        <!-- Basic Information -->
        <div class="form-section">
          <h2>{{ $t('register.form.basicInfo.title') }}</h2>
          
          <div class="form-group">
            <label for="name">{{ $t('register.form.basicInfo.name.label') }} *</label>
            <input
              id="name"
              v-model="form.name"
              type="text"
              :placeholder="$t('register.form.basicInfo.name.placeholder')"
              required
            />
            <span v-if="errors.name" class="error">{{ errors.name }}</span>
          </div>
          
          <div class="form-group">
            <label for="gender">{{ $t('register.form.basicInfo.gender.label') }} *</label>
            <select id="gender" v-model="form.gender" required>
              <option value="">{{ $t('register.form.basicInfo.gender.placeholder') }}</option>
              <option value="male">{{ $t('register.form.basicInfo.gender.male') }}</option>
              <option value="female">{{ $t('register.form.basicInfo.gender.female') }}</option>
            </select>
            <span v-if="errors.gender" class="error">{{ errors.gender }}</span>
          </div>
          
          <div class="form-group">
            <label for="phone">{{ $t('register.form.basicInfo.phone.label') }} *</label>
            <input
              id="phone"
              v-model="form.phone"
              type="tel"
              :placeholder="$t('register.form.basicInfo.phone.placeholder')"
              required
            />
            <span v-if="errors.phone" class="error">{{ errors.phone }}</span>
          </div>
          
          <div class="form-group">
            <label for="idCard">{{ $t('register.form.basicInfo.idCard.label') }} *</label>
            <input
              id="idCard"
              v-model="form.idCard"
              type="text"
              :placeholder="$t('register.form.basicInfo.idCard.placeholder')"
              required
            />
            <span v-if="errors.idCard" class="error">{{ errors.idCard }}</span>
          </div>
        </div>
        
        <!-- Contact Information -->
        <div class="form-section">
          <h2>{{ $t('register.form.contactInfo.title') }}</h2>
          
          <div class="form-group">
            <label for="email">{{ $t('register.form.contactInfo.email.label') }}</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              :placeholder="$t('register.form.contactInfo.email.placeholder')"
            />
            <span v-if="errors.email" class="error">{{ errors.email }}</span>
          </div>
          
          <div class="form-group">
            <label for="address">{{ $t('register.form.contactInfo.address.label') }}</label>
            <input
              id="address"
              v-model="form.address"
              type="text"
              :placeholder="$t('register.form.contactInfo.address.placeholder')"
            />
            <span v-if="errors.address" class="error">{{ errors.address }}</span>
          </div>
        </div>
        
        <!-- Emergency Contact -->
        <div class="form-section">
          <h2>{{ $t('register.form.emergencyContact.title') }}</h2>
          
          <div class="form-group">
            <label for="emergencyName">{{ $t('register.form.emergencyContact.name.label') }} *</label>
            <input
              id="emergencyName"
              v-model="form.emergencyContact.name"
              type="text"
              :placeholder="$t('register.form.emergencyContact.name.placeholder')"
              required
            />
            <span v-if="errors['emergencyContact.name']" class="error">{{ errors['emergencyContact.name'] }}</span>
          </div>
          
          <div class="form-group">
            <label for="emergencyPhone">{{ $t('register.form.emergencyContact.phone.label') }} *</label>
            <input
              id="emergencyPhone"
              v-model="form.emergencyContact.phone"
              type="tel"
              :placeholder="$t('register.form.emergencyContact.phone.placeholder')"
              required
            />
            <span v-if="errors['emergencyContact.phone']" class="error">{{ errors['emergencyContact.phone'] }}</span>
          </div>
          
          <div class="form-group">
            <label for="emergencyRelationship">{{ $t('register.form.emergencyContact.relationship.label') }} *</label>
            <select id="emergencyRelationship" v-model="form.emergencyContact.relationship" required>
              <option value="">{{ $t('register.form.emergencyContact.relationship.placeholder') }}</option>
              <option value="parent">{{ $t('register.form.emergencyContact.relationship.options.parent') }}</option>
              <option value="spouse">{{ $t('register.form.emergencyContact.relationship.options.spouse') }}</option>
              <option value="sibling">{{ $t('register.form.emergencyContact.relationship.options.sibling') }}</option>
              <option value="friend">{{ $t('register.form.emergencyContact.relationship.options.friend') }}</option>
              <option value="other">{{ $t('register.form.emergencyContact.relationship.options.other') }}</option>
            </select>
            <span v-if="errors['emergencyContact.relationship']" class="error">{{ errors['emergencyContact.relationship'] }}</span>
          </div>
        </div>
        
        <!-- Privacy Policy -->
        <div class="form-section">
          <div class="form-group checkbox-group">
            <label>
              <input type="checkbox" v-model="form.agreeToTerms" required />
              {{ $t('register.form.privacy.agree') }}
            </label>
            <span v-if="errors.agreeToTerms" class="error">{{ errors.agreeToTerms }}</span>
          </div>
        </div>
        
        <!-- Submit Button -->
        <div class="form-actions">
          <button type="submit" :disabled="isSubmitting" class="submit-btn">
            {{ isSubmitting ? $t('register.submit.processing') : $t('register.submit.button') }}
          </button>
        </div>
      </form>
      
      <!-- Success Message -->
      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
      </div>
      
      <!-- Error Message -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { registerMember } from '@/services/api'

const { t } = useI18n()
const router = useRouter()

const isSubmitting = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

const form = reactive({
  name: '',
  gender: '',
  phone: '',
  idCard: '',
  email: '',
  address: '',
  emergencyContact: {
    name: '',
    phone: '',
    relationship: ''
  },
  agreeToTerms: false
})

const errors = reactive({})

const validateForm = () => {
  const newErrors = {}
  
  // Basic info validation
  if (!form.name) {
    newErrors.name = t('register.form.basicInfo.name.required')
  }
  
  if (!form.gender) {
    newErrors.gender = t('register.form.basicInfo.gender.required')
  }
  
  if (!form.phone) {
    newErrors.phone = t('register.form.basicInfo.phone.required')
  } else if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    newErrors.phone = t('register.form.basicInfo.phone.invalid')
  }
  
  if (!form.idCard) {
    newErrors.idCard = t('register.form.basicInfo.idCard.required')
  } else if (!/(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/.test(form.idCard)) {
    newErrors.idCard = t('register.form.basicInfo.idCard.invalid')
  }
  
  // Email validation
  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    newErrors.email = t('register.form.contactInfo.email.invalid')
  }
  
  // Emergency contact validation
  if (!form.emergencyContact.name) {
    newErrors['emergencyContact.name'] = t('register.form.emergencyContact.name.required')
  }
  
  if (!form.emergencyContact.phone) {
    newErrors['emergencyContact.phone'] = t('register.form.emergencyContact.phone.required')
  } else if (!/^1[3-9]\d{9}$/.test(form.emergencyContact.phone)) {
    newErrors['emergencyContact.phone'] = t('register.form.emergencyContact.phone.invalid')
  }
  
  if (!form.emergencyContact.relationship) {
    newErrors['emergencyContact.relationship'] = t('register.form.emergencyContact.relationship.required')
  }
  
  // Terms agreement
  if (!form.agreeToTerms) {
    newErrors.agreeToTerms = t('register.form.privacy.required')
  }
  
  Object.assign(errors, newErrors)
  return Object.keys(newErrors).length === 0
}

const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }
  
  isSubmitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const response = await registerMember(form)
    successMessage.value = t('register.submit.success', { id: response.memberId })
    
    // Reset form after successful registration
    setTimeout(() => {
      router.push('/login')
    }, 3000)
  } catch (error) {
    errorMessage.value = t('register.submit.error')
    console.error('Registration error:', error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.register-view {
  padding: 2rem 0;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
}

.register-form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.form-section {
  margin-bottom: 2rem;
}

.form-section h2 {
  margin-bottom: 1rem;
  color: #555;
  font-size: 1.2rem;
  border-bottom: 2px solid #eee;
  padding-bottom: 0.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #4CAF50;
}

.checkbox-group {
  display: flex;
  align-items: center;
}

.checkbox-group input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}

.error {
  color: #f44336;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}

.form-actions {
  text-align: center;
  margin-top: 2rem;
}

.submit-btn {
  background-color: #4CAF50;
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  font-size: 1.1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover:not(:disabled) {
  background-color: #45a049;
}

.submit-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.success-message {
  background-color: #dff0d8;
  color: #3c763d;
  padding: 1rem;
  margin-top: 1rem;
  border-radius: 4px;
  text-align: center;
}

.error-message {
  background-color: #f2dede;
  color: #a94442;
  padding: 1rem;
  margin-top: 1rem;
  border-radius: 4px;
  text-align: center;
}

@media (max-width: 768px) {
  .register-form {
    padding: 1rem;
  }
  
  .form-group input,
  .form-group select {
    padding: 0.5rem;
  }
}
</style>