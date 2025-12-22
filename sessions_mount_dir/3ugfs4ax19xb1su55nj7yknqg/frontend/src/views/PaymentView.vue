<template>
  <div class="payment-view">
    <h1>收费管理</h1>
    
    <div class="payment-actions">
      <el-button type="primary" @click="showPaymentForm = true">
        新增收费记录
      </el-button>
    </div>
    
    <el-dialog v-model="showPaymentForm" title="新增收费记录" width="50%">
      <PaymentForm 
        @submit="handlePaymentSubmit" 
        @cancel="showPaymentForm = false" 
      />
    </el-dialog>
    
    <el-table :data="payments" style="width: 100%" border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="member_id" label="会员ID" width="100" />
      <el-table-column prop="amount" label="金额" width="120" />
      <el-table-column prop="payment_type" label="支付类型" width="150" />
      <el-table-column prop="payment_date" label="支付日期" width="180" />
    </el-table>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElButton, ElDialog, ElTable, ElTableColumn } from 'element-plus';
import PaymentForm from '@/components/PaymentForm.vue';
import { getPayments, createPayment } from '@/api/payments.js';

export default {
  name: 'PaymentView',
  components: {
    ElButton,
    ElDialog,
    ElTable,
    ElTableColumn,
    PaymentForm
  },
  setup() {
    const payments = ref([]);
    const showPaymentForm = ref(false);

    const fetchPayments = async () => {
      try {
        const data = await getPayments();
        payments.value = data;
      } catch (error) {
        console.error('Failed to fetch payments:', error);
      }
    };

    const handlePaymentSubmit = async (paymentData) => {
      try {
        await createPayment(paymentData);
        showPaymentForm.value = false;
        await fetchPayments();
      } catch (error) {
        console.error('Failed to create payment:', error);
      }
    };

    onMounted(() => {
      fetchPayments();
    });

    return {
      payments,
      showPaymentForm,
      handlePaymentSubmit
    };
  }
};
</script>

<style scoped>
.payment-view {
  padding: 20px;
}

.payment-actions {
  margin-bottom: 20px;
}
</style>