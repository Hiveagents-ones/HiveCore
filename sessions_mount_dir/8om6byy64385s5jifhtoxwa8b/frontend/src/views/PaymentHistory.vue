<template>
  <div class="payment-history">
    <div class="page-header">
      <h1>支付历史记录</h1>
      <p class="subtitle">查看您的所有会员购买和续费记录</p>
    </div>

    <div class="filters-section">
      <div class="filter-group">
        <label for="status-filter">状态筛选</label>
        <select id="status-filter" v-model="filters.status" @change="fetchPaymentHistory">
          <option value="">全部状态</option>
          <option value="pending">待支付</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="refunded">已退款</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="method-filter">支付方式</label>
        <select id="method-filter" v-model="filters.method" @change="fetchPaymentHistory">
          <option value="">全部方式</option>
          <option value="alipay">支付宝</option>
          <option value="wechat">微信支付</option>
          <option value="stripe">信用卡/借记卡</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="date-range">日期范围</label>
        <div class="date-range-inputs">
          <input 
            type="date" 
            id="start-date" 
            v-model="filters.startDate" 
            @change="fetchPaymentHistory"
            :max="filters.endDate || today"
          />
          <span>至</span>
          <input 
            type="date" 
            id="end-date" 
            v-model="filters.endDate" 
            @change="fetchPaymentHistory"
            :min="filters.startDate"
            :max="today"
          />
        </div>
      </div>

      <div class="filter-actions">
        <button class="btn btn-secondary" @click="resetFilters">重置筛选</button>
        <button class="btn btn-primary" @click="fetchPaymentHistory">刷新数据</button>
      </div>
    </div>

    <div class="payment-list" v-if="!loading">
      <div v-if="payments.length === 0" class="empty-state">
        <div class="empty-icon">💳</div>
        <h3>暂无支付记录</h3>
        <p>您还没有任何支付记录，当您购买会员计划后，这里将显示您的支付历史。</p>
        <router-link to="/membership" class="btn btn-primary">浏览会员计划</router-link>
      </div>

      <div v-else class="payment-cards">
        <div v-for="payment in payments" :key="payment.id" class="payment-card">
          <div class="payment-header">
            <div class="payment-info">
              <h3 class="payment-plan">{{ payment.plan_name || '会员计划' }}</h3>
              <p class="payment-date">{{ formatDate(payment.created_at) }}</p>
            </div>
            <div class="payment-amount">
              <span class="amount">{{ formatCurrency(payment.amount, payment.currency) }}</span>
              <span :class="['status-badge', payment.status]">{{ getStatusText(payment.status) }}</span>
            </div>
          </div>

          <div class="payment-details">
            <div class="detail-row">
              <span class="label">支付ID:</span>
              <span class="value">{{ payment.id }}</span>
            </div>
            <div class="detail-row">
              <span class="label">支付方式:</span>
              <span class="value">{{ getMethodText(payment.payment_method) }}</span>
            </div>
            <div v-if="payment.transaction_id" class="detail-row">
              <span class="label">交易ID:</span>
              <span class="value">{{ payment.transaction_id }}</span>
            </div>
            <div v-if="payment.refunded_amount > 0" class="detail-row">
              <span class="label">退款金额:</span>
              <span class="value">{{ formatCurrency(payment.refunded_amount, payment.currency) }}</span>
            </div>
          </div>

          <div class="payment-actions">
            <button v-if="payment.status === 'pending'" class="btn btn-outline" @click="continuePayment(payment.id)">继续支付</button>
            <button v-if="payment.status === 'pending'" class="btn btn-outline-danger" @click="cancelPayment(payment.id)">删除订单</button>
            <button v-if="payment.status === 'completed' && payment.refunded_amount === 0" class="btn btn-outline" @click="openRefundDialog(payment)">申请退款</button>
            <button class="btn btn-outline" @click="viewDetails(payment.id)">查看详情</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>加载支付记录中...</p>
    </div>

    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="fetchPaymentHistory">重试</button>
    </div>

    <div v-if="payments.length > 0 && totalPages > 1" class="pagination">
      <button 
        class="pagination-btn" 
        :disabled="currentPage === 1" 
        @click="changePage(currentPage - 1)"
      >
        上一页
      </button>
      
      <div class="page-numbers">
        <button 
          v-for="page in visiblePages" 
          :key="page" 
          class="pagination-btn" 
          :class="{ active: page === currentPage }"
          @click="changePage(page)"
        >
          {{ page }}
        </button>
      </div>
      
      <button 
        class="pagination-btn" 
        :disabled="currentPage === totalPages" 
        @click="changePage(currentPage + 1)"
      >
        下一页
      </button>
    </div>

    <!-- 退款申请对话框 -->
    <div v-if="showRefundDialog" class="modal-overlay" @click="closeRefundDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>申请退款</h3>
          <button class="close-btn" @click="closeRefundDialog">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="refund-amount">退款金额</label>
            <input 
              type="number" 
              id="refund-amount" 
              v-model.number="refundForm.amount" 
              :max="selectedPayment?.amount || 0"
              step="0.01"
              min="0.01"
            />
            <small>最大可退款金额: {{ formatCurrency(selectedPayment?.amount || 0, selectedPayment?.currency || 'CNY') }}</small>
          </div>
          <div class="form-group">
            <label for="refund-reason">退款原因</label>
            <textarea id="refund-reason" v-model="refundForm.reason" rows="4" placeholder="请输入退款原因..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeRefundDialog">取消</button>
          <button class="btn btn-primary" @click="submitRefund" :disabled="submittingRefund">
            {{ submittingRefund ? '提交中...' : '提交申请' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 支付详情对话框 -->
    <div v-if="showDetailsDialog" class="modal-overlay" @click="closeDetailsDialog">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>支付详情</h3>
          <button class="close-btn" @click="closeDetailsDialog">&times;</button>
        </div>
        <div class="modal-body" v-if="selectedPayment">
          <div class="detail-section">
            <h4>订单信息</h4>
            <div class="detail-row">
              <span class="label">订单ID:</span>
              <span class="value">{{ selectedPayment.id }}</span>
            </div>
            <div class="detail-row">
              <span class="label">创建时间:</span>
              <span class="value">{{ formatDate(selectedPayment.created_at) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">会员计划:</span>
              <span class="value">{{ selectedPayment.plan_name || '会员计划' }}</span>
            </div>
            <div class="detail-row">
              <span class="label">金额:</span>
              <span class="value">{{ formatCurrency(selectedPayment.amount, selectedPayment.currency) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">状态:</span>
              <span :class="['status-badge', selectedPayment.status]">{{ getStatusText(selectedPayment.status) }}</span>
            </div>
          </div>

          <div class="detail-section">
            <h4>支付信息</h4>
            <div class="detail-row">
              <span class="label">支付方式:</span>
              <span class="value">{{ getMethodText(selectedPayment.payment_method) }}</span>
            </div>
            <div v-if="selectedPayment.transaction_id" class="detail-row">
              <span class="label">交易ID:</span>
              <span class="value">{{ selectedPayment.transaction_id }}</span>
            </div>
            <div v-if="selectedPayment.paid_at" class="detail-row">
              <span class="label">支付时间:</span>
              <span class="value">{{ formatDate(selectedPayment.paid_at) }}</span>
            </div>
          </div>

          <div v-if="selectedPayment.refunded_amount > 0" class="detail-section">
            <h4>退款信息</h4>
            <div class="detail-row">
              <span class="label">退款金额:</span>
              <span class="value">{{ formatCurrency(selectedPayment.refunded_amount, selectedPayment.currency) }}</span>
            </div>
            <div v-if="selectedPayment.refunded_at" class="detail-row">
              <span class="label">退款时间:</span>
              <span class="value">{{ formatDate(selectedPayment.refunded_at) }}</span>
            </div>
            <div v-if="selectedPayment.refund_reason" class="detail-row">
              <span class="label">退款原因:</span>
              <span class="value">{{ selectedPayment.refund_reason }}</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="closeDetailsDialog">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getPaymentHistory, cancelPayment as cancelPaymentApi, requestRefund as requestRefundApi, getPaymentDetails, exportPaymentHistory } from '@/api/payment';

export default {
  name: 'PaymentHistory',
  setup() {
    const router = useRouter();
    const payments = ref([]);
    const loading = ref(true);
    const error = ref(null);
    const currentPage = ref(1);
    const totalPages = ref(1);
    const pageSize = ref(10);
    const today = computed(() => new Date().toISOString().split('T')[0]);
    
    const filters = reactive({
      status: '',
      method: '',
      startDate: '',
      endDate: ''
    });
    
    const showRefundDialog = ref(false);
    const showDetailsDialog = ref(false);
    const selectedPayment = ref(null);
    const submittingRefund = ref(false);
    const exporting = ref(false);
    
    const refundForm = reactive({
      amount: 0,
      reason: ''
    });
    
    // 计算可见的页码
    const visiblePages = computed(() => {
      const pages = [];
      const maxVisible = 5;
      
      if (totalPages.value <= maxVisible) {
        for (let i = 1; i <= totalPages.value; i++) {
          pages.push(i);
        }
      } else {
        const start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2));
        const end = Math.min(totalPages.value, start + maxVisible - 1);
        
        for (let i = start; i <= end; i++) {
          pages.push(i);
        }
      }
      
      return pages;
    });
    
    // 获取支付历史
    const fetchPaymentHistory = async () => {
      loading.value = true;
      error.value = null;
      
      try {
        const params = {
          page: currentPage.value,
          limit: pageSize.value,
          ...filters
        };
        
        // 移除空值参数
        Object.keys(params).forEach(key => {
          if (params[key] === '' || params[key] === null || params[key] === undefined) {
            delete params[key];
          }
        });
        
        const response = await getPaymentHistory(params);
        payments.value = response.items || [];
        totalPages.value = Math.ceil((response.total || 0) / pageSize.value);
      } catch (err) {
        console.error('获取支付历史失败:', err);
        error.value = '获取支付历史失败，请稍后重试';
      } finally {
        loading.value = false;
      }
    };
    
    // 切换页码
    const changePage = (page) => {
      if (page >= 1 && page <= totalPages.value) {
        currentPage.value = page;
        fetchPaymentHistory();
      }
    };
    
    // 重置筛选条件
    const resetFilters = () => {
      filters.status = '';
      filters.method = '';
      filters.startDate = '';
      filters.endDate = '';
      currentPage.value = 1;
      fetchPaymentHistory();
    };
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '未知';
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    };
    
    // 格式化货币
    const formatCurrency = (amount, currency = 'CNY') => {
      const formatter = new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: currency
      });
      return formatter.format(amount);
    };
    
    // 获取状态文本
    const getStatusText = (status) => {
      const statusMap = {
        pending: '待支付',
        completed: '已完成',
        failed: '失败',
        refunded: '已退款',
        cancelled: '已取消'
      };
      return statusMap[status] || status;
    };
    
    // 获取支付方式文本
    const getMethodText = (method) => {
      const methodMap = {
        alipay: '支付宝',
        wechat: '微信支付',
        stripe: '信用卡/借记卡'
      };
      return methodMap[method] || method;
    };
    
    // 继续支付
    const continuePayment = (paymentId) => {
      router.push(`/payment?id=${paymentId}`);
    };
    
    // 取消支付
    const cancelPayment = async (paymentId) => {
      if (!confirm('确定要取消此支付订单吗？')) return;
      
      try {
        await cancelPaymentApi(paymentId);
        alert('订单已取消');
        fetchPaymentHistory();
      } catch (err) {
        console.error('取消支付失败:', err);
        alert('取消支付失败，请稍后重试');
      }
    };
    
    // 打开退款对话框
    const openRefundDialog = (payment) => {
      selectedPayment.value = payment;
      refundForm.amount = payment.amount;
      refundForm.reason = '';
      showRefundDialog.value = true;
    };
    
    // 关闭退款对话框
    const closeRefundDialog = () => {
      showRefundDialog.value = false;
      selectedPayment.value = null;
      refundForm.amount = 0;
      refundForm.reason = '';
    };
    
    // 提交退款申请
    const submitRefund = async () => {
      if (!refundForm.amount || refundForm.amount <= 0) {
        alert('请输入有效的退款金额');
        return;
      }
      
      if (!refundForm.reason.trim()) {
        alert('请输入退款原因');
        return;
      }
      
      submittingRefund.value = true;
      
      try {
        await requestRefundApi({
          payment_id: selectedPayment.value.id,
          amount: refundForm.amount,
          reason: refundForm.reason
        });
        
        alert('退款申请已提交，请等待审核');
        closeRefundDialog();
        fetchPaymentHistory();
      } catch (err) {
        console.error('申请退款失败:', err);
        alert('申请退款失败，请稍后重试');
      } finally {
        submittingRefund.value = false;
      }
    };
    
    // 打开详情对话框
    const viewDetails = async (paymentId) => {
      try {
        const paymentDetails = await getPaymentDetails(paymentId);
        selectedPayment.value = paymentDetails;
        showDetailsDialog.value = true;
      } catch (err) {
        console.error('获取支付详情失败:', err);
        alert('获取支付详情失败，请稍后重试');
      }
    };
    
    // 关闭详情对话框
    const closeDetailsDialog = () => {
      showDetailsDialog.value = false;
      selectedPayment.value = null;
    };
    
    onMounted(() => {
      fetchPaymentHistory();
    });
    
    return {
      payments,
      loading,
      error,
      currentPage,
      totalPages,
      pageSize,
      today,
      filters,
      visiblePages,
      showRefundDialog,
      showDetailsDialog,
      selectedPayment,
      submittingRefund,
      exporting,
      refundForm,
      fetchPaymentHistory,
      changePage,
      resetFilters,
      formatDate,
      formatCurrency,
      getStatusText,
      getMethodText,
      continuePayment,
      cancelPayment,
      openRefundDialog,
      closeRefundDialog,
      submitRefund,
      viewDetails,
      closeDetailsDialog,
      exportHistory
    };
  }
};
</script>

