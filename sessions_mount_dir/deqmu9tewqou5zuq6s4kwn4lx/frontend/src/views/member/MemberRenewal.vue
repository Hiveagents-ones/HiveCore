<template>
  <div class="member-renewal">
    <el-card class="renewal-card">
      <template #header>
        <div class="card-header">
          <h2>会员续费</h2>
          <el-tag v-if="memberInfo" :type="getStatusType(memberInfo.status)">
            {{ memberInfo.status }}
          </el-tag>
        </div>
      </template>

      <!-- 会员信息展示 -->
      <div v-if="memberInfo" class="member-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="会员ID">{{ memberInfo.id }}</el-descriptions-item>
          <el-descriptions-item label="会员等级">{{ memberInfo.level }}</el-descriptions-item>
          <el-descriptions-item label="当前到期时间">{{ formatDate(memberInfo.expireDate) }}</el-descriptions-item>
          <el-descriptions-item label="剩余天数">{{ calculateRemainingDays(memberInfo.expireDate) }}天</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 套餐选择 -->
      <div class="package-selection">
        <h3>选择续费套餐</h3>
        <el-radio-group v-model="selectedPackage" class="package-group">
          <el-radio 
            v-for="pkg in packages" 
            :key="pkg.id" 
            :label="pkg.id"
            class="package-item"
          >
            <div class="package-content">
              <div class="package-name">{{ pkg.name }}</div>
              <div class="package-price">¥{{ pkg.price }}</div>
              <div class="package-duration">{{ pkg.duration }}天</div>
              <div v-if="pkg.discount" class="package-discount">{{ pkg.discount }}</div>
            </div>
          </el-radio>
        </el-radio-group>
      </div>

      <!-- 支付方式选择 -->
      <div class="payment-method">
        <h3>选择支付方式</h3>
        <el-radio-group v-model="paymentMethod" class="payment-group">
          <el-radio label="alipay" class="payment-item">
            <img src="/icons/alipay.png" alt="支付宝" class="payment-icon" />
            支付宝
          </el-radio>
          <el-radio label="wechat" class="payment-item">
            <img src="/icons/wechat.png" alt="微信支付" class="payment-icon" />
            微信支付
          </el-radio>
          <el-radio label="card" class="payment-item">
            <img src="/icons/card.png" alt="银行卡" class="payment-icon" />
            银行卡
          </el-radio>
        </el-radio-group>
      </div>

      <!-- 确认续费按钮 -->
      <div class="renewal-actions">
        <el-button 
          type="primary" 
          size="large" 
          :disabled="!selectedPackage || !paymentMethod"
          @click="handleRenewal"
          :loading="processing"
        >
          确认续费
        </el-button>
        <el-button size="large" @click="$router.back()">返回</el-button>
      </div>
    </el-card>

    <!-- 支付确认对话框 -->
    <el-dialog 
      v-model="showPaymentDialog" 
      title="支付确认" 
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="payment-confirmation">
        <p>请确认以下支付信息：</p>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="套餐名称">{{ selectedPackageInfo?.name }}</el-descriptions-item>
          <el-descriptions-item label="套餐时长">{{ selectedPackageInfo?.duration }}天</el-descriptions-item>
          <el-descriptions-item label="支付金额">¥{{ selectedPackageInfo?.price }}</el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ getPaymentMethodName(paymentMethod) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="showPaymentDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmPayment" :loading="processing">
          确认支付
        </el-button>
      </template>
    </el-dialog>

    <!-- 支付成功提示 -->
    <el-dialog 
      v-model="showSuccessDialog" 
      title="续费成功" 
      width="400px"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <div class="success-content">
        <el-result 
          icon="success" 
          title="续费成功" 
          :sub-title="`您的会员已成功续费${selectedPackageInfo?.duration}天，新的到期时间为${formatDate(newExpireDate)}`"
        >
          <template #extra>
            <el-button type="primary" @click="goToMemberCenter">返回会员中心</el-button>
          </template>
        </el-result>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useMemberStore } from '@/stores/member'
import { formatDate } from '@/utils/date'

const router = useRouter()
const memberStore = useMemberStore()

