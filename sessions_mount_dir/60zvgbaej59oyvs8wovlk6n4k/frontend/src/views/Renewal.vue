<template>
  <div class="renewal-container">
    <el-card class="renewal-card">
      <template #header>
        <div class="card-header">
          <h2>会员续费</h2>
          <el-tag v-if="membershipInfo" :type="membershipInfo.status === 'active' ? 'success' : 'warning'">
            {{ membershipInfo.status === 'active' ? '有效会员' : '会员已过期' }}
          </el-tag>
        </div>
      </template>

      <!-- 会员信息 -->
      <div v-if="membershipInfo" class="membership-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="当前套餐">
            {{ membershipInfo.plan_name }}
          </el-descriptions-item>
          <el-descriptions-item label="到期时间">
            {{ formatDate(membershipInfo.expires_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="剩余天数">
            <span :class="{ 'text-danger': membershipInfo.days_left <= 7 }">
              {{ membershipInfo.days_left }} 天
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="自动续费">
            <el-switch
              v-model="membershipInfo.auto_renew"
              @change="handleAutoRenewChange"
            />
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 套餐选择 -->
      <div class="plan-selection">
        <h3>选择续费套餐</h3>
        <el-row :gutter="20">
          <el-col
            v-for="plan in plans"
            :key="plan.id"
            :xs="24"
            :sm="12"
            :md="8"
          >
            <el-card
              :class="[
                'plan-card',
                { 'selected': selectedPlan?.id === plan.id },
                { 'popular': plan.is_popular }
              ]"
              @click="selectPlan(plan)"
            >
              <template #header>
                <div class="plan-header">
                  <span class="plan-name">{{ plan.name }}</span>
                  <el-tag v-if="plan.is_popular" type="danger" size="small">
                    热门
                  </el-tag>
                </div>
              </template>
              <div class="plan-content">
                <div class="plan-price">
                  <span class="currency">¥</span>
                  <span class="amount">{{ plan.price }}</span>
                  <span class="period">/{{ plan.duration }}{{ plan.duration_unit }}</span>
                </div>
                <ul class="plan-features">
                  <li v-for="feature in plan.features" :key="feature">
                    <el-icon><Check /></el-icon>
                    {{ feature }}
                  </li>
                </ul>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 支付方式 -->
      <div v-if="selectedPlan" class="payment-method">
        <h3>选择支付方式</h3>
        <el-alert
          v-if="!isSecureContext"
          title="支付功能需要HTTPS环境"
          type="warning"
          :closable="false"
          show-icon
        />
        <el-radio-group v-model="selectedPaymentMethod">
          <el-radio label="alipay" :disabled="!isSecureContext">
            <el-icon><Wallet /></el-icon>
            支付宝
          </el-radio>
          <el-radio label="wechat" :disabled="!isSecureContext">
            <el-icon><Wallet /></el-icon>
            微信支付
          </el-radio>
          <el-radio label="stripe" :disabled="!isSecureContext">
            <el-icon><CreditCard /></el-icon>
            信用卡
          </el-radio>
        </el-radio-group>
      </div>

      <!-- 支付按钮 -->
      <div v-if="selectedPlan && selectedPaymentMethod" class="payment-actions">
        <el-button
          type="primary"
          size="large"
          :loading="paymentLoading"
          :disabled="!isSecureContext"
          @click="handlePayment"
        >
          立即支付 ¥{{ selectedPlan.price }}
        </el-button>
        <p v-if="!isSecureContext" class="security-notice">
          <el-icon><Warning /></el-icon>
          请在HTTPS环境下使用支付功能
        </p>
      </div>
    </el-card>

    <!-- 支付历史 -->
    <el-card class="history-card">
      <template #header>
        <h3>支付历史</h3>
      </template>
      <el-table
        :data="paymentHistory"
        v-loading="historyLoading"
        style="width: 100%"
      >
        <el-table-column prop="created_at" label="支付时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="plan_name" label="套餐" width="120" />
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="scope">
            ¥{{ scope.row.amount }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="120" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button
              v-if="scope.row.status === 'pending'"
              type="text"
              @click="handleRetryPayment(scope.row)"
            >
              重新支付
            </el-button>
            <el-button
              type="text"
              @click="viewPaymentDetail(scope.row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Wallet, CreditCard } from '@element-plus/icons-vue'
import { api } from '@/api/index.js'
import { usePaymentStore } from '@/stores/payment.js'

const paymentStore = usePaymentStore()

// 检查是否为安全上下文（HTTPS）
const isSecureContext = computed(() => window.isSecureContext || location.protocol === 'https:')

// 检查HTTPS
const checkHTTPS = () => {
  if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
    ElMessage.warning('为了支付安全，请使用HTTPS协议访问')
    return false
  }
  return true
}

// 组件挂载时检查HTTPS
onMounted(() => {
  if (!checkHTTPS()) {
    // 可以在这里添加重定向逻辑或禁用支付功能
  }
})

// 响应式数据
const membershipInfo = ref(null)
const plans = ref([])
const selectedPlan = ref(null)
const selectedPaymentMethod = ref('alipay')
const paymentHistory = ref([])
const paymentLoading = ref(false)
const historyLoading = ref(false)

// 获取会员信息
const fetchMembershipInfo = async () => {
  try {
    const response = await api.get('/membership/info')
    membershipInfo.value = response.data
  } catch (error) {
    console.error('Failed to fetch membership info:', error)
  }
}

// 获取套餐列表
const fetchPlans = async () => {
  try {
    const response = await api.get('/membership/plans')
    plans.value = response.data
  } catch (error) {
    console.error('Failed to fetch plans:', error)
  }
}

// 获取支付历史
const fetchPaymentHistory = async () => {
  historyLoading.value = true
  try {
    const response = await api.payment.getHistory()
    paymentHistory.value = response.data.items || []
  } catch (error) {
    console.error('Failed to fetch payment history:', error)
  } finally {
    historyLoading.value = false
  }
}

// 选择套餐
const selectPlan = (plan) => {
  selectedPlan.value = plan
}

// 处理自动续费变更
const handleAutoRenewChange = async (value) => {
  try {
    await api.put('/membership/auto-renew', { auto_renew: value })
    ElMessage.success('自动续费设置已更新')
  } catch (error) {
    membershipInfo.value.auto_renew = !value
    ElMessage.error('更新自动续费设置失败')
  }
}

// 处理支付
const handlePayment = async () => {
  if (!selectedPlan.value || !selectedPaymentMethod.value) {
    ElMessage.warning('请选择套餐和支付方式')
    return
  }

  // 再次检查HTTPS
  if (!checkHTTPS()) {
    return
  }

  paymentLoading.value = true
  try {
    const paymentData = {
      plan_id: selectedPlan.value.id,
      payment_method: selectedPaymentMethod.value
    }

    const response = await api.payment.initiate(paymentData)
    const { payment_intent_id, client_secret } = response.data

    // 根据支付方式处理不同的支付流程
    if (selectedPaymentMethod.value === 'stripe') {
      // 使用Stripe处理支付
      const stripe = window.Stripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY)
      const { error } = await stripe.confirmCardPayment(client_secret)
      
      if (error) {
        throw new Error(error.message)
      }
      
      await confirmPayment(payment_intent_id)
    } else {
      // 其他支付方式（支付宝、微信）跳转到支付页面
      window.location.href = response.data.payment_url
    }
  } catch (error) {
    console.error('Payment failed:', error)
    ElMessage.error(error.message || '支付失败，请重试')
  } finally {
    paymentLoading.value = false
  }
}

// 确认支付
const confirmPayment = async (paymentIntentId) => {
  try {
    await api.payment.confirm(paymentIntentId)
    ElMessage.success('支付成功')
    await fetchMembershipInfo()
    await fetchPaymentHistory()
  } catch (error) {
    console.error('Failed to confirm payment:', error)
    ElMessage.error('支付确认失败')
  }
}

// 重试支付
const handleRetryPayment = async (payment) => {
  // 检查HTTPS
  if (!checkHTTPS()) {
    return
  }

  try {
    const response = await api.payment.initiate({
      payment_id: payment.id
    })
    window.location.href = response.data.payment_url
  } catch (error) {
    console.error('Failed to retry payment:', error)
    ElMessage.error('重试支付失败')
  }
}

// 查看支付详情
const viewPaymentDetail = (payment) => {
  ElMessageBox.alert(
    `<div>
      <p><strong>支付ID:</strong> ${payment.id}</p>
      <p><strong>套餐:</strong> ${payment.plan_name}</p>
      <p><strong>金额:</strong> ¥${payment.amount}</p>
      <p><strong>状态:</strong> ${getStatusText(payment.status)}</p>
      <p><strong>支付方式:</strong> ${payment.payment_method}</p>
      <p><strong>创建时间:</strong> ${formatDate(payment.created_at)}</p>
    </div>`,
    '支付详情',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '确定'
    }
  )
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    'pending': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'cancelled': 'info'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'pending': '待支付',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消'
  }
  return statusMap[status] || status
}

