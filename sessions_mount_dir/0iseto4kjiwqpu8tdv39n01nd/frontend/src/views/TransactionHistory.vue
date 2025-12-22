<template>
  <div class="transaction-history">
    <div class="page-header">
      <h1>交易历史</h1>
      <p class="subtitle">查看您的所有订单和支付记录</p>
    </div>

    <div class="filters">
      <div class="filter-group">
        <label for="statusFilter">状态筛选</label>
        <select id="statusFilter" v-model="filters.status">
          <option value="">全部</option>
          <option value="pending">待支付</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="typeFilter">类型筛选</label>
        <select id="typeFilter" v-model="filters.type">
          <option value="">全部</option>
          <option value="subscription">订阅</option>
          <option value="renewal">续费</option>
          <option value="upgrade">升级</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="dateRange">日期范围</label>
        <input type="date" id="dateRange" v-model="filters.dateRange" />
      </div>
    </div>

    <div class="transactions-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="transactions.length === 0" class="empty-state">
        <p>暂无交易记录</p>
      </div>
      <div v-else>
        <div v-for="transaction in transactions" :key="transaction.id" class="transaction-item">
          <div class="transaction-header">
            <span class="transaction-id">订单号: {{ transaction.orderId }}</span>
            <span :class="['status', transaction.status]">{{ getStatusText(transaction.status) }}</span>
          </div>
          <div class="transaction-details">
            <div class="detail-row">
              <span class="label">类型:</span>
              <span class="value">{{ getTypeText(transaction.type) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">金额:</span>
              <span class="value">¥{{ transaction.amount.toFixed(2) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">支付方式:</span>
              <span class="value">{{ getPaymentMethodText(transaction.paymentMethod) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">创建时间:</span>
              <span class="value">{{ formatDate(transaction.createdAt) }}</span>
            </div>
            <div v-if="transaction.completedAt" class="detail-row">
              <span class="label">完成时间:</span>
              <span class="value">{{ formatDate(transaction.completedAt) }}</span>
            </div>
          </div>
          <div v-if="transaction.status === 'pending'" class="transaction-actions">
            <button @click="handlePayment(transaction)" class="btn-primary">继续支付</button>
            <button @click="handleCancel(transaction)" class="btn-secondary">取消订单</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button @click="prevPage" :disabled="currentPage === 1">上一页</button>
      <span>第 {{ currentPage }} 页，共 {{ totalPages }} 页</span>
      <button @click="nextPage" :disabled="currentPage === totalPages">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { fetchTransactions, cancelOrder } from '@/api/payment'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const transactions = ref([])
const currentPage = ref(1)
const totalPages = ref(1)
const filters = ref({
  status: '',
  type: '',
  dateRange: ''
})

const loadTransactions = async () => {
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      limit: 10,
      ...filters.value
    }
    const response = await fetchTransactions(params)
    transactions.value = response.data.items
    totalPages.value = Math.ceil(response.data.total / 10)
  } catch (error) {
    console.error('加载交易历史失败:', error)
  } finally {
    loading.value = false
  }
}

const handlePayment = (transaction) => {
  router.push({
    name: 'Payment',
    query: { orderId: transaction.orderId }
  })
}

const handleCancel = async (transaction) => {
  try {
    await cancelOrder(transaction.orderId)
    await loadTransactions()
  } catch (error) {
    console.error('取消订单失败:', error)
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '待支付',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

const getTypeText = (type) => {
  const typeMap = {
    subscription: '订阅',
    renewal: '续费',
    upgrade: '升级'
  }
  return typeMap[type] || type
}

const getPaymentMethodText = (method) => {
  const methodMap = {
    alipay: '支付宝',
    wechat: '微信支付',
    stripe: '信用卡'
  }
  return methodMap[method] || method
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

watch(filters, () => {
  currentPage.value = 1
  loadTransactions()
}, { deep: true })

watch(currentPage, () => {
  loadTransactions()
})

onMounted(() => {
  if (!userStore.isAuthenticated) {
    router.push({ name: 'Login' })
    return
  }
  loadTransactions()
})
</script>

<style scoped>
.transaction-history {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 10px;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.filters {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.filter-group label {
  font-size: 14px;
  color: #666;
}

.filter-group select,
.filter-group input {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.transactions-list {
  margin-bottom: 30px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.transaction-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
  transition: box-shadow 0.3s;
}

.transaction-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.transaction-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.transaction-id {
  font-weight: 600;
  color: #333;
}

.status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status.pending {
  background: #fff3cd;
  color: #856404;
}

.status.completed {
  background: #d4edda;
  color: #155724;
}

.status.failed {
  background: #f8d7da;
  color: #721c24;
}

.status.cancelled {
  background: #e2e3e5;
  color: #383d41;
}

.transaction-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 15px;
}

.detail-row {
  display: flex;
  gap: 10px;
}

.label {
  color: #666;
  font-size: 14px;
}

.value {
  color: #333;
  font-size: 14px;
  font-weight: 500;
}

.transaction-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.btn-primary {
  background: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary:hover {
  background: #545b62;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination button:hover:not(:disabled) {
  background: #f5f5f5;
}

@media (max-width: 768px) {
  .filters {
    flex-direction: column;
  }

  .transaction-details {
    grid-template-columns: 1fr;
  }

  .transaction-actions {
    flex-direction: column;
  }
}
</style>