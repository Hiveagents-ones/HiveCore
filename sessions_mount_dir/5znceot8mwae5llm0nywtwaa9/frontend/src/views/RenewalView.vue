<template>
  <div class="renewal-view">
    <div class="container">
      <h1>{{ $t('renewal.title') }}</h1>
      
      <!-- 会员状态卡片 -->
      <div class="status-card">
        <h2>{{ $t('renewal.currentStatus') }}</h2>
        <div class="status-info">
          <div class="status-item">
            <span class="label">{{ $t('renewal.membershipType') }}:</span>
            <span class="value">{{ currentMembership.type || $t('renewal.notMember') }}</span>
          </div>
          <div class="status-item">
            <span class="label">{{ $t('renewal.expiryDate') }}:</span>
            <span class="value">{{ formatDate(currentMembership.expiryDate) || $t('renewal.notApplicable') }}</span>
          </div>
          <div class="status-item">
            <span class="label">{{ $t('renewal.daysRemaining') }}:</span>
            <span class="value">{{ daysRemaining || $t('renewal.notApplicable') }}</span>
          </div>
        </div>
      </div>

      <!-- 套餐选择 -->
      <div class="plans-section">
        <h2>{{ $t('renewal.selectPlan') }}</h2>
        <div class="plans-grid">
          <div 
            v-for="plan in membershipPlans" 
            :key="plan.id"
            class="plan-card"
            :class="{ selected: selectedPlan?.id === plan.id }"
            @click="selectPlan(plan)"
          >
            <h3>{{ plan.name }}</h3>
            <div class="price">{{ formatCurrency(plan.price) }}</div>
            <div class="duration">{{ plan.duration }} {{ $t('renewal.days') }}</div>
            <ul class="features">
              <li v-for="feature in plan.features" :key="feature">
                {{ feature }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 支付方式 -->
      <div class="payment-section" v-if="selectedPlan">
        <h2>{{ $t('renewal.paymentMethod') }}</h2>
        <div class="payment-methods">
          <div 
            v-for="method in paymentMethods" 
            :key="method.id"
            class="payment-method"
            :class="{ selected: selectedPaymentMethod?.id === method.id }"
            @click="selectPaymentMethod(method)"
          >
            <img :src="method.icon" :alt="method.name" />
            <span>{{ method.name }}</span>
          </div>
        </div>
      </div>

      <!-- 确认按钮 -->
      <div class="actions" v-if="selectedPlan && selectedPaymentMethod">
        <button 
          class="btn-primary" 
          @click="processPayment"
          :disabled="processing"
        >
          {{ processing ? $t('renewal.processing') : $t('renewal.confirmRenewal') }}
        </button>
      </div>

      <!-- 线下支付提示 -->
      <div class="offline-notice" v-if="selectedPaymentMethod?.type === 'offline'">
        <p>{{ $t('renewal.offlinePaymentNotice') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMembershipStore } from '@/stores/membership'
import { usePaymentStore } from '@/stores/payment'

const { t } = useI18n()
const membershipStore = useMembershipStore()
const paymentStore = usePaymentStore()

const selectedPlan = ref(null)
const selectedPaymentMethod = ref(null)
const processing = ref(false)

// 当前会员状态
const currentMembership = computed(() => membershipStore.currentMembership)

// 剩余天数
const daysRemaining = computed(() => {
  if (!currentMembership.value?.expiryDate) return null
  const expiry = new Date(currentMembership.value.expiryDate)
  const now = new Date()
  const diff = Math.floor((expiry - now) / (1000 * 60 * 60 * 24))
  return diff > 0 ? diff : 0
})

// 可选套餐
const membershipPlans = ref([
  {
    id: 1,
    name: t('renewal.plans.basic.name'),
    price: 99,
    duration: 30,
    features: [
      t('renewal.plans.basic.feature1'),
      t('renewal.plans.basic.feature2'),
      t('renewal.plans.basic.feature3')
    ]
  },
  {
    id: 2,
    name: t('renewal.plans.premium.name'),
    price: 199,
    duration: 90,
    features: [
      t('renewal.plans.premium.feature1'),
      t('renewal.plans.premium.feature2'),
      t('renewal.plans.premium.feature3'),
      t('renewal.plans.premium.feature4')
    ]
  },
  {
    id: 3,
    name: t('renewal.plans.vip.name'),
    price: 399,
    duration: 365,
    features: [
      t('renewal.plans.vip.feature1'),
      t('renewal.plans.vip.feature2'),
      t('renewal.plans.vip.feature3'),
      t('renewal.plans.vip.feature4'),
      t('renewal.plans.vip.feature5')
    ]
  }
])

// 支付方式
const paymentMethods = ref([
  {
    id: 1,
    name: 'WeChat Pay',
    type: 'online',
    icon: '/icons/wechat-pay.svg'
  },
  {
    id: 2,
    name: 'Alipay',
    type: 'online',
    icon: '/icons/alipay.svg'
  },
  {
    id: 3,
    name: t('renewal.offlinePayment'),
    type: 'offline',
    icon: '/icons/bank-transfer.svg'
  }
])

// 选择套餐
const selectPlan = (plan) => {
  selectedPlan.value = plan
}

// 选择支付方式
const selectPaymentMethod = (method) => {
  selectedPaymentMethod.value = method
}

// 处理支付
const processPayment = async () => {
  if (!selectedPlan.value || !selectedPaymentMethod.value) return

  processing.value = true
  try {
    const paymentData = {
      planId: selectedPlan.value.id,
      paymentMethodId: selectedPaymentMethod.value.id,
      amount: selectedPlan.value.price
    }

    if (selectedPaymentMethod.value.type === 'online') {
      // 在线支付
      const result = await paymentStore.processOnlinePayment(paymentData)
      if (result.success) {
        // 跳转到支付页面
        window.location.href = result.paymentUrl
      } else {
        alert(t('renewal.paymentFailed'))
      }
    } else {
      // 线下支付
      const result = await paymentStore.processOfflinePayment(paymentData)
      if (result.success) {
        alert(t('renewal.offlinePaymentSubmitted'))
        // 刷新会员状态
        await membershipStore.fetchMembershipStatus()
      } else {
        alert(t('renewal.paymentFailed'))
      }
    }
  } catch (error) {
    console.error('Payment error:', error)
    alert(t('renewal.paymentError'))
  } finally {
    processing.value = false
  }
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return null
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

// 格式化货币
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  }).format(amount)
}

