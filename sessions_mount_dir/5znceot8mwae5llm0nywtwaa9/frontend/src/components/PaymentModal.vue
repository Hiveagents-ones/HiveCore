<template>
  <div v-if="isVisible" class="payment-modal-overlay" @click="closeModal">
    <div class="payment-modal" @click.stop>
      <div class="modal-header">
        <h3>{{ $t('payment.title') }}</h3>
        <button class="close-btn" @click="closeModal">&times;</button>
      </div>
      
      <div class="modal-body">
        <div class="selected-plan">
          <h4>{{ $t('payment.selectedPlan') }}</h4>
          <div class="plan-info">
            <span class="plan-name">{{ selectedPlan.name }}</span>
            <span class="plan-price">{{ formatPrice(selectedPlan.price) }}</span>
          </div>
        </div>

        <div class="payment-methods">
          <h4>{{ $t('payment.selectMethod') }}</h4>
          <div class="method-options">
            <label class="method-option" v-for="method in paymentMethods" :key="method.id">
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

        <div class="payment-form" v-if="selectedMethod">
          <div v-if="selectedMethod === 'wechat' || selectedMethod === 'alipay'">
            <p class="online-payment-hint">{{ $t('payment.onlinePaymentHint') }}</p>
          </div>
          
          <div v-else-if="selectedMethod === 'offline'">
            <div class="form-group">
              <label for="offline-receipt">{{ $t('payment.receiptNumber') }}</label>
              <input 
                type="text" 
                id="offline-receipt" 
                v-model="offlineReceipt"
                :placeholder="$t('payment.enterReceiptNumber')"
              >
            </div>
            <div class="form-group">
              <label for="offline-note">{{ $t('payment.note') }}</label>
              <textarea 
                id="offline-note" 
                v-model="offlineNote"
                :placeholder="$t('payment.enterNote')"
                rows="3"
              ></textarea>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="closeModal">{{ $t('common.cancel') }}</button>
        <button 
          class="btn-confirm" 
          @click="processPayment"
          :disabled="!selectedMethod || isProcessing"
        >
          {{ isProcessing ? $t('payment.processing') : $t('payment.confirmPayment') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMembershipStore } from '@/stores/membership'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  selectedPlan: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'success'])

const { t } = useI18n()
const membershipStore = useMembershipStore()
const { showToast } = useToast()

const selectedMethod = ref('')
const offlineReceipt = ref('')
const offlineNote = ref('')
const isProcessing = ref(false)

const paymentMethods = computed(() => [
  { id: 'wechat', name: t('payment.wechatPay'), icon: '📱' },
  { id: 'alipay', name: t('payment.alipay'), icon: '💳' },
  { id: 'offline', name: t('payment.offlinePayment'), icon: '📋' }
])

const formatPrice = (price) => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  }).format(price)
}

const closeModal = () => {
  emit('close')
  resetForm()
}

const resetForm = () => {
  selectedMethod.value = ''
  offlineReceipt.value = ''
  offlineNote.value = ''
  isProcessing.value = false
}

const processPayment = async () => {
  if (!selectedMethod.value) {
    showToast(t('payment.selectMethodError'), 'error')
    return
  }

  if (selectedMethod.value === 'offline' && !offlineReceipt.value) {
    showToast(t('payment.receiptRequired'), 'error')
    return
  }

  isProcessing.value = true

  try {
    const paymentData = {
      planId: props.selectedPlan.id,
      method: selectedMethod.value,
      ...(selectedMethod.value === 'offline' && {
        receiptNumber: offlineReceipt.value,
        note: offlineNote.value
      })
    }

    const result = await membershipStore.processRenewal(paymentData)
    
    if (result.success) {
      showToast(t('payment.success'), 'success')
      emit('success', result)
      closeModal()
    } else {
      showToast(result.message || t('payment.failed'), 'error')
    }
  } catch (error) {
    console.error('Payment processing error:', error)
    showToast(t('payment.error'), 'error')
  } finally {
    isProcessing.value = false
  }
}

watch(() => props.isVisible, (newVal) => {
  if (newVal) {
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
}

.payment-modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.selected-plan {
  margin-bottom: 25px;
}

.selected-plan h4 {
  margin: 0 0 10px 0;
  font-size: 1rem;
  color: #666;
}

.plan-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.plan-name {
  font-weight: 600;
  color: #333;
}

.plan-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e74c3c;
}

.payment-methods {
  margin-bottom: 25px;
}

.payment-methods h4 {
  margin: 0 0 15px 0;
  font-size: 1rem;
  color: #666;
}

.method-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.method-option {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.method-option:hover {
  border-color: #3498db;
  background-color: #f8f9fa;
}

.method-option input[type="radio"] {
  margin-right: 12px;
}

.method-icon {
  font-size: 1.25rem;
  margin-right: 10px;
}

.method-name {
  font-weight: 500;
}

.payment-form {
  margin-bottom: 20px;
}

.online-payment-hint {
  padding: 15px;
  background-color: #e8f4fd;
  border-left: 4px solid #3498db;
  border-radius: 4px;
  color: #2c3e50;
  margin: 0;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #555;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3498db;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #eee;
}

.btn-cancel,
.btn-confirm {
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-cancel {
  background-color: #f8f9fa;
  color: #666;
}

.btn-cancel:hover {
  background-color: #e9ecef;
}

.btn-confirm {
  background-color: #3498db;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background-color: #2980b9;
}

.btn-confirm:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

@media (max-width: 576px) {
  .payment-modal {
    width: 95%;
  }
  
  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 15px;
  }
}
</style>