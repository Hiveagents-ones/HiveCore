<template>
  <div class="renewal-view">
    <el-card class="status-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>会员状态</span>
          <el-tag :type="isExpired ? 'danger' : 'success'">
            {{ isExpired ? '已过期' : '有效' }}
          </el-tag>
        </div>
      </template>
      
      <div class="status-content">
        <div class="current-plan">
          <h3>当前套餐</h3>
          <p v-if="currentPlan">{{ currentPlan.name }} - {{ currentPlan.price }}元/{{ currentPlan.duration }}天</p>
          <p v-else>无套餐</p>
        </div>
        
        <div class="expiry-info">
          <h3>到期时间</h3>
          <p v-if="membershipStatus?.expiryDate">
            {{ formatDate(membershipStatus.expiryDate) }}
            <span class="days-left">(剩余 {{ daysUntilExpiry }} 天)</span>
          </p>
          <p v-else>无到期时间</p>
        </div>
      </div>
    </el-card>

    <el-card class="plans-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>选择续费套餐</span>
          <el-button @click="fetchPlans" :icon="Refresh" circle />
        </div>
      </template>
      
      <div class="plans-grid">
        <div 
          v-for="plan in plans" 
          :key="plan.id"
          class="plan-item"
          :class="{ 'selected': selectedPlan?.id === plan.id }"
          @click="selectPlan(plan)"
        >
          <div class="plan-header">
            <h3>{{ plan.name }}</h3>
            <el-tag v-if="plan.featured" type="warning">推荐</el-tag>
          </div>
          
          <div class="plan-price">
            <span class="price">{{ plan.price }}</span>
            <span class="unit">元</span>
          </div>
          
          <div class="plan-duration">
            {{ plan.duration }}天
          </div>
          
          <div class="plan-features">
            <ul>
              <li v-for="feature in plan.features" :key="feature">
                <el-icon><Check /></el-icon>
                {{ feature }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </el-card>

    <el-card class="payment-card" v-if="selectedPlan">
      <template #header>
        <span>支付方式</span>
      </template>
      
      <div class="payment-methods">
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
      </div>
      
      <div class="payment-summary">
        <div class="summary-item">
          <span>套餐:</span>
          <span>{{ selectedPlan.name }}</span>
        </div>
        <div class="summary-item">
          <span>时长:</span>
          <span>{{ selectedPlan.duration }}天</span>
        </div>
        <div class="summary-item total">
          <span>应付金额:</span>
          <span class="price">{{ selectedPlan.price }}元</span>
        </div>
      </div>
      
      <div class="payment-actions">
        <el-button 
          type="primary" 
          size="large"
          :loading="processing"
          @click="handleRenewal"
        >
          立即支付
        </el-button>
      </div>
    </el-card>

    <!-- 支付弹窗 -->
    <el-dialog 
      v-model="paymentDialogVisible" 
      title="扫码支付" 
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="payment-qr">
        <div class="qr-code" v-if="paymentQrCode">
          <img :src="paymentQrCode" alt="支付二维码" />
        </div>
        <div class="payment-tips">
          <p>请使用{{ paymentMethod === 'wechat' ? '微信' : '支付宝' }}扫码支付</p>
          <p class="amount">支付金额: {{ selectedPlan?.price }}元</p>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="cancelPayment">取消支付</el-button>
        <el-button type="primary" @click="checkPaymentStatus">支付完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePlanStore } from '../stores/plan.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, 
  Check, 
  WechatPay, 
  AlipaySquareFill 
} from '@element-plus/icons-vue'

const planStore = usePlanStore()
const paymentMethod = ref('wechat')
const processing = ref(false)
const paymentDialogVisible = ref(false)
const paymentQrCode = ref('')
const paymentTimer = ref(null)

const loading = computed(() => planStore.loading)
const currentPlan = computed(() => planStore.currentPlan)
const selectedPlan = computed(() => planStore.selectedPlan)
const membershipStatus = computed(() => planStore.membershipStatus)
const plans = computed(() => planStore.plans)
const isExpired = computed(() => planStore.isExpired)
const daysUntilExpiry = computed(() => planStore.daysUntilExpiry)

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const fetchPlans = async () => {
  try {
    await planStore.fetchPlans()
  } catch (error) {
    ElMessage.error('获取套餐列表失败')
  }
}

