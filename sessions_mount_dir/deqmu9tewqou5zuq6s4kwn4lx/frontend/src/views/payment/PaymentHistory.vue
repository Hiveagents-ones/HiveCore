<template>
  <div class="payment-history">
    <div class="page-header">
      <h1>支付历史记录</h1>
      <div class="performance-metrics" v-if="metrics">
        <span class="metric">响应时间: {{ metrics.responseTime }}ms</span>
        <span class="metric">数据量: {{ metrics.dataCount }}</span>
        <span class="metric">最后更新: {{ metrics.lastUpdate }}</span>
      </div>
    </div>

    <div class="filters">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="handleDateChange"
      />
      <el-select v-model="statusFilter" placeholder="支付状态" @change="handleStatusChange">
        <el-option label="全部" value="" />
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="处理中" value="pending" />
      </el-select>
      <el-button type="primary" @click="refreshData">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <div class="payment-table">
      <el-table
        v-loading="loading"
        :data="paymentHistory"
        style="width: 100%"
        :default-sort="{ prop: 'paymentDate', order: 'descending' }"
      >
        <el-table-column prop="paymentId" label="支付ID" width="120" />
        <el-table-column prop="memberId" label="会员ID" width="120" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="scope">
            ¥{{ scope.row.amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="paymentMethod" label="支付方式" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="paymentDate" label="支付日期" width="180" sortable>
          <template #default="scope">
            {{ formatDate(scope.row.paymentDate) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" @click="viewDetails(scope.row)">
              详情
            </el-button>
            <el-button
              size="small"
              type="danger"
              v-if="scope.row.status === 'success'"
              @click="handleRefund(scope.row)"
            >
              退款
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
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
    </div>

    <!-- 支付详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="支付详情"
      width="50%"
    >
      <div v-if="selectedPayment" class="payment-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="支付ID">{{ selectedPayment.paymentId }}</el-descriptions-item>
          <el-descriptions-item label="会员ID">{{ selectedPayment.memberId }}</el-descriptions-item>
          <el-descriptions-item label="金额">¥{{ selectedPayment.amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ selectedPayment.paymentMethod }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedPayment.status)">
              {{ getStatusText(selectedPayment.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="支付日期">{{ formatDate(selectedPayment.paymentDate) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ selectedPayment.description }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(selectedPayment.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(selectedPayment.updatedAt) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 退款对话框 -->
    <el-dialog
      v-model="refundDialogVisible"
      title="退款"
      width="40%"
    >
      <el-form :model="refundForm" label-width="100px">
        <el-form-item label="退款金额">
          <el-input-number
            v-model="refundForm.amount"
            :min="0"
            :max="selectedPayment?.amount || 0"
            :precision="2"
          />
        </el-form-item>
        <el-form-item label="退款原因">
          <el-input
            v-model="refundForm.reason"
            type="textarea"
            rows="3"
            placeholder="请输入退款原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="refundDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmRefund">确认退款</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { paymentAPI } from '@/api/payment'

// 响应式数据
const loading = ref(false)
const paymentHistory = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const dateRange = ref([])
const statusFilter = ref('')

// 性能指标
const metrics = ref(null)

// 对话框状态
const detailDialogVisible = ref(false)
const refundDialogVisible = ref(false)
const selectedPayment = ref(null)

// 退款表单
const refundForm = ref({
  amount: 0,
  reason: ''
})

// 获取支付历史
const fetchPaymentHistory = async () => {
  loading.value = true
  const startTime = performance.now()
  
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      status: statusFilter.value
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0].toISOString()
      params.endDate = dateRange.value[1].toISOString()
    }
    
    const response = await paymentAPI.getPaymentHistory('current', params)
    paymentHistory.value = response.data.items || []
    total.value = response.data.total || 0
    
    // 更新性能指标
    const endTime = performance.now()
    metrics.value = {
      responseTime: Math.round(endTime - startTime),
      dataCount: paymentHistory.value.length,
      lastUpdate: new Date().toLocaleTimeString()
    }
  } catch (error) {
    console.error('Failed to fetch payment history:', error)
    ElMessage.error('获取支付历史失败')
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  fetchPaymentHistory()
}

// 处理日期范围变化
const handleDateChange = () => {
  currentPage.value = 1
  fetchPaymentHistory()
}

// 处理状态筛选变化
const handleStatusChange = () => {
  currentPage.value = 1
  fetchPaymentHistory()
}

// 处理分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchPaymentHistory()
}

// 处理页码变化
const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchPaymentHistory()
}

// 查看详情
const viewDetails = (payment) => {
  selectedPayment.value = payment
  detailDialogVisible.value = true
}

// 处理退款
const handleRefund = (payment) => {
  selectedPayment.value = payment
  refundForm.value = {
    amount: payment.amount,
    reason: ''
  }
  refundDialogVisible.value = true
}

// 确认退款
const confirmRefund = async () => {
  if (!refundForm.value.reason) {
    ElMessage.warning('请输入退款原因')
    return
  }
  
  try {
    await paymentAPI.refundPayment(selectedPayment.value.paymentId, refundForm.value)
    ElMessage.success('退款申请已提交')
    refundDialogVisible.value = false
    fetchPaymentHistory()
  } catch (error) {
    console.error('Refund failed:', error)
    ElMessage.error('退款失败')
  }
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    success: 'success',
    failed: 'danger',
    pending: 'warning'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    success: '成功',
    failed: '失败',
    pending: '处理中'
  }
  return texts[status] || status
}

// 格式化日期
const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 组件挂载
onMounted(() => {
  fetchPaymentHistory()
})
</script>

<style scoped>
.payment-history {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.performance-metrics {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #666;
}

.metric {
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.filters {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  align-items: center;
}

.payment-table {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.payment-details {
  padding: 20px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>