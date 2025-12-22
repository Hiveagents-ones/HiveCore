<template>
  <div class="payment-management">
    <h1>支付管理</h1>
    <div class="search-bar">
      <el-form :inline="true">
        <el-form-item label="关键字">
          <el-input 
            v-model="searchQuery" 
            placeholder="搜索支付记录/会员/订单号" 
            style="width: 200px" 
            clearable
            @keyup.enter="handleSearchPayments"
          />
        </el-form-item>
        <el-form-item label="日期范围">
        <el-form-item label="支付状态">
        <el-form-item label="支付方式">
        <el-form-item label="会员ID">
          <el-input v-model="memberId" placeholder="会员ID" style="width: 120px" clearable />
        </el-form-item>
          <el-select v-model="paymentMethod" placeholder="全部方式" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="银行卡" value="bank" />
            <el-option label="现金" value="cash" />
          </el-select>
        </el-form-item>
          <el-select v-model="paymentStatus" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="处理中" value="processing" />
            <el-option label="已退款" value="refunded" />
          </el-select>
        </el-form-item>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 250px"
          />
        </el-form-item>
        <el-form-item>
          <el-button 
            type="primary"
            :loading="searchLoading" 
            @click="handleSearchPayments"
          >
            <el-icon><search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleResetSearch">
          <el-button @click="showAdvancedSearch = !showAdvancedSearch">
            <el-icon><filter /></el-icon> 高级搜索
          </el-button>
            <el-icon><refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    <el-collapse-transition>
      <div v-show="showAdvancedSearch" class="advanced-search">
        <el-form :inline="true">
          <el-form-item label="最小金额">
            <el-input-number v-model="minAmount" :precision="2" :controls="false" style="width: 120px" />
          </el-form-item>
          <el-form-item label="最大金额">
            <el-input-number v-model="maxAmount" :precision="2" :controls="false" style="width: 120px" />
          </el-form-item>
          <el-form-item label="订单号">
            <el-input v-model="orderNumber" placeholder="订单号" style="width: 200px" clearable />
          </el-form-item>
        </el-form>
      </div>
    </el-collapse-transition>
    </div>
    
    <div class="payment-tabs">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="支付记录" name="payments">
          <PaymentList 
            :payments="payments" 
            :loading="loading" 
            @refresh="fetchPayments" 
            @refund="handleRefundPayment"
            @search="handleSearchPayments"
            @create="showCreateDialog"
          />
        </el-tab-pane>
        
        <el-tab-pane label="发票管理" name="invoices">
          <InvoiceList 
            :invoices="invoices" 
            :loading="loading" 
            @refresh="fetchInvoices" 
            @generate="showGenerateDialog"
            @download="handleDownloadInvoice"

          />
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- 创建支付对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建支付记录" width="50%">
      <PaymentForm 
        @submit="handleCreatePayment" 
        @cancel="createDialogVisible = false"
      />
    </el-dialog>
    
    <!-- 生成发票对话框 -->
    <el-dialog v-model="generateDialogVisible" title="生成发票" width="50%">
      <InvoiceForm 
        @submit="handleGenerateInvoice" 
        @cancel="generateDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Search, Refresh } from '@element-plus/icons-vue';
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue';
import PaymentList from '@/components/payment/PaymentList.vue';
import InvoiceList from '@/components/payment/InvoiceList.vue';
import PaymentForm from '@/components/payment/PaymentForm.vue';
import InvoiceForm from '@/components/payment/InvoiceForm.vue';
import { createPayment, getPayments, requestRefund, generateInvoice, getInvoices } from '@/api/payments';
import { downloadInvoice } from '@/api/payments';
import { searchPayments } from '@/api/payments';

