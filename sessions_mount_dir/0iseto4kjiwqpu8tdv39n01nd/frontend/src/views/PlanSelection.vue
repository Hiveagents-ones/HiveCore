<template>
  <div class="plan-selection">
    <div class="container">
      <header class="page-header">
        <h1>选择会员套餐</h1>
        <p>选择最适合您的会员套餐，享受更多专属权益</p>
      </header>

      <div class="plans-grid" v-if="!loading">
        <div 
          v-for="plan in plans" 
          :key="plan.id"
          class="plan-card"
          :class="{ 'selected': selectedPlan?.id === plan.id, 'popular': plan.is_popular }"
          @click="selectPlan(plan)"
        >
          <div v-if="plan.is_popular" class="popular-badge">最受欢迎</div>
          
          <div class="plan-header">
            <h3>{{ plan.name }}</h3>
            <div class="price">
              <span class="currency">¥</span>
              <span class="amount">{{ plan.price }}</span>
              <span class="period">/{{ plan.billing_cycle }}</span>
            </div>
          </div>

          <div class="plan-features">
            <ul>
              <li v-for="feature in plan.features" :key="feature">
                <i class="icon-check"></i>
                {{ feature }}
              </li>
            </ul>
          </div>

          <button 
            class="select-btn"
            :class="{ 'selected': selectedPlan?.id === plan.id }"
            @click.stop="handleSelectPlan(plan)"
          >
            {{ selectedPlan?.id === plan.id ? '已选择' : '选择此套餐' }}
          </button>
        </div>
      </div>

      <div v-else class="loading">
        <div class="spinner"></div>
        <p>加载套餐信息中...</p>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <div class="payment-section" v-if="selectedPlan">
        <h2>选择支付方式</h2>
        <div class="payment-methods">
          <div 
            v-for="method in paymentMethods" 
            :key="method.id"
            class="payment-method"
            :class="{ 'selected': selectedPaymentMethod === method.id }"
            @click="selectPaymentMethod(method.id)"
          >
            <img :src="method.icon" :alt="method.name" class="payment-icon">
            <span>{{ method.name }}</span>
          </div>
        </div>

        <button 
          class="purchase-btn"
          :disabled="!selectedPaymentMethod || processing"
          @click="handlePurchase"
        >
          <span v-if="!processing">立即购买 ¥{{ selectedPlan.price }}</span>
          <span v-else>处理中...</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSubscriptionStore } from '@/stores/subscription'
import { usePaymentStore } from '@/stores/payment'

const router = useRouter()
const subscriptionStore = useSubscriptionStore()
const paymentStore = usePaymentStore()

const plans = ref([])
const selectedPlan = ref(null)
const selectedPaymentMethod = ref(null)
const loading = ref(true)
const error = ref(null)
const processing = ref(false)

const paymentMethods = [
  { id: 'alipay', name: '支付宝', icon: '/icons/alipay.svg' },
  { id: 'wechat', name: '微信支付', icon: '/icons/wechat.svg' },
  { id: 'stripe', name: '信用卡/借记卡', icon: '/icons/stripe.svg' }
]

const fetchPlans = async () => {
  try {
    loading.value = true
    const response = await subscriptionStore.fetchPlans()
    plans.value = response.data
  } catch (err) {
    error.value = '加载套餐信息失败，请稍后重试'
    console.error('Failed to fetch plans:', err)
  } finally {
    loading.value = false
  }
}

const selectPlan = (plan) => {
  selectedPlan.value = plan
}

const selectPaymentMethod = (methodId) => {
  selectedPaymentMethod.value = methodId
}

const handleSelectPlan = (plan) => {
  selectPlan(plan)
  // 滚动到支付部分
  document.querySelector('.payment-section')?.scrollIntoView({ 
    behavior: 'smooth',
    block: 'center'
  })
}

const handlePurchase = async () => {
  if (!selectedPlan.value || !selectedPaymentMethod.value) return

  try {
    processing.value = true
    error.value = null

    const orderData = {
      plan_id: selectedPlan.value.id,
      payment_method: selectedPaymentMethod.value
    }

    const response = await paymentStore.createOrder(orderData)
    
    // 根据支付方式处理支付
    if (selectedPaymentMethod.value === 'alipay' || selectedPaymentMethod.value === 'wechat') {
      // 跳转到支付页面
      window.location.href = response.data.payment_url
    } else if (selectedPaymentMethod.value === 'stripe') {
      // 使用Stripe Checkout
      const stripe = Stripe(response.data.stripe_public_key)
      await stripe.redirectToCheckout({
        sessionId: response.data.session_id
      })
    }
  } catch (err) {
    error.value = err.response?.data?.message || '创建订单失败，请重试'
    console.error('Purchase failed:', err)
  } finally {
    processing.value = false
  }
}

onMounted(() => {
  fetchPlans()
})
</script>

<style scoped>
.plan-selection {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  text-align: center;
  color: white;
  margin-bottom: 3rem;
}

.page-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.page-header p {
  font-size: 1.2rem;
  opacity: 0.9;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.plan-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
}

.plan-card.selected {
  border: 2px solid #667eea;
  transform: scale(1.02);
}

.plan-card.popular {
  border: 2px solid #f59e0b;
}

.popular-badge {
  position: absolute;
  top: -12px;
  right: 20px;
  background: #f59e0b;
  color: white;
  padding: 0.25rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: bold;
}

.plan-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.plan-header h3 {
  font-size: 1.5rem;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.price {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.25rem;
}

.currency {
  font-size: 1.5rem;
  color: #6b7280;
}

.amount {
  font-size: 3rem;
  font-weight: bold;
  color: #1f2937;
}

.period {
  font-size: 1rem;
  color: #6b7280;
}

.plan-features ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.plan-features li {
  padding: 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #4b5563;
}

.icon-check {
  color: #10b981;
  font-weight: bold;
}

.icon-check::before {
  content: '✓';
}

.select-btn {
  width: 100%;
  padding: 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s ease;
  margin-top: 1.5rem;
}

.select-btn:hover {
  background: #5a67d8;
}

.select-btn.selected {
  background: #10b981;
}

.loading {
  text-align: center;
  color: white;
  padding: 3rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  background: #ef4444;
  color: white;
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
  margin-bottom: 2rem;
}

.payment-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-top: 2rem;
}

.payment-section h2 {
  color: #1f2937;
  margin-bottom: 1.5rem;
  text-align: center;
}

.payment-methods {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.payment-method {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 120px;
}

.payment-method:hover {
  border-color: #667eea;
}

.payment-method.selected {
  border-color: #667eea;
  background: #f3f4f6;
}

.payment-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 0.5rem;
}

.purchase-btn {
  width: 100%;
  max-width: 400px;
  padding: 1rem;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.125rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s ease;
  display: block;
  margin: 0 auto;
}

.purchase-btn:hover:not(:disabled) {
  background: #059669;
}

.purchase-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .page-header h1 {
    font-size: 2rem;
  }
  
  .plans-grid {
    grid-template-columns: 1fr;
  }
  
  .payment-methods {
    flex-direction: column;
    align-items: center;
  }
  
  .payment-method {
    width: 100%;
    max-width: 300px;
  }
}
</style>