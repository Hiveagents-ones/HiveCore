<template>
  <div class="payment-monitoring">
    <h2>结算监控</h2>
    
    <div class="filters">
      <el-input
        v-model="searchQuery"
        placeholder="搜索会员ID或支付方式"
        style="width: 300px"
        clearable
        @clear="handleSearchClear"
        @keyup.enter="fetchPayments"
      />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="handleDateChange"
      />
      <el-button type="primary" @click="fetchPayments">查询</el-button>
    </div>
    
    <el-table
      :data="filteredPayments"
      border
      style="width: 100%"
      v-loading="loading"
    >
      <el-table-column prop="id" label="支付ID" width="100" />
      <el-table-column prop="member_id" label="会员ID" width="100" />
      <el-table-column prop="member_name" label="会员姓名" width="120" />
      <el-table-column prop="amount" label="金额" width="120" />
      <el-table-column prop="payment_method" label="支付方式" width="150" />
      <el-table-column prop="payment_date" label="支付日期" width="180" />
      <el-table-column label="操作" width="120">
        <template #default="scope">
          <el-button
            size="small"
            @click="handleDetail(scope.row)"
          >详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      :current-page="currentPage"
      :page-size="pageSize"
      :total="totalPayments"
      @current-change="handlePageChange"
      layout="total, prev, pager, next"
    />
    
    <el-dialog
      v-model="detailDialogVisible"
      title="支付详情"
      width="50%"
    >
      <div v-if="currentPayment">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="支付ID">{{ currentPayment.id }}</el-descriptions-item>
          <el-descriptions-item label="会员ID">{{ currentPayment.member_id }}</el-descriptions-item>
          <el-descriptions-item label="会员姓名">{{ currentPayment.member_name }}</el-descriptions-item>
          <el-descriptions-item label="金额">{{ currentPayment.amount }}</el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ currentPayment.payment_method }}</el-descriptions-item>
          <el-descriptions-item label="支付日期">{{ formatDate(currentPayment.payment_date) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useMemberStore } from '../stores/member';
import paymentsApi from '../api/payments';
import { ElMessage } from 'element-plus';

export default {
  name: 'PaymentMonitoring',
  
  setup() {
    const payments = ref([]);
    const filteredPayments = ref([]);
    const loading = ref(false);
    const searchQuery = ref('');
    const dateRange = ref([]);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const totalPayments = ref(0);
    const detailDialogVisible = ref(false);
    const currentPayment = ref(null);
    
    const memberStore = useMemberStore();

    const fetchPayments = async () => {
      try {
        loading.value = true;
        const response = await paymentsApi.getAllPayments();
        payments.value = response.data.map(payment => {
          const member = memberStore.getMemberById(payment.member_id);
          return {
            ...payment,
            member_name: member ? member.name : '未知会员'
          };
        });
        totalPayments.value = payments.value.length;
        applyFilters();
      } catch (error) {
        ElMessage.error(error.message);
      } finally {
        loading.value = false;
      }
    };
    
    const applyFilters = async () => {
      await memberStore.fetchMembers();
      let result = [...payments.value];
      
      // 搜索过滤
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase();
        result = result.filter(payment => 
          payment.member_id.toString().includes(query) || 
          payment.payment_method.toLowerCase().includes(query)
        );
      }
      
      // 日期过滤
      if (dateRange.value && dateRange.value.length === 2) {
        const [startDate, endDate] = dateRange.value;
        result = result.filter(payment => {
          const paymentDate = new Date(payment.payment_date);
          return paymentDate >= new Date(startDate) && 
                 paymentDate <= new Date(endDate);
        });
      }
      
      // 分页
      const start = (currentPage.value - 1) * pageSize.value;
      const end = start + pageSize.value;
      filteredPayments.value = result.slice(start, end);
      totalPayments.value = result.length;
    };
    
    const handleSearchClear = () => {
      searchQuery.value = '';
      fetchPayments();
    };
    
    const handleDateChange = () => {
      currentPage.value = 1;
      applyFilters();
    };
    
    const handlePageChange = (page) => {
      currentPage.value = page;
      applyFilters();
    };
    
    const handleDetail = (payment) => {
      currentPayment.value = payment;
      detailDialogVisible.value = true;
    };
    
    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleString();
    };
    
    onMounted(() => {
      fetchPayments();
    });
    
    return {
      payments,
      filteredPayments,
      loading,
      searchQuery,
      dateRange,
      currentPage,
      pageSize,
      totalPayments,
      detailDialogVisible,
      currentPayment,
      fetchPayments,
      handleSearchClear,
      handleDateChange,
      handlePageChange,
      handleDetail,
      formatDate
    };
  }
};
</script>

<style scoped>
.payment-monitoring {
  padding: 20px;
}

.filters {
  margin-bottom: 20px;
  display: flex;
  gap: 15px;
  align-items: center;
}

.el-pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
</style>