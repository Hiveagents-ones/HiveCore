<template>
  <div class="payment-history-container">
    <h1>{{ t('paymentHistory.title') }}</h1>
    <el-alert
      title="提示"
      type="info"
      :description="t('paymentHistory.tip')"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />
    
    <div class="filter-section">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item :label="t('paymentHistory.memberId')">
        <el-form-item :label="t('paymentHistory.paymentMethod')">
        <el-form-item :label="t('paymentHistory.invoiceStatus')">
          <el-select v-model="filterForm.invoice_status" :placeholder="t('paymentHistory.invoiceStatusPlaceholder')" clearable>
            <el-option label="已开票" value="issued"></el-option>
            <el-option label="未开票" value="not_issued"></el-option>
          </el-select>
        </el-form-item>
          <el-select v-model="filterForm.payment_method" :placeholder="t('paymentHistory.paymentMethodPlaceholder')" clearable>
            <el-option label="微信支付" value="wechat"></el-option>
            <el-option label="支付宝" value="alipay"></el-option>
            <el-option label="银行卡" value="bank"></el-option>
            <el-option label="现金" value="cash"></el-option>
          </el-select>
        </el-form-item>
          <el-input v-model="filterForm.member_id" :placeholder="t('paymentHistory.memberIdPlaceholder')" clearable></el-input>
        </el-form-item>
        
        <el-form-item :label="t('paymentHistory.dateRange')">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            :start-placeholder="t('paymentHistory.startDate')"
            :end-placeholder="t('paymentHistory.endDate')"
            value-format="yyyy-MM-dd"
            @change="handleDateChange">
          </el-date-picker>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="fetchPayments">{{ t('common.search') }}</el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <div class="payment-table">
      <el-table :data="payments" border style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="支付ID" width="100"></el-table-column>
        <el-table-column prop="member_id" label="会员ID" width="100"></el-table-column>
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">
            ¥{{ row.amount.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="120">
          <template #default="{ row }">
            {{ formatPaymentMethod(row.payment_method) }}
          </template>
        </el-table-column>
        <el-table-column prop="payment_date" label="支付日期" width="180"></el-table-column>
        <el-table-column prop="invoice_status" label="发票状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.invoice_status === 'issued' ? 'success' : 'info'">
              {{ row.invoice_status === 'issued' ? '已开票' : '未开票' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row)">详情</el-button>
            <el-button size="small" type="success" @click="generateInvoice(row.id)">发票</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <div class="pagination">
      <el-pagination
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :current-page="currentPage"
        :page-sizes="[10, 20, 50, 100]"
        :page-size="pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total">
      </el-pagination>
    </div>
    
    <el-dialog v-model="detailVisible" title="支付详情" width="50%">
      <div v-if="currentPayment">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="支付ID">{{ currentPayment.id }}</el-descriptions-item>
          <el-descriptions-item label="会员ID">{{ currentPayment.member_id }}</el-descriptions-item>
          <el-descriptions-item label="金额">¥{{ currentPayment.amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ currentPayment.payment_method }}</el-descriptions-item>
          <el-descriptions-item label="支付日期">{{ currentPayment.payment_date }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ currentPayment.notes || '无' }}</el-descriptions-item>
          <el-descriptions-item label="发票状态">
            <el-tag :type="currentPayment.invoice_status === 'issued' ? 'success' : 'info'">
              {{ formatInvoiceStatus(currentPayment.invoice_status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import paymentApi from '../api/payment';
import { downloadFile } from '../utils/file';

export default {
  setup() {
    const payments = ref([]);
    const loading = ref(false);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);
    const filterForm = ref({
      member_id: '',
      start_date: '',
      end_date: '',
      payment_method: '',
      invoice_status: ''
    });
    const dateRange = ref([]);
    const detailVisible = ref(false);
    const currentPayment = ref(null);

    const { t } = useI18n();

const fetchPayments = async () => {
      try {
        loading.value = true;
        const params = {
          ...filterForm.value,
          page: currentPage.value,
          limit: pageSize.value
        };
        
        const response = await paymentApi.getPayments(params);
        payments.value = response.data.data;
        total.value = response.data.total;
      } catch (error) {
        ElMessage.error('获取支付记录失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    const handleSizeChange = (val) => {
      pageSize.value = val;
      fetchPayments();
    };

    const handleCurrentChange = (val) => {
      currentPage.value = val;
      fetchPayments();
    };

    const handleDateChange = (val) => {
      if (val && val.length === 2) {
        filterForm.value.start_date = val[0];
        filterForm.value.end_date = val[1];
      } else {
        filterForm.value.start_date = '';
        filterForm.value.end_date = '';
      }
    };

    const showDetail = async (payment) => {
      try {
        const response = await paymentApi.getPaymentDetail(payment.id);
        currentPayment.value = response.data;
        detailVisible.value = true;
      } catch (error) {
        ElMessage.error('获取支付详情失败: ' + error.message);
      }
    };

    const generateInvoice = async (paymentId) => {
      try {
        loading.value = true;
        const response = await paymentApi.getInvoice(paymentId);
        downloadFile(response.data, `invoice_${paymentId}.pdf`);
        ElMessage.success(t('paymentHistory.invoiceDownloadSuccess'));
      } catch (error) {
        ElMessage.error(t('paymentHistory.invoiceDownloadError') + error.message);
      } finally {
        loading.value = false;
      }
      try {
        loading.value = true;
        const response = await paymentApi.getInvoice(paymentId);
        
        // 创建PDF下载链接
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `invoice_${paymentId}.pdf`);
        document.body.appendChild(link);
        link.click();
        
        ElMessage.success('发票下载成功');
      } catch (error) {
        ElMessage.error('生成发票失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      fetchPayments();
    });

    const formatPaymentMethod = (method) => {

    
    const formatInvoiceStatus = (status) => {
      const statusMap = {
        'issued': t('paymentHistory.invoiceStatusIssued'),
        'not_issued': t('paymentHistory.invoiceStatusNotIssued')
      };
      return statusMap[status] || status;
    };
      const methods = {
        'wechat': '微信支付',
        'alipay': '支付宝',
        'bank': '银行卡',
        'cash': '现金'
      };
      return methods[method] || method;
    };
    return {
      payments,
      loading,
      currentPage,
      pageSize,
      total,
      filterForm,
      dateRange,
      detailVisible,
      currentPayment,
      fetchPayments,
      handleSizeChange,
      handleCurrentChange,
      handleDateChange,
      showDetail,
      generateInvoice
    };
  }
};
</script>

<style scoped>
.payment-history-container {
  padding: 20px;
}

.filter-section {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  align-items: center;
}

.payment-table {
  margin-bottom: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    const formatPaymentMethod = (method) => {
      const methods = {
        'wechat': t('paymentHistory.paymentMethodWechat'),
        'alipay': t('paymentHistory.paymentMethodAlipay'),
        'bank': t('paymentHistory.paymentMethodBank'),
        'cash': t('paymentHistory.paymentMethodCash')
      };
      return methods[method] || method;
    };

    const formatInvoiceStatus = (status) => {
      const statusMap = {
        'issued': t('paymentHistory.invoiceStatusIssued'),
        'not_issued': t('paymentHistory.invoiceStatusNotIssued')
      };
      return statusMap[status] || status;
    };