<template>
  <div class="payment-history-container">
    <!-- 即将到期提醒 -->
    <el-alert
      v-if="showRenewalReminder"
      title="会籍即将到期提醒"
      type="warning"
      :description="`您有 ${upcomingRenewals.length} 笔支付记录将在30天内到期，请及时续费。`"
      show-icon
      :closable="false"
      class="renewal-alert"
    />

    <el-card class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="支付状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable>
            <el-option label="成功" value="succeeded"></el-option>
            <el-option label="失败" value="failed"></el-option>
            <el-option label="处理中" value="processing"></el-option>
            <el-option label="已取消" value="canceled"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="filters.method" placeholder="全部方式" clearable>
            <el-option label="信用卡" value="credit_card"></el-option>
            <el-option label="支付宝" value="alipay"></el-option>
            <el-option label="微信支付" value="wechat"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="success" @click="handleExport" :loading="exporting">导出</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="paymentHistory"
        style="width: 100%"
        stripe
        border
      >
        <el-table-column prop="id" label="支付ID" width="120" />
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="scope">
            ¥{{ scope.row.amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="支付方式" width="120">
          <template #default="scope">
            {{ getMethodText(scope.row.method) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button
              size="small"
              type="primary"
              link
              @click="handleViewDetails(scope.row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 支付详情对话框 -->
    <el-dialog
      v-model="detailsVisible"
      title="支付详情"
      width="50%"
      destroy-on-close
    >
      <div v-if="selectedPayment" class="payment-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="支付ID">
            {{ selectedPayment.id }}
          </el-descriptions-item>
          <el-descriptions-item label="金额">
            ¥{{ selectedPayment.amount.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedPayment.status)">
              {{ getStatusText(selectedPayment.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="支付方式">
            {{ getMethodText(selectedPayment.method) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(selectedPayment.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(selectedPayment.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="交易ID" span="2">
            {{ selectedPayment.transaction_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" span="2">
            {{ selectedPayment.description || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { api } from '../api/index.js';

// 响应式数据
const loading = ref(false);
const exporting = ref(false);
const paymentHistory = ref([]);
const detailsVisible = ref(false);
const selectedPayment = ref(null);

// 筛选条件
const filters = reactive({
  status: '',
  method: '',
  dateRange: null
});

// 分页数据
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
});

// 获取支付历史
const fetchPaymentHistory = async () => {
  loading.value = true;
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      status: filters.status || undefined,
      method: filters.method || undefined,
      start_date: filters.dateRange?.[0] || undefined,
      end_date: filters.dateRange?.[1] || undefined
    };

    const response = await api.payment.getHistory(params);
    paymentHistory.value = response.data.items || [];
    pagination.total = response.data.total || 0;
  } catch (error) {
    console.error('获取支付历史失败:', error);
    ElMessage.error('获取支付历史失败');
  } finally {
    loading.value = false;
  }
};

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1;
  fetchPaymentHistory();
};

// 重置筛选条件
const handleReset = () => {
  filters.status = '';
  filters.method = '';
  filters.dateRange = null;
  pagination.currentPage = 1;
  fetchPaymentHistory();
};

// 导出支付历史
const handleExport = async () => {
  exporting.value = true;
  try {
    const params = {
      status: filters.status || undefined,
      method: filters.method || undefined,
      start_date: filters.dateRange?.[0] || undefined,
      end_date: filters.dateRange?.[1] || undefined
    };

    const response = await api.payment.export(params);
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `payment_history_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    ElMessage.success('导出成功');
  } catch (error) {
    console.error('导出失败:', error);
    ElMessage.error('导出失败');
  } finally {
    exporting.value = false;
  }
};

// 查看详情
const handleViewDetails = (payment) => {
  selectedPayment.value = payment;
  detailsVisible.value = true;
};

// 分页大小改变
const handleSizeChange = (size) => {
  pagination.pageSize = size;
  pagination.currentPage = 1;
  fetchPaymentHistory();
};

// 当前页改变
const handleCurrentChange = (page) => {
  pagination.currentPage = page;
  fetchPaymentHistory();
};

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    succeeded: 'success',
    failed: 'danger',
    processing: 'warning',
    canceled: 'info'
  };
  return statusMap[status] || 'info';
};

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    succeeded: '成功',
    failed: '失败',
    processing: '处理中',
    canceled: '已取消'
  };
  return statusMap[status] || status;
};

// 获取支付方式文本
const getMethodText = (method) => {
  const methodMap = {
    credit_card: '信用卡',
    alipay: '支付宝',
    wechat: '微信支付'
  };
  return methodMap[method] || method;
};

// 格式化日期
const formatDate = (dateString) => {
// 计算即将到期的支付记录
const upcomingRenewals = computed(() => {
  const today = new Date();
  const thirtyDaysLater = new Date();
  thirtyDaysLater.setDate(today.getDate() + 30);
  
  return paymentHistory.value.filter(payment => {
    if (payment.status !== 'succeeded') return false;
    const updatedAt = new Date(payment.updated_at);
    return updatedAt >= today && updatedAt <= thirtyDaysLater;
  });
});

// 显示即将到期提醒
const showRenewalReminder = computed(() => {
  return upcomingRenewals.value.length > 0;
});


  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// 组件挂载时获取数据
onMounted(() => {
  fetchPaymentHistory();
});
</script>

<style scoped>
.payment-history-container {
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

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.payment-details {

.renewal-alert {
  margin-bottom: 20px;
}
  padding: 20px;
}
</style>