<style scoped>
.payment-history {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
  color: #333;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.filters-section {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  min-width: 150px;
}

.filter-group label {
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.filter-group select,
.filter-group input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.date-range-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-range-inputs span {
  color: #666;
}

.filter-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.payment-list {
  margin-bottom: 30px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 20px;
  margin-bottom: 10px;
  color: #333;
}

.empty-state p {
  color: #666;
  margin-bottom: 20px;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.payment-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.payment-card {
  background-color: #fff;
  border: 1px solid #eaeaea;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.3s;
}

.payment-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.payment-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.payment-info h3 {
  font-size: 18px;
  margin-bottom: 5px;
  color: #333;
}

.payment-date {
  color: #666;
  font-size: 14px;
}

.payment-amount {
  text-align: right;
}

.amount {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 5px;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.pending {
  background-color: #fff3cd;
  color: #856404;
}

.status-badge.completed {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.failed {
  background-color: #f8d7da;
  color: #721c24;
}

.status-badge.refunded {
  background-color: #e2e3e5;
  color: #383d41;
}

.status-badge.cancelled {
  background-color: #e2e3e5;
  color: #383d41;
}

.payment-details {
  margin-bottom: 15px;
}

.detail-row {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;
}

.detail-row .label {
  width: 80px;
  color: #666;
  flex-shrink: 0;
}

.detail-row .value {
  color: #333;
  word-break: break-all;
}

.payment-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  text-align: center;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 30px;
}

.pagination-btn {
  padding: 8px 12px;
  border: 1px solid #ddd;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background-color: #f8f9fa;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-btn.active {
  background-color: #3498db;
  color: white;
  border-color: #3498db;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group small {
  display: block;
  margin-top: 5px;
  color: #666;
  font-size: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #eee;
}

.detail-section {
  margin-bottom: 25px;
}

.detail-section h4 {
  margin-bottom: 15px;
  font-size: 16px;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
  text-align: center;
}

.btn-primary {
  background-color: #3498db;
  color: white;
}

.btn-primary:hover {
  background-color: #2980b9;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #5a6268;
}

.btn-outline {
  background-color: transparent;
  color: #3498db;
  border: 1px solid #3498db;
}

.btn-outline:hover {
  background-color: #3498db;
  color: white;
}

.btn-outline-danger {
  background-color: transparent;
  color: #dc3545;
  border: 1px solid #dc3545;
}

.btn-outline-danger:hover {
  background-color: #dc3545;
  color: white;
}

@media (max-width: 768px) {
  .payment-history {
    padding: 15px;
  }
  
  .filters-section {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-actions {
    margin-left: 0;
    justify-content: center;
  }
  
  .payment-cards {
    grid-template-columns: 1fr;
  }
  
  .payment-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .payment-amount {
    text-align: left;
    margin-top: 10px;
  }
}
</style>