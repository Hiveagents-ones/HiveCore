<template>
  <div class="payment-view">
    <h1>{{ t('payment.title') }}</h1>
    
    <div class="payment-form">
      <el-form :model="paymentForm" label-width="120px" ref="paymentFormRef">
        <el-form-item :label="t('payment.memberId')" prop="member_id" required>
          <el-input-number v-model="paymentForm.member_id" :min="1" />
        </el-form-item>
        
        <el-form-item :label="t('payment.amount')" prop="amount" required>
          <el-input-number v-model="paymentForm.amount" :min="0" :precision="2" />
        </el-form-item>
        
        <el-form-item :label="t('payment.method')" prop="payment_method" required>
          <el-select v-model="paymentForm.payment_method" placeholder="请选择支付方式">
            <el-option :label="t('payment.methods.wechat')" value="wechat" />
            <el-option :label="t('payment.methods.alipay')" value="alipay" />
            <el-option :label="t('payment.methods.cash')" value="cash" />
            <el-option :label="t('payment.methods.bankCard')" value="bank_card" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitPayment">{{ t('payment.submit') }}</el-button>
          <el-button @click="resetForm">{{ t('payment.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <div class="payment-history">
      <h2>{{ t('payment.history') }}</h2>
      <el-table :data="paymentHistory" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" :label="t('payment.table.id')" width="100" />
        <el-table-column prop="member_id" :label="t('payment.table.memberId')" width="100" />
        <el-table-column prop="amount" :label="t('payment.table.amount')" width="120" :formatter="formatAmount" />
        <el-table-column prop="payment_method" :label="t('payment.table.method')" width="120" :formatter="formatMethod" />
        <el-table-column prop="payment_date" :label="t('payment.table.date')" width="180" />
      </el-table>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import paymentApi from '@/api/payments';

export default {
  name: 'PaymentView',
  setup() {
    const { t } = useI18n();
    const formatAmount = (row) => {
      return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY',
        minimumFractionDigits: 2
      }).format(row.amount);
    };
    
    const formatMethod = (row) => {
      if (!row.payment_method) return '';
      return t(`payment.methods.${row.payment_method}`);
    };
    const paymentForm = ref({
      member_id: null,
      amount: null,
      payment_method: null
    });
    
    const paymentFormRef = ref(null);
    const paymentHistory = ref([]);
    const loading = ref(false);
    
    const fetchPaymentHistory = async () => {
      try {
        loading.value = true;
        const response = await paymentApi.getAllPayments();
        paymentHistory.value = response.data;
      } catch (error) {
        ElMessage.error(t('payment.errors.fetchFailed') + error.message);
      } finally {
        loading.value = false;
      }
    };
    
    const submitPayment = async () => {
      try {
        await paymentFormRef.value.validate();
        await paymentApi.createPayment(paymentForm.value);
        ElMessage.success(t('payment.success'));
        resetForm();
        fetchPaymentHistory();
      } catch (error) {
        if (error.message !== 'validate') {
          ElMessage.error(t('payment.errors.submitFailed') + error.message);
        }
      }
    };
    
    const resetForm = () => {
      paymentFormRef.value.resetFields();
    };
    
    onMounted(() => {
      fetchPaymentHistory();
    });
    
    return {
      t,
      paymentForm,
      paymentFormRef,
      paymentHistory,
      loading,
      submitPayment,
      resetForm,
      formatAmount,
      formatMethod
    };
  }
};
</script>

<style scoped>
.payment-view {
  padding: 20px;
}

.payment-form {
  margin-bottom: 30px;
  max-width: 600px;
}

.payment-history {
  margin-top: 30px;
}
</style>