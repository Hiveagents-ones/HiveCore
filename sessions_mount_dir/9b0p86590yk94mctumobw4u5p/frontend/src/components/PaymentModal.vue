<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ $t('payment.title') }}</h2>
        <button class="close-btn" @click="closeModal">&times;</button>
      </div>
      
      <div class="modal-body">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <p>{{ $t('payment.processing') }}</p>
        </div>
        
        <div v-else-if="error" class="error-message">
          <p>{{ error }}</p>
          <button @click="retryPayment" class="retry-btn">{{ $t('payment.retry') }}</button>
        </div>
        
        <div v-else-if="paymentSuccess" class="success-message">
          <p>{{ $t('payment.success') }}</p>
          <button @click="closeModal" class="close-modal-btn">{{ $t('payment.close') }}</button>
        </div>
        
        <div v-else class="payment-form">
          <div class="plan-info">
            <h3>{{ selectedPlan?.name }}</h3>
            <p class="price">{{ formatCurrency(selectedPlan?.price) }}</p>
            <p class="duration">{{ $t('payment.duration', { months: selectedPlan?.duration_months }) }}</p>
          </div>
          
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label for="card-element">{{ $t('payment.cardInfo') }}</label>
              <div id="card-element" class="card-element"></div>
            </div>
            
            <div v-if="cardError" class="card-error">
              {{ cardError }}
            </div>
            
            <button type="submit" class="pay-btn" :disabled="processing">
              {{ processing ? $t('payment.processing') : $t('payment.pay') }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { loadStripe } from '@stripe/stripe-js'
import { apiMethods } from '@/services/api'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notification'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  selectedPlan: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'success'])

const { t } = useI18n()
const notificationStore = useNotificationStore()

const stripe = ref(null)
const elements = ref(null)
const cardElement = ref(null)
const clientSecret = ref('')
const loading = ref(false)
const processing = ref(false)
const error = ref('')
const cardError = ref('')
const paymentSuccess = ref(false)

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount / 100)
}

const closeModal = () => {
  emit('close')
  resetState()
}

const resetState = () => {
  loading.value = false
  processing.value = false
  error.value = ''
  cardError.value = ''
  paymentSuccess.value = false
  clientSecret.value = ''
}

const initializeStripe = async () => {
  try {
    loading.value = true
    
    // Load Stripe
    stripe.value = await loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY)
    
    // Create payment intent
    const response = await apiMethods.payment.createPaymentIntent(props.selectedPlan.id)
    clientSecret.value = response.client_secret
    
    // Create elements
    elements.value = stripe.value.elements({
      clientSecret: clientSecret.value,
      appearance: {
        theme: 'stripe',
        variables: {
          colorPrimary: '#0570de',
          colorBackground: '#ffffff',
          colorText: '#30313d',
          colorDanger: '#df1b41',
          fontFamily: 'system-ui, sans-serif',
          spacingUnit: '4px',
          borderRadius: '6px'
        }
      }
    })
    
    // Create and mount card element
    cardElement.value = elements.value.create('payment', {
      layout: 'tabs'
    })
    
    cardElement.value.mount('#card-element')
    
    // Handle card element errors
    cardElement.value.on('change', ({ error }) => {
      cardError.value = error ? error.message : ''
    })
    
    loading.value = false
  } catch (err) {
    console.error('Stripe initialization error:', err)
    error.value = t('payment.initError')
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!stripe.value || !elements.value) return
  
  try {
    processing.value = true
    
    const { error: submitError } = await elements.value.submit()
    if (submitError) {
      cardError.value = submitError.message
      processing.value = false
      return
    }
    
    // Confirm payment
    const { error, paymentIntent } = await stripe.value.confirmPayment({
      elements: elements.value,
      clientSecret: clientSecret.value,
      confirmParams: {
        return_url: `${window.location.origin}/payment/success`,
      },
      redirect: 'if_required'
    })
    
    if (error) {
      if (error.type === 'card_error' || error.type === 'validation_error') {
        cardError.value = error.message
      } else {
        error.value = t('payment.paymentError')
      }
      processing.value = false
      return
    }
    
    // Handle 3D Secure if required
    if (paymentIntent && paymentIntent.status === 'requires_action') {
      const { error: confirmError } = await stripe.value.confirmCardPayment(clientSecret.value)
      if (confirmError) {
        error.value = t('payment.verificationFailed')
        processing.value = false
        return
      }
    }
    
    // Payment successful
    await apiMethods.payment.confirmPayment(paymentIntent.id)
    paymentSuccess.value = true
    emit('success')
    notificationStore.showSuccess(t('payment.success'))
    
    setTimeout(() => {
      closeModal()
    }, 2000)
    
  } catch (err) {
    console.error('Payment error:', err)
    error.value = t('payment.paymentError')
  } finally {
    processing.value = false
  }
}

const retryPayment = () => {
  resetState()
  initializeStripe()
}

// Watch for modal open/close
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    initializeStripe()
  } else {
    if (cardElement.value) {
      cardElement.value.destroy()
    }
  }
})

// Cleanup on unmount
onBeforeUnmount(() => {
  if (cardElement.value) {
    cardElement.value.destroy()
  }
})
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
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
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
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #374151;
}

.modal-body {
  padding: 24px;
}

.loading {
  text-align: center;
  padding: 40px 0;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  text-align: center;
  color: #dc2626;
  padding: 20px;
}

.retry-btn {
  background-color: #dc2626;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 15px;
  font-size: 1rem;
}

.retry-btn:hover {
  background-color: #b91c1c;
}

.success-message {
  text-align: center;
  color: #059669;
  padding: 20px;
}

.close-modal-btn {
  background-color: #059669;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 15px;
  font-size: 1rem;
}

.close-modal-btn:hover {
  background-color: #047857;
}

.payment-form {
  max-width: 400px;
  margin: 0 auto;
}

.plan-info {
  text-align: center;
  margin-bottom: 30px;
  padding: 20px;
  background-color: #f9fafb;
  border-radius: 8px;
}

.plan-info h3 {
  margin: 0 0 10px;
  color: #1f2937;
  font-size: 1.25rem;
}

.price {
  font-size: 2rem;
  font-weight: bold;
  color: #059669;
  margin: 10px 0;
}

.duration {
  color: #6b7280;
  margin: 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #374151;
}

.card-element {
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background-color: white;
}

.card-error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-top: 8px;
}

.pay-btn {
  width: 100%;
  background-color: #059669;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.pay-btn:hover:not(:disabled) {
  background-color: #047857;
}

.pay-btn:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}
</style>