<template>
  <div class="renewal-view">
    <div class="container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1>{{ $t('renewal.title') }}</h1>
        <p class="subtitle">{{ $t('renewal.subtitle') }}</p>
      </div>

      <!-- 会员状态卡片 -->
      <div class="status-card" v-if="membershipStatus">
        <div class="status-header">
          <div class="status-badge" :class="statusClass">
            {{ $t(`membership.status.${membershipStatus.status}`) }}
          </div>
          <div class="expiry-date" v-if="membershipStatus.expires_at">
            {{ $t('membership.expiresOn') }}: {{ formatDate(membershipStatus.expires_at) }}
          </div>
        </div>
        <div class="status-details">
          <div class="current-plan">
            <span class="label">{{ $t('membership.currentPlan') }}:</span>
            <span class="value">{{ membershipStatus.plan_name || $t('membership.noPlan') }}</span>
          </div>
          <div class="remaining-days" v-if="membershipStatus.remaining_days !== null">
            <span class="label">{{ $t('membership.remainingDays') }}:</span>
            <span class="value">{{ membershipStatus.remaining_days }} {{ $t('common.days') }}</span>
          </div>
        </div>
      </div>

      <!-- 套餐列表 -->
      <div class="plans-section">
        <h2>{{ $t('renewal.selectPlan') }}</h2>
        <div class="plans-grid" v-if="plans.length > 0">
          <div 
            v-for="plan in plans" 
            :key="plan.id"
            class="plan-card"
            :class="{ 
              'selected': selectedPlanId === plan.id,
              'current': membershipStatus?.plan_id === plan.id
            }"
            @click="selectPlan(plan.id)"
          >
            <div class="plan-header">
              <h3>{{ plan.name }}</h3>
              <div class="price">
                <span class="currency">{{ plan.currency }}</span>
                <span class="amount">{{ plan.price }}</span>
                <span class="period">/{{ $t(`billing.${plan.billing_cycle}`) }}</span>
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
            <div class="plan-footer">
              <button 
                class="btn btn-primary"
                :disabled="selectedPlanId !== plan.id || isProcessing"
                @click.stop="handleRenewal(plan.id)"
              >
                <span v-if="isProcessing && selectedPlanId === plan.id">
                  <i class="icon-spinner"></i>
                  {{ $t('common.processing') }}
                </span>
                <span v-else>
                  {{ membershipStatus?.plan_id === plan.id ? $t('renewal.renew') : $t('renewal.upgrade') }}
                </span>
              </button>
            </div>
          </div>
        </div>
        <div v-else-if="!isLoading" class="no-plans">
          <p>{{ $t('renewal.noPlansAvailable') }}</p>
        </div>
      </div>

      <!-- 续费历史 -->
      <div class="history-section" v-if="renewalHistory.length > 0">
        <h2>{{ $t('renewal.history') }}</h2>
        <div class="history-list">
          <div v-for="item in renewalHistory" :key="item.id" class="history-item">
            <div class="history-info">
              <div class="plan-name">{{ item.plan_name }}</div>
              <div class="date">{{ formatDate(item.created_at) }}</div>
            </div>
            <div class="history-amount">
              {{ item.currency }} {{ item.amount }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiMethods } from '@/services/api'
import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notification'

const { t } = useI18n()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

// 响应式数据
const membershipStatus = ref(null)
const plans = ref([])
const selectedPlanId = ref(null)
const renewalHistory = ref([])
const isLoading = ref(true)
const isProcessing = ref(false)

// 计算属性
const statusClass = computed(() => {
  if (!membershipStatus.value) return ''
  return `status-${membershipStatus.value.status.toLowerCase()}`
})

// 方法
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

const selectPlan = (planId) => {
  selectedPlanId.value = planId
}

const loadMembershipStatus = async () => {
  try {
    const response = await apiMethods.membership.getStatus()
    membershipStatus.value = response
  } catch (error) {
    console.error('Failed to load membership status:', error)
  }
}

const loadPlans = async () => {
  try {
    const response = await apiMethods.membership.getPlans()
    plans.value = response
  } catch (error) {
    console.error('Failed to load plans:', error)
  }
}

const loadRenewalHistory = async () => {
  try {
    const response = await apiMethods.membership.getHistory()
    renewalHistory.value = response
  } catch (error) {
    console.error('Failed to load renewal history:', error)
  }
}

const handleRenewal = async (planId) => {
  if (!planId) return
  
  isProcessing.value = true
  try {
    // 创建支付意图
    const paymentIntent = await apiMethods.payment.createPaymentIntent(planId)
    
    // 这里应该集成Stripe或其他支付SDK
    // 为了演示，我们直接确认支付
    await apiMethods.payment.confirmPayment(paymentIntent.id)
    
    // 续费会员
    await apiMethods.membership.renew(planId)
    
    notificationStore.showSuccess(t('renewal.success'))
    
    // 重新加载状态
    await loadMembershipStatus()
    await loadRenewalHistory()
  } catch (error) {
    console.error('Renewal failed:', error)
  } finally {
    isProcessing.value = false
  }
}

// 生命周期
onMounted(async () => {
  isLoading.value = true
  try {
    await Promise.all([
      loadMembershipStatus(),
      loadPlans(),
      loadRenewalHistory()
    ])
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.renewal-view {
  padding: 2rem 0;
  min-height: 100vh;
  background-color: var(--color-background);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
}

.page-header h1 {
  font-size: 2.5rem;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
}

.status-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.9rem;
}

.status-active {
  background-color: var(--color-success-light);
  color: var(--color-success);
}

.status-expired {
  background-color: var(--color-danger-light);
  color: var(--color-danger);
}

.status-trialing {
  background-color: var(--color-warning-light);
  color: var(--color-warning);
}

.expiry-date {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.status-details {
  display: flex;
  gap: 2rem;
}

.status-details .label {
  color: var(--color-text-secondary);
  margin-right: 0.5rem;
}

.status-details .value {
  font-weight: 600;
}

.plans-section {
  margin-bottom: 3rem;
}

.plans-section h2 {
  margin-bottom: 1.5rem;
  color: var(--color-text-primary);
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.plan-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.plan-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.plan-card.selected {
  border-color: var(--color-primary);
}

.plan-card.current {
  border-color: var(--color-success);
}

.plan-header {
  margin-bottom: 1.5rem;
}

.plan-header h3 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.price {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.currency {
  font-size: 1rem;
  color: var(--color-text-secondary);
}

.amount {
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-primary);
}

.period {
  color: var(--color-text-secondary);
}

.plan-features ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.plan-features li {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
  color: var(--color-text-primary);
}

.icon-check {
  color: var(--color-success);
  margin-right: 0.5rem;
}

.plan-footer {
  margin-top: 1.5rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
}

.btn-primary {
  background-color: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.no-plans {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-secondary);
}

.history-section h2 {
  margin-bottom: 1.5rem;
  color: var(--color-text-primary);
}

.history-list {
  background: white;
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.history-item:last-child {
  border-bottom: none;
}

.plan-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.date {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.history-amount {
  font-weight: 600;
  color: var(--color-primary);
}

.icon-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .plans-grid {
    grid-template-columns: 1fr;
  }
  
  .status-details {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>