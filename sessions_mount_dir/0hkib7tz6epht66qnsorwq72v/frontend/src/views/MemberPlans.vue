<template>
  <div class="member-plans-container">
    <div class="page-header">
      <h1>选择会员套餐</h1>
      <p>选择最适合您的会员套餐，享受更多专属权益</p>
    </div>

    <div class="plans-grid" v-if="!loading">
      <div 
        v-for="plan in plans" 
        :key="plan.id"
        class="plan-card"
        :class="{ 
          'selected': selectedPlan?.id === plan.id,
          'popular': plan.is_popular 
        }"
        @click="selectPlan(plan)"
      >
        <div v-if="plan.is_popular" class="popular-badge">
          最受欢迎
        </div>
        
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
              <i class="fas fa-check"></i>
              {{ feature }}
            </li>
          </ul>
        </div>

        <div class="plan-action">
          <button 
            class="btn-select"
            :class="{ 'btn-selected': selectedPlan?.id === plan.id }"
          >
            {{ selectedPlan?.id === plan.id ? '已选择' : '选择此套餐' }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="loading-container">
      <div class="loading-spinner"></div>
      <p>加载套餐信息中...</p>
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
          <i :class="method.icon"></i>
          <span>{{ method.name }}</span>
        </div>
      </div>

      <button 
        class="btn-pay"
        @click="proceedToPayment"
        :disabled="!selectedPaymentMethod || processing"
      >
        <span v-if="!processing">立即支付 ¥{{ selectedPlan.price }}</span>
        <span v-else>处理中...</span>
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMembershipStore } from '@/stores/membership'
import { usePaymentStore } from '@/stores/payment'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const membershipStore = useMembershipStore()
const paymentStore = usePaymentStore()
const userStore = useUserStore()

const plans = ref([])
const selectedPlan = ref(null)
const selectedPaymentMethod = ref(null)
const loading = ref(true)
const processing = ref(false)
const error = ref('')

const paymentMethods = [
  { id: 'alipay', name: '支付宝', icon: 'fab fa-alipay' },
  { id: 'wechat', name: '微信支付', icon: 'fab fa-weixin' },
  { id: 'stripe', name: '信用卡/借记卡', icon: 'fas fa-credit-card' }
]

const selectPlan = (plan) => {
  selectedPlan.value = plan
  error.value = ''
}

const selectPaymentMethod = (methodId) => {
  selectedPaymentMethod.value = methodId
  error.value = ''
}

const proceedToPayment = async () => {
  if (!selectedPlan.value || !selectedPaymentMethod.value) {
    error.value = '请选择套餐和支付方式'
    return
  }

  processing.value = true
  error.value = ''

  try {
    const paymentData = {
      plan_id: selectedPlan.value.id,
      payment_method: selectedPaymentMethod.value,
      amount: selectedPlan.value.price,
      currency: 'CNY'
    }

    const response = await paymentStore.createPayment(paymentData)
    
    if (response.success) {
      // 根据支付方式跳转到相应的支付页面
      if (selectedPaymentMethod.value === 'alipay') {
        window.location.href = response.payment_url
      } else if (selectedPaymentMethod.value === 'wechat') {
        // 显示二维码或跳转到微信支付
        router.push({ 
          name: 'PaymentQR', 
          params: { paymentId: response.payment_id } 
        })
      } else if (selectedPaymentMethod.value === 'stripe') {
        // 跳转到Stripe Checkout
        window.location.href = response.checkout_url
      }
    } else {
      error.value = response.message || '创建支付失败，请重试'
    }
  } catch (err) {
    error.value = '支付处理失败，请重试'
    console.error('Payment error:', err)
  } finally {
    processing.value = false
  }
}

onMounted(async () => {
  // 检查用户是否已登录
  if (!userStore.isAuthenticated) {
    router.push({ name: 'Login' })
    return
  }

  try {
    const response = await membershipStore.getMembershipPlans()
    plans.value = response.plans || []
  } catch (err) {
    error.value = '加载套餐信息失败'
    console.error('Failed to load plans:', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.member-plans-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: #f8f9fa;
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.page-header p {
  font-size: 1.1rem;
  color: #7f8c8d;
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
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  border: 2px solid transparent;
  overflow: hidden;
}

.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
}

.plan-card.selected {
  border-color: #3498db;
  background: #f0f9ff;
}

.plan-card.popular {
  border-color: #e74c3c;
  transform: scale(1.02);
}

.popular-badge {
  position: absolute;
  top: -12px;
  right: 20px;
  background: #e74c3c;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: bold;
}

.plan-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.plan-header h3 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin-bottom: 1rem;
}

.price {
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.currency {
  font-size: 1.2rem;
  color: #7f8c8d;
  margin-right: 4px;
}

.amount {
  font-size: 2.5rem;
  font-weight: bold;
  color: #2c3e50;
}

.period {
  font-size: 1rem;
  color: #7f8c8d;
  margin-left: 4px;
}

.plan-features ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.plan-features li {
  padding: 0.5rem 0;
  color: #34495e;
  display: flex;
  align-items: center;
}

.plan-features i {
  color: #27ae60;
  margin-right: 0.5rem;
}

.plan-action {
  margin-top: 1.5rem;
}

.btn-select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #3498db;
  background: white;
  color: #3498db;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-select:hover {
  background: #3498db;
  color: white;
}

.btn-select.btn-selected {
  background: #3498db;
  color: white;
}

.loading-container {
  text-align: center;
  padding: 3rem;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.payment-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  animation: slideUp 0.5s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.payment-section h2 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin-bottom: 1.5rem;
}

.payment-methods {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.payment-method {
  flex: 1;
  min-width: 150px;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.payment-method:hover {
  border-color: #3498db;
  background: #f0f9ff;
}

.payment-method.selected {
  border-color: #3498db;
  background: #3498db;
  color: white;
}

.payment-method i {
  font-size: 2rem;
}

.btn-pay {
  width: 100%;
  padding: 1rem;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-pay:hover:not(:disabled) {
  background: #229954;
}

.btn-pay:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee;
  color: #c33;
  border-radius: 8px;
  text-align: center;
}

@media (max-width: 768px) {
  .member-plans-container {
    padding: 1rem;
  }
  
  .plans-grid {
    grid-template-columns: 1fr;
  }
  
  .payment-methods {
    flex-direction: column;
  }
  
  .payment-method {
    flex-direction: row;
    justify-content: flex-start;
  }
}
</style>