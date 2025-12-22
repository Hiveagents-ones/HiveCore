<template>
  <div class="offline-payment">
    <el-card class="payment-card">
      <template #header>
        <div class="card-header">
          <span>线下支付录入</span>
        </div>
      </template>
      
      <el-form
        ref="paymentFormRef"
        :model="paymentForm"
        :rules="paymentRules"
        label-width="120px"
        class="payment-form"
      >
        <el-form-item label="会员ID" prop="member_id">
          <el-input
            v-model="paymentForm.member_id"
            placeholder="请输入会员ID"
            clearable
          />
        </el-form-item>
        
        <el-form-item label="支付金额" prop="amount">
          <el-input-number
            v-model="paymentForm.amount"
            :min="0"
            :precision="2"
            :step="0.01"
            placeholder="请输入支付金额"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="支付方式" prop="payment_method">
          <el-select
            v-model="paymentForm.payment_method"
            placeholder="请选择支付方式"
            style="width: 100%"
          >
            <el-option label="现金" value="cash" />
            <el-option label="银行转账" value="bank_transfer" />
            <el-option label="支票" value="check" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="支付日期" prop="payment_date">
          <el-date-picker
            v-model="paymentForm.payment_date"
            type="datetime"
            placeholder="选择支付日期时间"
            style="width: 100%"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        
        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="paymentForm.notes"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            @click="submitPayment"
            :loading="submitting"
          >
            提交支付记录
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card class="recent-payments" v-if="recentPayments.length > 0">
      <template #header>
        <div class="card-header">
          <span>最近线下支付记录</span>
        </div>
      </template>
      
      <el-table :data="recentPayments" style="width: 100%">
        <el-table-column prop="member_id" label="会员ID" width="120" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="scope">
            ¥{{ scope.row.amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="120">
          <template #default="scope">
            {{ getPaymentMethodLabel(scope.row.payment_method) }}
          </template>
        </el-table-column>
        <el-table-column prop="payment_date" label="支付日期" width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// 表单引用
const paymentFormRef = ref(null)
const submitting = ref(false)
const recentPayments = ref([])

// 支付表单数据
const paymentForm = reactive({
  member_id: '',
  amount: null,
  payment_method: '',
  payment_date: '',
  notes: ''
})

// 表单验证规则
const paymentRules = {
  member_id: [
    { required: true, message: '请输入会员ID', trigger: 'blur' }
  ],
  amount: [
    { required: true, message: '请输入支付金额', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '金额必须大于0', trigger: 'blur' }
  ],
  payment_method: [
    { required: true, message: '请选择支付方式', trigger: 'change' }
  ],
  payment_date: [
    { required: true, message: '请选择支付日期', trigger: 'change' }
  ]
}

// 获取支付方式标签
const getPaymentMethodLabel = (method) => {
  const labels = {
    cash: '现金',
    bank_transfer: '银行转账',
    check: '支票',
    other: '其他'
  }
  return labels[method] || method
}

// 获取状态标签
const getStatusLabel = (status) => {
  const labels = {
    pending: '待确认',
    confirmed: '已确认',
    cancelled: '已取消'
  }
  return labels[status] || status
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    confirmed: 'success',
    cancelled: 'danger'
  }
  return types[status] || 'info'
}

// 提交支付记录
const submitPayment = async () => {
  if (!paymentFormRef.value) return
  
  try {
    await paymentFormRef.value.validate()
    submitting.value = true
    
    const response = await axios.post('/api/v1/payments/offline', paymentForm)
    
    if (response.data.success) {
      ElMessage.success('支付记录提交成功')
      resetForm()
      fetchRecentPayments()
    } else {
      ElMessage.error(response.data.message || '提交失败')
    }
  } catch (error) {
    console.error('提交支付记录失败:', error)
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('提交失败，请稍后重试')
    }
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (paymentFormRef.value) {
    paymentFormRef.value.resetFields()
  }
  Object.assign(paymentForm, {
    member_id: '',
    amount: null,
    payment_method: '',
    payment_date: '',
    notes: ''
  })
}

// 获取最近支付记录
const fetchRecentPayments = async () => {
  try {
    const response = await axios.get('/api/v1/payments/offline/recent', {
      params: { limit: 10 }
    })
    
    if (response.data.success) {
      recentPayments.value = response.data.data || []
    }
  } catch (error) {
    console.error('获取最近支付记录失败:', error)
  }
}

// 组件挂载时获取数据
onMounted(() => {
  fetchRecentPayments()
})
</script>

<style scoped>
.offline-payment {
  padding: 20px;
}

.payment-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.payment-form {
  max-width: 600px;
  margin: 0 auto;
}

.recent-payments {
  margin-top: 20px;
}
</style>