// 组件挂载时获取数据
onMounted(async () => {
  await Promise.all([
    fetchMembershipInfo(),
    fetchPlans(),
    fetchPaymentHistory()
  ])
})
</script>

<style scoped>
.renewal-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.renewal-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: #303133;
}

.membership-info {
  margin-bottom: 30px;
}

.text-danger {
  color: #f56c6c;
}

.plan-selection {
  margin-bottom: 30px;
}

.plan-selection h3 {
  margin-bottom: 20px;
  color: #303133;
}

.plan-card {
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
}

/* 禁用非HTTPS环境下的支付功能 */
.security-notice {
  margin-top: 10px;
  color: #e6a23c;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.security-notice .el-icon {
  margin-right: 5px;
}


.payment-method:has(.el-radio:disabled),
.payment-actions:has(.el-button:disabled) {
  opacity: 0.6;
  pointer-events: none;
}


.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.plan-card.selected {
  border: 2px solid #409eff;
}

.plan-card.popular {
  position: relative;
}

.plan-card.popular::before {
  content: '推荐';
  position: absolute;
  top: 10px;
  right: -30px;
  background: #f56c6c;
  color: white;
  padding: 2px 30px;
  transform: rotate(45deg);
  font-size: 12px;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plan-name {
  font-weight: bold;
  font-size: 16px;
}

.plan-content {
  text-align: center;
}

.plan-price {
  margin-bottom: 20px;
}

.currency {
  font-size: 20px;
  color: #909399;
}

.amount {
  font-size: 36px;
  font-weight: bold;
  color: #303133;
}

.period {
  color: #909399;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
}

.plan-features li {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  color: #606266;
}

.plan-features .el-icon {
  margin-right: 8px;
  color: #67c23a;
}

.payment-method {
  margin-bottom: 30px;
}

.payment-method h3 {
  margin-bottom: 20px;
  color: #303133;
}

.payment-actions {
  text-align: center;
}

.history-card {
  margin-top: 20px;
}

.history-card h3 {
  margin: 0;
  color: #303133;
}
</style>