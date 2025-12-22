<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ $t('payment.title') }}</h2>
        <button class="close-btn" @click="closeModal">&times;</button>
      </div>
      
      <div class="modal-body">
        <div v-if="selectedPlan" class="selected-plan">
          <h3>{{ $t('payment.selectedPlan') }}</h3>
          <div class="plan-info">
            <h4>{{ selectedPlan.name }}</h4>
            <p class="price">{{ formatCurrency(selectedPlan.price) }}</p>
            <p class="duration">{{ selectedPlan.duration }}</p>
          </div>
        </div>

        <div class="payment-methods">
          <h3>{{ $t('payment.selectMethod') }}</h3>
          <div class="method-options">
            <label v-for="method in paymentMethods" :key="method.id" class="method-option">
              <input 
                type="radio" 
                :value="method.id" 
                v-model="selectedPaymentMethod"
                name="payment-method"
              >
              <span class="method-icon">{{ method.icon }}</span>
              <span class="method-name">{{ method.name }}</span>
            </label>
          </div>
        </div>

        <div v-if="selectedPaymentMethod" class="payment-details">
          <h3>{{ $t('payment.paymentDetails') }}</h3>
          <div v-if="selectedPaymentMethod === 'card'" class="card-form">
            <div class="form-group">
              <label>{{ $t('payment.cardNumber') }}</label>
              <input 
                type="text" 
                v-model="cardDetails.number" 
                placeholder="1234 5678 9012 3456"
                maxlength="19"
                @input="formatCardNumber"
              >
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('payment.expiryDate') }}</label>
                <input 
                  type="text" 
                  v-model="cardDetails.expiry" 
                  placeholder="MM/YY"
                  maxlength="5"
                  @input="formatExpiryDate"
                >
              </div>
              <div class="form-group">
                <label>{{ $t('payment.cvv') }}</label>
                <input 
                  type="text" 
                  v-model="cardDetails.cvv" 
                  placeholder="123"
                  maxlength="3"
                >
              </div>
            </div>
            <div class="form-group">
              <label>{{ $t('payment.cardholderName') }}</label>
              <input 
                type="text" 
                v-model="cardDetails.name" 
                :placeholder="$t('payment.namePlaceholder')"
              >
            </div>
          </div>
          
          <div v-else-if="selectedPaymentMethod === 'alipay'" class="alipay-info">
            <p>{{ $t('payment.alipayRedirect') }}</p>
          </div>
          
          <div v-else-if="selectedPaymentMethod === 'wechat'" class="wechat-info">
            <p>{{ $t('payment.wechatRedirect') }}</p>
          </div>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </div>

      <div class="modal-footer">
        <button 
          class="btn btn-secondary" 
          @click="closeModal"
        >
          {{ $t('common.cancel') }}
        </button>
        <button 
          class="btn btn-primary" 
          @click="processPayment"
          :disabled="!canProcessPayment || isProcessing"
        >
          <span v-if="isProcessing" class="spinner"></span>
          {{ isProcessing ? $t('payment.processing') : $t('payment.payNow') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { paymentAPI } from '@/services/api';

export default {
  name: 'PaymentModal',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    selectedPlan: {
      type: Object,
      default: null
    }
  },
  emits: ['close', 'payment-success', 'payment-error'],
  setup(props, { emit }) {
    const { t } = useI18n();
    
    const selectedPaymentMethod = ref('');
    const isProcessing = ref(false);
    const error = ref('');
    
    const cardDetails = ref({
      number: '',
      expiry: '',
      cvv: '',
      name: ''
    });
    
    const paymentMethods = ref([
      { id: 'card', name: t('payment.creditCard'), icon: '💳' },
      { id: 'alipay', name: t('payment.alipay'), icon: '💙' },
      { id: 'wechat', name: t('payment.wechatPay'), icon: '💚' }
    ]);
    
    const canProcessPayment = computed(() => {
      if (!props.selectedPlan || !selectedPaymentMethod.value) return false;
      
      if (selectedPaymentMethod.value === 'card') {
        const { number, expiry, cvv, name } = cardDetails.value;
        return number.length === 19 && expiry.length === 5 && cvv.length === 3 && name.trim();
      }
      
      return true;
    });
    
    const formatCurrency = (amount) => {
      return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY'
      }).format(amount);
    };
    
    const formatCardNumber = (e) => {
      let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
      const matches = value.match(/\d{4,16}/g);
      const match = matches && matches[0] || '';
      const parts = [];
      
      for (let i = 0, len = match.length; i < len; i += 4) {
        parts.push(match.substring(i, i + 4));
      }
      
      if (parts.length) {
        cardDetails.value.number = parts.join(' ');
      } else {
        cardDetails.value.number = value;
      }
    };
    
    const formatExpiryDate = (e) => {
      let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
      if (value.length >= 2) {
        value = value.substring(0, 2) + '/' + value.substring(2, 4);
      }
      cardDetails.value.expiry = value;
    };
    
    const closeModal = () => {
      emit('close');
      resetForm();
    };
    
    const resetForm = () => {
      selectedPaymentMethod.value = '';
      cardDetails.value = {
        number: '',
        expiry: '',
        cvv: '',
        name: ''
      };
      error.value = '';
    };
    
    const processPayment = async () => {
      if (!canProcessPayment.value) return;
      
      isProcessing.value = true;
      error.value = '';
      
      try {
        const paymentData = {
          plan_id: props.selectedPlan.id,
          payment_method: selectedPaymentMethod.value
        };
        
        if (selectedPaymentMethod.value === 'card') {
          paymentData.card_details = cardDetails.value;
        }
        
        const response = await paymentAPI.createPaymentIntent(paymentData);
        
        if (response.requires_action) {
          // Handle 3D Secure or other authentication if needed
          window.location.href = response.redirect_url;
        } else {
          // Payment successful
          emit('payment-success', response);
          closeModal();
        }
      } catch (err) {
        error.value = err.message || t('payment.paymentFailed');
        emit('payment-error', err);
      } finally {
        isProcessing.value = false;
      }
    };
    
    watch(() => props.isVisible, (newVal) => {
      if (newVal) {
        resetForm();
      }
    });
    
    return {
      selectedPaymentMethod,
      isProcessing,
      error,
      cardDetails,
      paymentMethods,
      canProcessPayment,
      formatCurrency,
      formatCardNumber,
      formatExpiryDate,
      closeModal,
      processPayment
    };
  }
};
</script>

