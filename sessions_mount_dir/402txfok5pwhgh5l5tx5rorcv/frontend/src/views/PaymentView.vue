<template>
  <div class="payment-view">
    <el-card class="payment-card">
      <template #header>
        <div class="card-header">
          <span>支付中心</span>
          <el-button type="primary" @click="showCreatePaymentDialog">发起支付</el-button>
        </div>
      </template>

      <!-- 支付历史表格 -->
      <el-table :data="paymentHistory" v-loading="loading" stripe>
        <el-table-column prop="id" label="订单号" width="100" />
        <el-table-column prop="member_id" label="会员ID" width="100" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            ¥{{ row.amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="支付类型" width="150">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">{{ getTypeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="viewPaymentDetail(row.id)">详情</el-button>
            <el-button 
              size="small" 
              type="danger" 
              v-if="row.status === 'pending'"
              @click="cancelPayment(row.id)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建支付对话框 -->
    <el-dialog v-model="createDialogVisible" title="发起支付" width="500px">
      <el-form :model="paymentForm" :rules="paymentRules" ref="paymentFormRef" label-width="100px">
        <el-form-item label="会员ID" prop="member_id">
          <el-input-number v-model="paymentForm.member_id" :min="1" placeholder="请输入会员ID" />
        </el-form-item>
        <el-form-item label="支付金额" prop="amount">
          <el-input-number v-model="paymentForm.amount" :min="0.01" :precision="2" placeholder="请输入金额" />
        </el-form-item>
        <el-form-item label="支付类型" prop="type">
          <el-select v-model="paymentForm.type" placeholder="请选择支付类型" @change="handleTypeChange">
            <el-option label="会员费" value="membership" />
            <el-option label="私教课" value="private_course" />
            <el-option label="课程预约" value="course_booking" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程ID" prop="course_id" v-if="showCourseId">
          <el-input-number v-model="paymentForm.course_id" :min="1" placeholder="请输入课程ID" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="paymentForm.remark" type="textarea" placeholder="请输入备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitPayment" :loading="submitting">确认支付</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 支付详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="支付详情" width="600px">
      <el-descriptions :column="2" border v-if="paymentDetail">
        <el-descriptions-item label="订单号">{{ paymentDetail.id }}</el-descriptions-item>
        <el-descriptions-item label="会员ID">{{ paymentDetail.member_id }}</el-descriptions-item>
        <el-descriptions-item label="金额">¥{{ paymentDetail.amount.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="支付类型">{{ getTypeLabel(paymentDetail.type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(paymentDetail.status)">{{ getStatusLabel(paymentDetail.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="课程ID" v-if="paymentDetail.course_id">{{ paymentDetail.course_id }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(paymentDetail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(paymentDetail.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { paymentsApi, PaymentMethod, PaymentType, PaymentStatus } from '@/api/payments'

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const createDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const paymentHistory = ref([])
const paymentDetail = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const showCourseId = ref(false)

// 表单引用
const paymentFormRef = ref(null)

// 支付表单
const paymentForm = reactive({
  member_id: null,
  amount: null,
  type: '',
  course_id: null,
  method: ''
})

// 表单验证规则
const paymentRules = {
  member_id: [{ required: true, message: '请输入会员ID', trigger: 'blur' }],
  amount: [{ required: true, message: '请输入支付金额', trigger: 'blur' }],
  type: [{ required: true, message: '请选择支付类型', trigger: 'change' }],
  course_id: [{ required: true, message: '请输入课程ID', trigger: 'blur' }],
  method: [{ required: true, message: '请选择支付方式', trigger: 'change' }]
}

// 获取支付历史
const fetchPaymentHistory = async () => {
  loading.value = true
  try {
    const response = await paymentsApi.getPaymentHistory({
      page: currentPage.value,
      size: pageSize.value
    })
    paymentHistory.value = response.items || []
    total.value = response.total || 0
  } catch (error) {
    ElMessage.error('获取支付历史失败')
  } finally {
    loading.value = false
  }
}

// 显示创建支付对话框
const showCreatePaymentDialog = () => {
  createDialogVisible.value = true
  // 重置表单
  Object.keys(paymentForm).forEach(key => {
    paymentForm[key] = key === 'type' || key === 'method' ? '' : null
  })
  showCourseId.value = false
}

// 处理支付类型变化
const handleTypeChange = (value) => {
  showCourseId.value = value === PaymentType.PRIVATE_COURSE || value === PaymentType.COURSE_BOOKING
  if (!showCourseId.value) {
    paymentForm.course_id = null
  }
}

// 提交支付
const submitPayment = async () => {
  if (!paymentFormRef.value) return
  
  try {
    await paymentFormRef.value.validate()
    submitting.value = true
    
    const paymentData = { ...paymentForm }
    if (!showCourseId.value) {
      delete paymentData.course_id
    }
    
    const response = await paymentsApi.createPaymentWithUrl(paymentData)
    if (response.payment_url) {
      window.open(response.payment_url, '_blank')
    }
    ElMessage.success('支付订单创建成功')
    createDialogVisible.value = false
    fetchPaymentHistory()
  } catch (error) {
    if (error.response) {
      ElMessage.error(error.response.data.message || '创建支付订单失败')
    } else {
      ElMessage.error('创建支付订单失败')
    }
  } finally {
    submitting.value = false
  }
}

// 查看支付详情
const viewPaymentDetail = async (paymentId) => {
  try {
    const response = await paymentsApi.getPaymentDetail(paymentId)
    paymentDetail.value = response
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取支付详情失败')
  }
}

// 取消支付
const cancelPayment = async (paymentId) => {
  try {
    await ElMessageBox.confirm('确定要取消该支付订单吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await paymentsApi.cancelPayment(paymentId)
    ElMessage.success('支付订单已取消')
    fetchPaymentHistory()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消支付失败')
    }
  }
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchPaymentHistory()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchPaymentHistory()
}

// 工具函数
const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const getTypeLabel = (type) => {
  const labels = {
    [PaymentType.MEMBERSHIP]: '会员费',
    [PaymentType.PRIVATE_COURSE]: '私教课',
    [PaymentType.COURSE_BOOKING]: '课程预约'
  }
  return labels[type] || type
}

const getTypeTagType = (type) => {
  const types = {
    [PaymentType.MEMBERSHIP]: 'primary',
    [PaymentType.PRIVATE_COURSE]: 'success',
    [PaymentType.COURSE_BOOKING]: 'warning'
  }
  return types[type] || ''
}

const getStatusLabel = (status) => {
  const labels = {
    [PaymentStatus.PENDING]: '待支付',
    [PaymentStatus.SUCCESS]: '支付成功',
    [PaymentStatus.FAILED]: '支付失败',
    [PaymentStatus.CANCELLED]: '已取消'
  }
  return labels[status] || status
}

const getStatusTagType = (status) => {
  const types = {
    [PaymentStatus.PENDING]: 'warning',
    [PaymentStatus.SUCCESS]: 'success',
    [PaymentStatus.FAILED]: 'danger',
    [PaymentStatus.CANCELLED]: 'info'
  }
  return types[status] || ''
}

// 生命周期
onMounted(() => {
  fetchPaymentHistory()
})
</script>

<style scoped>
.payment-view {
  padding: 20px;
}

.payment-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const paymentForm = reactive({
  member_id: null,
  amount: null,
  type: '',
  course_id: null,
  remark: ''
})

# [AUTO-APPENDED] Failed to replace, adding new code:
const paymentRules = {
  member_id: [{ required: true, message: '请输入会员ID', trigger: 'blur' }],
  amount: [{ required: true, message: '请输入支付金额', trigger: 'blur' }],
  type: [{ required: true, message: '请选择支付类型', trigger: 'change' }],
  course_id: [{ required: true, message: '请输入课程ID', trigger: 'blur' }],
  remark: [{ required: false, message: '请输入备注信息', trigger: 'blur' }]
}