// 初始化
onMounted(async () => {
  await membershipStore.fetchMembershipStatus()
})
</script>

<style scoped>
.renewal-view {
  padding: 2rem 0;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
}

h2 {
  margin-bottom: 1.5rem;
  color: #555;
}

.status-card {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.status-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}

.status-item .label {
  font-weight: 600;
  color: #666;
}

.status-item .value {
  color: #333;
}

.plans-section {
  margin-bottom: 2rem;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.plan-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.plan-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.plan-card.selected {
  border-color: #007bff;
  background-color: #f8f9ff;
}

.plan-card h3 {
  margin-bottom: 1rem;
  color: #333;
}

.price {
  font-size: 2rem;
  font-weight: bold;
  color: #007bff;
  margin-bottom: 0.5rem;
}

.duration {
  color: #666;
  margin-bottom: 1rem;
}

.features {
  list-style: none;
  padding: 0;
}

.features li {
  padding: 0.25rem 0;
  color: #555;
}

.features li::before {
  content: '✓';
  color: #28a745;
  margin-right: 0.5rem;
}

.payment-section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.payment-methods {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.payment-method {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.payment-method:hover {
  border-color: #007bff;
}

.payment-method.selected {
  border-color: #007bff;
  background-color: #f8f9ff;
}

.payment-method img {
  width: 48px;
  height: 48px;
  margin-bottom: 0.5rem;
}

.payment-method span {
  font-size: 0.9rem;
  color: #555;
}

.actions {
  text-align: center;
  margin-bottom: 2rem;
}

.btn-primary {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 1rem 2rem;
  border-radius: 4px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-primary:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.offline-notice {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 2rem;
  text-align: center;
}

.offline-notice p {
  color: #856404;
  margin: 0;
}

@media (max-width: 768px) {
  .plans-grid {
    grid-template-columns: 1fr;
  }
  
  .payment-methods {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