export default {
  name: 'PaymentManagement',
  components: {
    PaymentList,
    InvoiceList,
    PaymentForm,
    InvoiceForm
  },
  setup() {
    const activeTab = ref('payments');
    const payments = ref([]);
    const invoices = ref([]);
    const loading = ref(false);
    const createDialogVisible = ref(false);
    const generateDialogVisible = ref(false);

    const searchQuery = ref('');
    const searchLoading = ref(false);
    const dateRange = ref([]);
    const paymentStatus = ref('');
    const paymentMethod = ref('');
    const showAdvancedSearch = ref(false);
    const minAmount = ref(null);
    const maxAmount = ref(null);
    const orderNumber = ref('');
    const memberId = ref('');
    const pagination = ref({
      currentPage: 1,
      pageSize: 10,
      total: 0
    });

    const fetchPayments = async () => {
      try {
        loading.value = true;
        const response = await getPayments();
        payments.value = response.data;
      } catch (error) {
        ElMessage.error('获取支付记录失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    const fetchInvoices = async () => {
      try {
        loading.value = true;
        const response = await getInvoices();
        invoices.value = response.data;
      } catch (error) {
        ElMessage.error('获取发票记录失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    const handleCreatePayment = async (paymentData) => {
      try {
        await createPayment(paymentData);
        ElMessage.success('支付记录创建成功');
        createDialogVisible.value = false;
        await fetchPayments();
      } catch (error) {
        ElMessage.error('创建支付记录失败: ' + error.message);
      }
    };

    const handleGenerateInvoice = async (invoiceData) => {
    const handleRefundPayment = async (paymentId) => {
      try {
        await requestRefund(paymentId);
        ElMessage.success('退款请求已提交');
        await fetchPayments();
      } catch (error) {
        ElMessage.error('提交退款请求失败: ' + error.message);
      }
    };
      try {
        await generateInvoice(invoiceData);
        ElMessage.success('发票生成成功');
        generateDialogVisible.value = false;
        await fetchInvoices();
      } catch (error) {
        ElMessage.error('生成发票失败: ' + error.message);
      }
    };

    const showCreateDialog = () => {
      createDialogVisible.value = true;
    };

    const showGenerateDialog = () => {
  generateDialogVisible.value = true;
};

const handleDownloadInvoice = async (invoiceId) => {


const handleResetSearch = async () => {
      minAmount.value = null;
      maxAmount.value = null;
      orderNumber.value = '';
      memberId.value = '';
      searchQuery.value = '';
      dateRange.value = [];
      paymentStatus.value = '';
      paymentMethod.value = '';
      pagination.value.currentPage = 1;
      await fetchPayments();
    };
    const searchQuery = ref('');
    const searchLoading = ref(false);
    
    const handleSearchPayments = async () => {
      try {
        searchLoading.value = true;
        const params = {
          query: searchQuery.value,
          start_date: dateRange.value?.[0],
          end_date: dateRange.value?.[1],
          status: paymentStatus.value,
          method: paymentMethod.value,
          min_amount: minAmount.value,
          max_amount: maxAmount.value,
          order_number: orderNumber.value,
          member_id: memberId.value,
          page: pagination.value.currentPage,
          page_size: pagination.value.pageSize
        };
        const response = await searchPayments(params);
        payments.value = response.data.items;
        pagination.value.total = response.data.total;
      } catch (error) {
        ElMessage.error('搜索支付记录失败: ' + error.message);
      } finally {
        searchLoading.value = false;
      }
    };
  try {
    const response = await downloadInvoice(invoiceId);
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `invoice_${invoiceId}.pdf`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    ElMessage.error('下载发票失败: ' + error.message);
  }
};

    onMounted(() => {
      fetchPayments();
      fetchInvoices();
    });

    return {
      paymentStatus,
      pagination,
      activeTab,
      payments,
      invoices,
      loading,
      createDialogVisible,
      generateDialogVisible,
      fetchPayments,
      fetchInvoices,
      handleCreatePayment,
      handleGenerateInvoice,
      showCreateDialog,
      showGenerateDialog,
      handleDownloadInvoice,
      handleRefundPayment
,
      searchQuery,
      searchLoading,
      dateRange,
      handleResetSearch,
      memberId,
      showAdvancedSearch,
      handleSearchPayments
    };
  }
};
</script>

<style scoped>
.payment-management {
  padding: 20px;
}

.payment-tabs {
  .search-bar {
    margin-bottom: 20px;
    background: #f5f7fa;
    padding: 20px;
    border-radius: 4px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  
  .search-bar .el-form {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  
  .search-bar .el-form-item {
    margin-bottom: 0;
  }
  margin-top: 20px;
  .advanced-search {
    background: #f8f8f8;
    padding: 15px;
    margin-top: 10px;
    border-radius: 4px;
  }
  
  .advanced-search .el-form {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
}
</style>