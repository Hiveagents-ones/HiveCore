<template>
  <div class="renewal-view">
    <div class="container">
      <h1>{{ $t('renewal.title') }}</h1>
      
      <!-- 会员信息卡片 -->
      <div class="member-info-card" v-if="memberInfo">
        <h2>{{ $t('renewal.currentMembership') }}</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">{{ $t('renewal.memberType') }}:</span>
            <span class="value">{{ memberInfo.type }}</span>
          </div>
          <div class="info-item">
            <span class="label">{{ $t('renewal.expiryDate') }}:</span>
            <span class="value">{{ formatDate(memberInfo.expiryDate) }}</span>
          </div>
          <div class="info-item">
            <span class="label">{{ $t('renewal.daysRemaining') }}:</span>
            <span class="value" :class="{ 'warning': daysRemaining <= 30 }">
              {{ daysRemaining }} {{ $t('renewal.days') }}
            </span>
          </div>
        </div>
      </div>

      <!-- 套餐选择 -->
      <div class="packages-section">
        <h2>{{ $t('renewal.selectPackage') }}</h2>
        <div class="packages-grid" v-if="packages.length">
          <div 
            v-for="pkg in packages" 
            :key="pkg.id"
            class="package-card"
            :class="{ 'selected': selectedPackage?.id === pkg.id }"
            @click="selectPackage(pkg)"
          >
            <div class="package-header">
              <h3>{{ pkg.name }}</h3>
              <div class="price">
                <span class="currency">{{ pkg.currency }}</span>
                <span class="amount">{{ pkg.price }}</span>
                <span class="period">/{{ pkg.period }}</span>
              </div>
            </div>
            <ul class="benefits">
              <li v-for="benefit in pkg.benefits" :key="benefit">
                <i class="icon-check"></i>
                {{ benefit }}
              </li>
            </ul>
            <div class="discount-badge" v-if="pkg.discount">
              {{ pkg.discount }}% OFF
            </div>
          </div>
        </div>
        <div v-else-if="!loading" class="no-packages">
          {{ $t('renewal.noPackagesAvailable') }}
        </div>
      </div>

      <!-- 支付方式 -->
      <div class="payment-section" v-if="selectedPackage">
        <h2>{{ $t('renewal.paymentMethod') }}</h2>
        <div class="payment-methods">
          <div 
            v-for="method in paymentMethods" 
            :key="method.id"
            class="payment-method"
            :class="{ 'selected': selectedPaymentMethod === method.id }"
            @click="selectPaymentMethod(method.id)"
          >
            <img :src="method.icon" :alt="method.name" class="method-icon">
            <span>{{ method.name }}</span>
          </div>
        </div>
      </div>

      <!-- 订单摘要 -->
      <div class="order-summary" v-if="selectedPackage && selectedPaymentMethod">
        <h2>{{ $t('renewal.orderSummary') }}</h2>
        <div class="summary-item">
          <span>{{ $t('renewal.package') }}:</span>
          <span>{{ selectedPackage.name }}</span>
        </div>
        <div class="summary-item">
          <span>{{ $t('renewal.duration') }}:</span>
          <span>{{ selectedPackage.duration }} {{ $t('renewal.days') }}</span>
        </div>
        <div class="summary-item discount" v-if="selectedPackage.discount">
          <span>{{ $t('renewal.discount') }}:</span>
          <span>-{{ selectedPackage.discount }}%</span>
        </div>
        <div class="summary-item total">
          <span>{{ $t('renewal.total') }}:</span>
          <span>{{ selectedPackage.currency }} {{ calculateTotal() }}</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="actions" v-if="selectedPackage && selectedPaymentMethod">
        <button 
          class="btn-primary"
          @click="processPayment"
          :disabled="processing"
        >
          <span v-if="!processing">{{ $t('renewal.payNow') }}</span>
          <span v-else>{{ $t('renewal.processing') }}...</span>
        </button>
      </div>

      <!-- 错误提示 -->
      <div class="error-message" v-if="error">
        <i class="icon-error"></i>
        {{ error }}
      </div>

      <!-- 成功提示 -->
      <div class="success-message" v-if="success">
        <i class="icon-success"></i>
        {{ success }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import { usePaymentStore } from '@/stores/payment'

const { t } = useI18n()
const router = useRouter()
const memberStore = useMemberStore()
const paymentStore = usePaymentStore()

// 响应式数据
const loading = ref(true)
const processing = ref(false)
const error = ref('')
const success = ref('')
const memberInfo = ref(null)
const packages = ref([])
const selectedPackage = ref(null)
const selectedPaymentMethod = ref('')
const paymentMethods = ref([
  { id: 'alipay', name: 'Alipay', icon: '/icons/alipay.svg' },
  { id: 'wechat', name: 'WeChat Pay', icon: '/icons/wechat.svg' },
  { id: 'card', name: 'Credit Card', icon: '/icons/card.svg' }
])

// 计算属性
const daysRemaining = computed(() => {
  if (!memberInfo.value?.expiryDate) return 0
  const expiry = new Date(memberInfo.value.expiryDate)
  const now = new Date()
  const diff = expiry - now
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)))
})

