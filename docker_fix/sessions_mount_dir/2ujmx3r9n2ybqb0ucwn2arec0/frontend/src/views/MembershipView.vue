<template>
  <div class="membership-view">
    <el-card class="membership-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>会员状态</span>
          <el-button type="primary" size="small" @click="refreshMembership" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <div v-if="membershipInfo">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="当前会员等级">
            <el-tag :type="getMembershipTagType(membershipInfo.level)">
              {{ getMembershipLevelText(membershipInfo.level) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="到期时间">
            <span :class="{ 'text-danger': isExpiringSoon(membershipInfo.expiresAt) }">
              {{ formatDate(membershipInfo.expiresAt) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="剩余天数" span="2">
            <el-progress 
              :percentage="getRemainingDaysPercentage(membershipInfo.expiresAt)"
              :color="getProgressColor(membershipInfo.expiresAt)"
              :show-text="false"
            />
            <span class="days-text">{{ getRemainingDays(membershipInfo.expiresAt) }} 天</span>
          </el-descriptions-item>
        </el-descriptions>

        <div class="renewal-section" v-if="isExpiringSoon(membershipInfo.expiresAt)">
          <el-alert
            title="会员即将到期"
            type="warning"
            :closable="false"
            show-icon
          >
            <template #default>
              <p>您的会员将在 {{ getRemainingDays(membershipInfo.expiresAt) }} 天后到期，请及时续费以享受会员权益。</p>
            </template>
          </el-alert>
        </div>

        <div class="plans-section">
          <h3>选择续费套餐</h3>
          <el-row :gutter="20">
            <el-col :span="8" v-for="plan in availablePlans" :key="plan.id">
              <el-card 
                class="plan-card" 
                :class="{ 'selected': selectedPlan?.id === plan.id }"
                @click="selectPlan(plan)"
              >
                <div class="plan-header">
                  <h4>{{ plan.name }}</h4>
                  <div class="price">¥{{ plan.price }}</div>
                  <div class="duration">{{ plan.duration }}天</div>
                </div>
                <ul class="plan-features">
                  <li v-for="feature in plan.features" :key="feature">
                    <el-icon><Check /></el-icon>
                    {{ feature }}
                  </li>
                </ul>
              </el-card>
            </el-col>
          </el-row>

          <div class="payment-section" v-if="selectedPlan">
            <h4>支付方式</h4>
            <el-radio-group v-model="paymentMethod">
              <el-radio label="wechat">
                <el-icon><WechatPay /></el-icon>
                微信支付
              </el-radio>
              <el-radio label="alipay">
                <el-icon><AlipaySquareFill /></el-icon>
                支付宝
              </el-radio>
            </el-radio-group>

            <div class="action-buttons">
              <el-button 
                type="primary" 
                size="large" 
                @click="processPayment"
                :loading="paymentProcessing"
                :disabled="!paymentMethod"
              >
                立即支付 ¥{{ selectedPlan.price }}
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!loading" class="no-membership">
        <el-empty description="您还不是会员">
          <el-button type="primary" @click="showPlans">立即开通会员</el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 支付二维码对话框 -->
    <el-dialog
      v-model="paymentDialogVisible"
      title="扫码支付"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="payment-qr">
        <div class="qr-code" v-loading="qrCodeLoading">
          <img v-if="paymentQrCode" :src="paymentQrCode" alt="支付二维码" />
        </div>
        <p class="payment-tip">请使用{{ paymentMethod === 'wechat' ? '微信' : '支付宝' }}扫描二维码完成支付</p>
        <el-button @click="checkPaymentStatus" :loading="checkingPayment">
          检查支付状态
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, 
  Check, 
  WechatPay, 
  AlipaySquareFill 
} from '@element-plus/icons-vue'
import api from '../utils/api'
import { usePlanStore } from '../stores/plan'

const planStore = usePlanStore()
const loading = ref(false)
const refreshing = ref(false)
const membershipInfo = ref(null)
const availablePlans = ref([])
const selectedPlan = ref(null)
const paymentMethod = ref('')
const paymentProcessing = ref(false)
const paymentDialogVisible = ref(false)
const paymentQrCode = ref('')
const qrCodeLoading = ref(false)
const checkingPayment = ref(false)
const paymentTimer = ref(null)

// 获取会员信息
const fetchMembershipInfo = async () => {
  try {
    loading.value = true
    const response = await api.get('/membership/status')
    membershipInfo.value = response.data
  } catch (error) {
    console.error('获取会员信息失败:', error)
    if (error.response?.status !== 404) {
      ElMessage.error('获取会员信息失败')
    }
  } finally {
    loading.value = false
  }
}

// 刷新会员信息
const refreshMembership = async () => {
  refreshing.value = true
  try {
    await fetchMembershipInfo()
    ElMessage.success('会员信息已更新')
  } catch (error) {
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

// 获取可用套餐
const fetchAvailablePlans = async () => {
  try {
    await planStore.fetchPlans()
    availablePlans.value = planStore.plans
  } catch (error) {
    console.error('获取套餐列表失败:', error)
    ElMessage.error('获取套餐列表失败')
  }
}

// 选择套餐
const selectPlan = (plan) => {
  selectedPlan.value = plan
}

// 处理支付
const processPayment = async () => {
  if (!selectedPlan.value || !paymentMethod.value) {
    ElMessage.warning('请选择套餐和支付方式')
    return
  }

  try {
    paymentProcessing.value = true
    const response = await api.post('/payment/create', {
      planId: selectedPlan.value.id,
      method: paymentMethod.value
    })

    if (response.data.qrCode) {
      paymentQrCode.value = response.data.qrCode
      paymentDialogVisible.value = true
      startPaymentPolling(response.data.paymentId)
    }
  } catch (error) {
    console.error('创建支付订单失败:', error)
    ElMessage.error('创建支付订单失败')
  } finally {
    paymentProcessing.value = false
  }
}

// 开始轮询支付状态
const startPaymentPolling = (paymentId) => {
  paymentTimer.value = setInterval(() => {
    checkPaymentStatus(paymentId)
  }, 3000)
}

// 检查支付状态
const checkPaymentStatus = async (paymentId) => {
  try {
    checkingPayment.value = true
    const id = paymentId || (paymentQrCode.value ? paymentQrCode.value.split('/').pop() : null)
    if (!id) return

    const response = await api.get(`/payment/status/${id}`)
    
    if (response.data.status === 'success') {
      clearInterval(paymentTimer.value)
      paymentDialogVisible.value = false
      ElMessage.success('支付成功！会员已续费')
      await fetchMembershipInfo()
      selectedPlan.value = null
      paymentMethod.value = ''
    } else if (response.data.status === 'failed') {
      clearInterval(paymentTimer.value)
      paymentDialogVisible.value = false
      ElMessage.error('支付失败，请重试')
    }
  } catch (error) {
    console.error('检查支付状态失败:', error)
  } finally {
    checkingPayment.value = false
  }
}

// 显示套餐
const showPlans = () => {
  fetchAvailablePlans()
}

// 获取会员等级标签类型
const getMembershipTagType = (level) => {
  const types = {
    'basic': 'info',
    'premium': 'warning',
    'vip': 'danger'
  }
  return types[level] || 'info'
}

// 获取会员等级文本
const getMembershipLevelText = (level) => {
  const texts = {
    'basic': '基础会员',
    'premium': '高级会员',
    'vip': 'VIP会员'
  }
  return texts[level] || '普通会员'
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 检查是否即将到期
const isExpiringSoon = (expiresAt) => {
  if (!expiresAt) return false
  const now = new Date()
  const expiry = new Date(expiresAt)
  const daysLeft = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24))
  return daysLeft <= 7
}

// 获取剩余天数
const getRemainingDays = (expiresAt) => {
  if (!expiresAt) return 0
  const now = new Date()
  const expiry = new Date(expiresAt)
  return Math.max(0, Math.ceil((expiry - now) / (1000 * 60 * 60 * 24)))
}

// 获取剩余天数百分比
const getRemainingDaysPercentage = (expiresAt) => {
  if (!expiresAt) return 0
  const now = new Date()
  const expiry = new Date(expiresAt)
  const totalDays = 365 // 假设会员期为一年
  const remainingDays = Math.max(0, Math.ceil((expiry - now) / (1000 * 60 * 60 * 24)))
  return Math.min(100, (remainingDays / totalDays) * 100)
}

// 获取进度条颜色
const getProgressColor = (expiresAt) => {
  const daysLeft = getRemainingDays(expiresAt)
  if (daysLeft <= 7) return '#f56c6c'
  if (daysLeft <= 30) return '#e6a23c'
  return '#67c23a'
}

// 组件挂载时获取数据
onMounted(async () => {
  await fetchMembershipInfo()
  await fetchAvailablePlans()
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (paymentTimer.value) {
    clearInterval(paymentTimer.value)
  }
})
</script>

<style scoped>
.membership-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.membership-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-danger {
  color: #f56c6c;
  font-weight: bold;
}

.days-text {
  margin-left: 10px;
  font-size: 14px;
  color: #606266;
}

.renewal-section {
  margin-top: 20px;
}

.plans-section {
  margin-top: 30px;
}

.plans-section h3 {
  margin-bottom: 20px;
  color: #303133;
}

.plan-card {
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
}

.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.plan-card.selected {
  border: 2px solid #409eff;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.3);
}

.plan-header {
  text-align: center;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.plan-header h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.price {
  font-size: 24px;
  font-weight: bold;
  color: #f56c6c;
  margin-bottom: 5px;
}

.duration {
  color: #909399;
  font-size: 14px;
}

.plan-features {
  list-style: none;
  padding: 15px 0 0 0;
  margin: 0;
}

.plan-features li {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: #606266;
  font-size: 14px;
}

.plan-features .el-icon {
  margin-right: 8px;
  color: #67c23a;
}

.payment-section {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.payment-section h4 {
  margin-bottom: 15px;
  color: #303133;
}

.action-buttons {
  margin-top: 20px;
  text-align: center;
}

.payment-qr {
  text-align: center;
}

.qr-code {
  width: 200px;
  height: 200px;
  margin: 0 auto 20px;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-code img {
  max-width: 100%;
  max-height: 100%;
}

.payment-tip {
  color: #606266;
  margin-bottom: 20px;
}

.no-membership {
  padding: 40px 0;
}
</style>