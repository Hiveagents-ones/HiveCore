<template>
  <div v-if="isVisible" class="payment-modal-overlay" @click.self="closeModal">
    <div class="payment-modal">
      <div class="modal-header">
        <h2>{{ $t('payment.title') }}</h2>
        <button class="close-btn" @click="closeModal">&times;</button>
      </div>
      
      <div class="modal-body">
        <div class="package-selection">
          <h3>{{ $t('payment.selectPackage') }}</h3>
          <div class="packages">
            <div 
              v-for="pkg in packages" 
              :key="pkg.id"
              class="package-card"
              :class="{ 'selected': selectedPackage?.id === pkg.id }"
              @click="selectPackage(pkg)"
            >
              <h4>{{ pkg.name }}</h4>
              <div class="price">{{ formatPrice(pkg.price) }}</div>
              <ul class="benefits">
                <li v-for="benefit in pkg.benefits" :key="benefit">
                  {{ benefit }}
                </li>
              </ul>
            </div>
          </div>
        </div>
        
        <div class="payment-methods">
          <h3>{{ $t('payment.selectMethod') }}</h3>
          <div class="methods">
            <label 
              v-for="method in paymentMethods" 
              :key="method.id"
              class="method-option"
            >
              <input 
                type="radio" 
                name="payment-method" 
                :value="method.id"
                v-model="selectedMethod"
              >
              <span class="method-icon">{{ method.icon }}</span>
              <span class="method-name">{{ method.name }}</span>
            </label>
          </div>
        </div>
        
        <div class="security-notice">
          <div class="security-icon">🔒</div>
          <p>{{ $t('payment.securityNotice') }}</p>
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          class="cancel-btn" 
          @click="closeModal"
          :disabled="isProcessing"
        >
          {{ $t('common.cancel') }}
        </button>
        <button 
          class="confirm-btn" 
          @click="processPayment"
          :disabled="!canProcess || isProcessing"
        >
          <span v-if="isProcessing" class="loading-spinner"></span>
          {{ isProcessing ? $t('payment.processing') : $t('payment.confirm') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePaymentStore } from '@/stores/payment'
import { useUserStore } from '@/stores/user'

const { t } = useI18n()
const paymentStore = usePaymentStore()
const userStore = useUserStore()

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  packages: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['close', 'success', 'error'])

const selectedPackage = ref(null)
const selectedMethod = ref('credit_card')
const isProcessing = ref(false)

const paymentMethods = [
  { id: 'credit_card', name: t('payment.creditCard'), icon: '💳' },
  { id: 'alipay', name: t('payment.alipay'), icon: '💙' },
  { id: 'wechat', name: t('payment.wechatPay'), icon: '💚' },
  { id: 'paypal', name: t('payment.paypal'), icon: '💰' }
]

const canProcess = computed(() => {
  return selectedPackage.value && selectedMethod.value && !isProcessing.value
})

const selectPackage = (pkg) => {
  selectedPackage.value = pkg
}

const formatPrice = (price) => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  }).format(price)
}

const closeModal = () => {
  if (!isProcessing.value) {
    emit('close')
    resetForm()
  }
}

const resetForm = () => {
  selectedPackage.value = null
  selectedMethod.value = 'credit_card'
  isProcessing.value = false
}

const processPayment = async () => {
  if (!canProcess.value) return
  
  isProcessing.value = true
  
  try {
    const paymentData = {
      packageId: selectedPackage.value.id,
      method: selectedMethod.value,
      userId: userStore.currentUser.id
    }
    
    const result = await paymentStore.processPayment(paymentData)
    
    if (result.success) {
      emit('success', result)
      closeModal()
    } else {
      emit('error', result.message)
    }
  } catch (error) {
    console.error('Payment error:', error)
    emit('error', t('payment.error.general'))
  } finally {
    isProcessing.value = false
  }
}

watch(() => props.isVisible, (newVal) => {
  if (!newVal) {
    resetForm()
  }
})
</script>

<style scoped>
.payment-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.payment-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  background-color: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 24px;
}

.package-selection h3,
.payment-methods h3 {
  margin: 0 0 16px 0;
  font-size: 1.125rem;
  color: #374151;
}

.packages {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.package-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.package-card:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.package-card.selected {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.package-card h4 {
  margin: 0 0 8px 0;
  font-size: 1.125rem;
  color: #1f2937;
}

.price {
  font-size: 1.5rem;
  font-weight: bold;
  color: #3b82f6;
  margin-bottom: 12px;
}

.benefits {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
}

.benefits li {
  padding: 4px 0;
  font-size: 0.875rem;
  color: #6b7280;
  position: relative;
  padding-left: 20px;
}

.benefits li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #10b981;
}

.methods {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.method-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.method-option:hover {
  border-color: #3b82f6;
  background-color: #f9fafb;
}

.method-option input[type="radio"] {
  margin-bottom: 8px;
}

.method-icon {
  font-size: 1.5rem;
  margin-bottom: 4px;
}

.method-name {
  font-size: 0.875rem;
  color: #374151;
}

.security-notice {
  display: flex;
  align-items: center;
  padding: 12px;
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  margin-top: 16px;
}

.security-icon {
  font-size: 1.25rem;
  margin-right: 8px;
}

.security-notice p {
  margin: 0;
  font-size: 0.875rem;
  color: #166534;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #e5e7eb;
}

.cancel-btn,
.confirm-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.cancel-btn {
  background-color: #f3f4f6;
  color: #374151;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #e5e7eb;
}

.confirm-btn {
  background-color: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  gap: 8px;
}

.confirm-btn:hover:not(:disabled) {
  background-color: #2563eb;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #ffffff;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 640px) {
  .payment-modal {
    width: 95%;
    margin: 16px;
  }
  
  .packages {
    grid-template-columns: 1fr;
  }
  
  .methods {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>