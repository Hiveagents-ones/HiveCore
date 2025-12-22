<template>
  <div class="payment-history">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="会员ID">
          <el-input
            v-model="filterForm.member_id"
            placeholder="请输入会员ID"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="支付状态">
          <el-select
            v-model="filterForm.status"
            placeholder="请选择支付状态"
            clearable
          >
            <el-option
              v-for="(label, value) in statusOptions"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="支付类型">
          <el-select
            v-model="filterForm.type"
            placeholder="请选择支付类型"
            clearable
          >
            <el-option
              v-for="(label, value) in typeOptions"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="paymentList"
        style="width: 100%"
        stripe
      >
        <el-table-column prop="id" label="支付ID" width="100" />
        <el-table-column prop="member_id" label="会员ID" width="100" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            ¥{{ row.amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="支付类型" width="150">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">
              {{ typeOptions[row.type] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ statusOptions[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="120">
          <template #default="{ row }">
            {{ getPaymentMethodLabel(row.payment_method) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              @click="handleViewDetail(row.id)"
            >
              详情
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              type="danger"
              link
              @click="handleCancel(row.id)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="支付详情"
      width="600px"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="支付ID">
          {{ paymentDetail.id }}
        </el-descriptions-item>
        <el-descriptions-item label="会员ID">
          {{ paymentDetail.member_id }}
        </el-descriptions-item>
        <el-descriptions-item label="金额">
          ¥{{ paymentDetail.amount?.toFixed(2) }}
        </el-descriptions-item>
        <el-descriptions-item label="支付类型">
          {{ typeOptions[paymentDetail.type] }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(paymentDetail.status)">
            {{ statusOptions[paymentDetail.status] }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="课程ID">
          {{ paymentDetail.course_id || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(paymentDetail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDateTime(paymentDetail.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="支付方式">
          {{ getPaymentMethodLabel(paymentDetail.payment_method) }}
        </el-descriptions-item>
        <el-descriptions-item label="支付渠道订单号">
          {{ paymentDetail.channel_order_id || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { paymentsApi, PaymentType, PaymentStatus } from '@/api/payments'

// 响应式数据
const loading = ref(false)
const paymentList = ref([])
const paymentDetail = ref({})
const detailDialogVisible = ref(false)

// 筛选表单
const filterForm = reactive({
  member_id: '',
  status: '',
  type: '',
  dateRange: []
})

// 分页数据
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 支付类型选项
const typeOptions = {
  [PaymentType.MEMBERSHIP]: '会员费',
  [PaymentType.PRIVATE_COURSE]: '私教课',
  [PaymentType.COURSE_BOOKING]: '课程预约'
}

// 支付状态选项
const statusOptions = {
  [PaymentStatus.PENDING]: '待支付',
  [PaymentStatus.SUCCESS]: '支付成功',
  [PaymentStatus.FAILED]: '支付失败',
  [PaymentStatus.CANCELLED]: '已取消'
}

// 获取支付历史列表
const fetchPaymentHistory = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      ...filterForm
    }
    // 处理日期范围
    if (params.dateRange && params.dateRange.length === 2) {
      params.start_date = params.dateRange[0]
      params.end_date = params.dateRange[1]
    }
    delete params.dateRange
    
    // 清理空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    
    const response = await paymentsApi.getPaymentHistory(params)
    paymentList.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    ElMessage.error('获取支付历史失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}

// 获取支付详情
const fetchPaymentDetail = async (paymentId) => {
  try {
    const response = await paymentsApi.getPaymentDetail(paymentId)
    paymentDetail.value = response
  } catch (error) {
    ElMessage.error('获取支付详情失败: ' + (error.response?.data?.message || error.message))
  }
}

// 取消支付
const cancelPayment = async (paymentId) => {
  try {
    await paymentsApi.cancelPayment(paymentId)
    ElMessage.success('取消支付成功')
    fetchPaymentHistory()
  } catch (error) {
    ElMessage.error('取消支付失败: ' + (error.response?.data?.message || error.message))
  }
}

// 事件处理
const handleSearch = () => {
  pagination.page = 1
  fetchPaymentHistory()
}

const handleReset = () => {
  filterForm.member_id = ''
  filterForm.status = ''
  filterForm.type = ''
  filterForm.dateRange = []
  pagination.page = 1
  fetchPaymentHistory()
}

const handleSizeChange = (val) => {
  pagination.size = val
  pagination.page = 1
  fetchPaymentHistory()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchPaymentHistory()
}

const handleViewDetail = (paymentId) => {
  fetchPaymentDetail(paymentId)
  detailDialogVisible.value = true
}

const handleCancel = (paymentId) => {
  ElMessageBox.confirm(
    '确认取消该笔支付吗？',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    cancelPayment(paymentId)
  }).catch(() => {
    // 用户取消操作
  })
}

// 工具函数
const getTypeTagType = (type) => {
  const typeMap = {
    [PaymentType.MEMBERSHIP]: 'primary',
    [PaymentType.PRIVATE_COURSE]: 'success',
    [PaymentType.COURSE_BOOKING]: 'warning'
  }
  return typeMap[type] || ''
}

const getStatusTagType = (status) => {
  const statusMap = {
    [PaymentStatus.PENDING]: 'warning',
    [PaymentStatus.SUCCESS]: 'success',
    [PaymentStatus.FAILED]: 'danger',
    [PaymentStatus.CANCELLED]: 'info'
  }
  return statusMap[status] || ''
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getPaymentMethodLabel = (method) => {
  return paymentMethodOptions[method] || '-'
}

// 生命周期
onMounted(() => {
  fetchPaymentHistory()
})
</script>

<style scoped>
.payment-history {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>