<style scoped>
.modal-overlay {
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

.modal-content {
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

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
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
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.selected-plan h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.1rem;
  color: #555;
}

.plan-info h4 {
  margin: 0 0 5px 0;
  color: #333;
}

.price {
  font-size: 1.5rem;
  font-weight: bold;
  color: #e63946;
  margin: 5px 0;
}

.duration {
  color: #666;
  margin: 0;
}

.payment-methods {
  margin-bottom: 20px;
}

.payment-methods h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.1rem;
  color: #555;
}

.method-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.method-option {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.method-option:hover {
  border-color: #4361ee;
  background-color: #f8f9ff;
}

.method-option input[type="radio"] {
  margin-right: 10px;
}

.method-icon {
  font-size: 1.2rem;
  margin-right: 10px;
}

.method-name {
  font-weight: 500;
}

.payment-details {
  margin-bottom: 20px;
}

.payment-details h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.1rem;
  color: #555;
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

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #4361ee;
  box-shadow: 0 0 0 2px rgba(67, 97, 238, 0.2);
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-row .form-group {
  flex: 1;
}

.alipay-info, .wechat-info {
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
  text-align: center;
}

.error-message {
  padding: 10px;
  background-color: #ffebee;
  color: #c62828;
  border-radius: 4px;
  margin-top: 15px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #eee;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.btn-secondary {
  background-color: #e9ecef;
  color: #495057;
}

.btn-secondary:hover {
  background-color: #dee2e6;
}

.btn-primary {
  background-color: #4361ee;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #3a56d4;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 0.8s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 576px) {
  .modal-content {
    width: 95%;
  }
  
  .form-row {
    flex-direction: column;
    gap: 0;
  }
}
</style>