const selectPlan = (plan) => {
  planStore.selectPlan(plan)
}

const handleRenewal = async () => {
  if (!selectedPlan.value) {
    ElMessage.warning('请选择套餐')
    return
  }

  try {
    processing.value = true
    
    // 模拟支付流程
    paymentDialogVisible.value = true
    paymentQrCode.value = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent('payment_' + Date.now())}`
    
    // 启动支付状态检查
    startPaymentCheck()
  } catch (error) {
    ElMessage.error(error.message || '支付失败')
  } finally {
    processing.value = false
  }
}

const startPaymentCheck = () => {
  paymentTimer.value = setInterval(async () => {
    try {
      // 这里应该调用后端检查支付状态的接口
      // const result = await api.get('/payment/status')
      // if (result.data.paid) {
      //   handlePaymentSuccess()
      // }
    } catch (error) {
      console.error('检查支付状态失败:', error)
    }
  }, 3000)
}

const checkPaymentStatus = async () => {
  try {
    // 模拟支付成功
    await planStore.renewMembership(paymentMethod.value)
    handlePaymentSuccess()
  } catch (error) {
    ElMessage.error(error.message || '支付确认失败')
  }
}

const handlePaymentSuccess = () => {
  clearInterval(paymentTimer.value)
  paymentDialogVisible.value = false
  paymentQrCode.value = ''
  
  ElMessage.success('支付成功，会员已续费')
  
  // 刷新会员状态
  planStore.fetchMembershipStatus()
}

const cancelPayment = () => {
  clearInterval(paymentTimer.value)
  paymentDialogVisible.value = false
  paymentQrCode.value = ''
  
  ElMessageBox.confirm('确定要取消支付吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '继续支付',
    type: 'warning'
  }).then(() => {
    ElMessage.info('支付已取消')
  }).catch(() => {
    paymentDialogVisible.value = true
    startPaymentCheck()
  })
}

onMounted(async () => {
  planStore.loadFromLocalStorage()
  
  try {
    await Promise.all([
      planStore.fetchMembershipStatus(),
      planStore.fetchPlans()
    ])
  } catch (error) {
    ElMessage.error('获取会员信息失败')
  }
})
</script>

<style scoped>
.renewal-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.status-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
}

.current-plan h3,
.expiry-info h3 {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 14px;
}

.days-left {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}

.plans-card {
  margin-bottom: 20px;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.plan-item {
  border: 2px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.plan-item:hover {
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.plan-item.selected {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.plan-header h3 {
  margin: 0;
  color: #303133;
}

.plan-price {
  margin-bottom: 10px;
}

.price {
  font-size: 32px;
  font-weight: bold;
  color: #f56c6c;
}

.unit {
  font-size: 14px;
  color: #909399;
  margin-left: 4px;
}

.plan-duration {
  color: #606266;
  margin-bottom: 15px;
}

.plan-features ul {
  list-style: none;
  padding: 0;
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
  color: #67c23a;
  margin-right: 8px;
}

.payment-card {
  margin-bottom: 20px;
}

.payment-methods {
  margin-bottom: 20px;
}

.payment-methods .el-radio {
  margin-right: 20px;
  margin-bottom: 10px;
}

.payment-methods .el-icon {
  margin-right: 8px;
}

.payment-summary {
  background-color: #f5f7fa;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #606266;
}

.summary-item:last-child {
  margin-bottom: 0;
}

.summary-item.total {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.summary-item.total .price {
  color: #f56c6c;
}

.payment-actions {
  text-align: center;
}

.payment-actions .el-button {
  min-width: 200px;
}

.payment-qr {
  text-align: center;
}

.qr-code {
  margin-bottom: 20px;
}

.qr-code img {
  width: 200px;
  height: 200px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.payment-tips p {
  margin: 5px 0;
  color: #606266;
}

.payment-tips .amount {
  font-size: 18px;
  font-weight: bold;
  color: #f56c6c;
}

@media (max-width: 768px) {
  .status-content {
    grid-template-columns: 1fr;
  }
  
  .plans-grid {
    grid-template-columns: 1fr;
  }
}
</style>