// 响应式数据
const memberInfo = ref(null)
const packages = ref([])
const selectedPackage = ref('')
const paymentMethod = ref('alipay')
const processing = ref(false)
const showPaymentDialog = ref(false)
const showSuccessDialog = ref(false)
const newExpireDate = ref(null)

// 计算属性
const selectedPackageInfo = computed(() => {
  return packages.value.find(pkg => pkg.id === selectedPackage.value)
})

// 方法
const getStatusType = (status) => {
  const statusMap = {
    '正常': 'success',
    '即将到期': 'warning',
    '已过期': 'danger'
  }
  return statusMap[status] || 'info'
}

const calculateRemainingDays = (expireDate) => {
  if (!expireDate) return 0
  const now = new Date()
  const expire = new Date(expireDate)
  const diffTime = expire - now
  return Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)))
}

const getPaymentMethodName = (method) => {
  const methodMap = {
    'alipay': '支付宝',
    'wechat': '微信支付',
    'card': '银行卡'
  }
  return methodMap[method] || method
}

const handleRenewal = () => {
  if (!selectedPackage.value || !paymentMethod.value) {
    ElMessage.warning('请选择套餐和支付方式')
    return
  }
  showPaymentDialog.value = true
}

const confirmPayment = async () => {
  processing.value = true
  try {
    // 调用续费API
    const response = await memberStore.renewMembership({
      packageId: selectedPackage.value,
      paymentMethod: paymentMethod.value
    })
    
    if (response.success) {
      newExpireDate.value = response.data.newExpireDate
      showPaymentDialog.value = false
      showSuccessDialog.value = true
      
      // 更新会员信息
      await fetchMemberInfo()
    } else {
      ElMessage.error(response.message || '续费失败')
    }
  } catch (error) {
    console.error('续费错误:', error)
    ElMessage.error('续费过程中发生错误，请稍后重试')
  } finally {
    processing.value = false
  }
}

const goToMemberCenter = () => {
  router.push('/member/center')
}

const fetchMemberInfo = async () => {
  try {
    const response = await memberStore.getMemberInfo()
    if (response.success) {
      memberInfo.value = response.data
    }
  } catch (error) {
    console.error('获取会员信息失败:', error)
  }
}

const fetchPackages = async () => {
  try {
    // 模拟获取套餐数据
    packages.value = [
      { id: 'monthly', name: '月卡', price: 30, duration: 30, discount: '无优惠' },
      { id: 'quarterly', name: '季卡', price: 80, duration: 90, discount: '省10元' },
      { id: 'yearly', name: '年卡', price: 280, duration: 365, discount: '省80元' }
    ]
  } catch (error) {
    console.error('获取套餐信息失败:', error)
  }
}

// 生命周期
onMounted(async () => {
  await fetchMemberInfo()
  await fetchPackages()
})
</script>

<style scoped>
.member-renewal {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.renewal-card {
  border-radius: 8px;
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

.member-info {
  margin-bottom: 30px;
}

.package-selection,
.payment-method {
  margin-bottom: 30px;
}

.package-selection h3,
.payment-method h3 {
  margin-bottom: 15px;
  color: #606266;
}

.package-group {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.package-item {
  flex: 1;
  min-width: 200px;
}

.package-content {
  padding: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition: all 0.3s;
}

.package-item.is-checked .package-content {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.package-name {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 8px;
}

.package-price {
  font-size: 20px;
  color: #f56c6c;
  margin-bottom: 5px;
}

.package-duration {
  color: #909399;
  margin-bottom: 5px;
}

.package-discount {
  color: #67c23a;
  font-size: 12px;
}

.payment-group {
  display: flex;
  gap: 20px;
}

.payment-item {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition: all 0.3s;
}

.payment-item.is-checked {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.payment-icon {
  width: 24px;
  height: 24px;
  margin-right: 8px;
}

.renewal-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 30px;
}

.payment-confirmation {
  margin-bottom: 20px;
}

.payment-confirmation p {
  margin-bottom: 15px;
  color: #606266;
}

.success-content {
  text-align: center;
}

@media (max-width: 768px) {
  .package-group {
    flex-direction: column;
  }
  
  .payment-group {
    flex-direction: column;
  }
  
  .renewal-actions {
    flex-direction: column;
  }
}
</style>