// 方法
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

const selectPackage = (pkg) => {
  selectedPackage.value = pkg
  error.value = ''
  success.value = ''
}

const selectPaymentMethod = (methodId) => {
  selectedPaymentMethod.value = methodId
  error.value = ''
  success.value = ''
}

const calculateTotal = () => {
  if (!selectedPackage.value) return 0
  const price = parseFloat(selectedPackage.value.price)
  const discount = selectedPackage.value.discount || 0
  return (price * (1 - discount / 100)).toFixed(2)
}

const processPayment = async () => {
  if (!selectedPackage.value || !selectedPaymentMethod.value) {
    error.value = t('renewal.selectPackageAndPayment')
    return
  }

  processing.value = true
  error.value = ''
  success.value = ''

  try {
    const paymentData = {
      packageId: selectedPackage.value.id,
      paymentMethod: selectedPaymentMethod.value,
      amount: calculateTotal(),
      currency: selectedPackage.value.currency
    }

    const result = await paymentStore.processPayment(paymentData)
    
    if (result.success) {
      success.value = t('renewal.paymentSuccess')
      // 刷新会员信息
      await fetchMemberInfo()
      // 3秒后跳转到会员中心
      setTimeout(() => {
        router.push('/member')
      }, 3000)
    } else {
      error.value = result.message || t('renewal.paymentFailed')
    }
  } catch (err) {
    console.error('Payment error:', err)
    error.value = t('renewal.paymentError')
  } finally {
    processing.value = false
  }
}

const fetchMemberInfo = async () => {
  try {
    memberInfo.value = await memberStore.getMemberInfo()
  } catch (err) {
    console.error('Failed to fetch member info:', err)
    error.value = t('renewal.fetchMemberError')
  }
}

const fetchPackages = async () => {
  try {
    packages.value = await paymentStore.getAvailablePackages()
  } catch (err) {
    console.error('Failed to fetch packages:', err)
    error.value = t('renewal.fetchPackagesError')
  }
}

// 生命周期
onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchMemberInfo(),
      fetchPackages()
    ])
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.renewal-view {
  padding: 2rem 0;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 2rem;
  text-align: center;
}

h2 {
  font-size: 1.5rem;
  color: #34495e;
  margin-bottom: 1.5rem;
}

.member-info-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-item .label {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.info-item .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
}

.info-item .value.warning {
  color: #e74c3c;
}

.packages-section {
  margin-bottom: 2rem;
}

.packages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.package-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.package-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
}

.package-card.selected {
  border: 2px solid #3498db;
  background: #f0f8ff;
}

.package-header {
  margin-bottom: 1.5rem;
}

.package-header h3 {
  font-size: 1.3rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.price {
  font-size: 2rem;
  font-weight: bold;
  color: #3498db;
}

.currency {
  font-size: 1.2rem;
  vertical-align: super;
}

.period {
  font-size: 1rem;
  color: #7f8c8d;
}

.benefits {
  list-style: none;
  padding: 0;
}

.benefits li {
  padding: 0.5rem 0;
  color: #34495e;
  display: flex;
  align-items: center;
}

.icon-check {
  color: #27ae60;
  margin-right: 0.5rem;
}

.discount-badge {
  position: absolute;
  top: 1rem;
  right: -2rem;
  background: #e74c3c;
  color: white;
  padding: 0.3rem 3rem;
  transform: rotate(45deg);
  font-size: 0.8rem;
  font-weight: bold;
}

.payment-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.payment-methods {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.payment-method {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.payment-method:hover {
  border-color: #3498db;
}

.payment-method.selected {
  border-color: #3498db;
  background: #f0f8ff;
}

.method-icon {
  width: 24px;
  height: 24px;
  margin-right: 0.5rem;
}

.order-summary {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  color: #34495e;
}

.summary-item.discount {
  color: #e74c3c;
}

.summary-item.total {
  font-size: 1.2rem;
  font-weight: bold;
  color: #2c3e50;
  border-top: 2px solid #e0e0e0;
  margin-top: 1rem;
  padding-top: 1rem;
}

.actions {
  text-align: center;
  margin-bottom: 2rem;
}

.btn-primary {
  background: #3498db;
  color: white;
  border: none;
  padding: 1rem 3rem;
  font-size: 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-primary:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.error-message {
  background: #fee;
  color: #e74c3c;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
}

.success-message {
  background: #efe;
  color: #27ae60;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
}

.icon-error,
.icon-success {
  margin-right: 0.5rem;
}

.no-packages {
  text-align: center;
  color: #7f8c8d;
  padding: 2rem;
}

@media (max-width: 768px) {
  .packages-grid {
    grid-template-columns: 1fr;
  }
  
  .payment-methods {
    flex-direction: column;
  }
  
  .payment-method {
    width: 100%;
  }
}
</style>