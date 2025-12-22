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
      <el-table-column prop="description" label="描述" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElButton, ElDialog, ElTable, ElTableColumn } from 'element-plus';
import PaymentForm from '@/components/PaymentForm.vue';
import { getPayments, createPayment } from '@/api/payments.js';
import { usePaymentStore } from '@/stores/payment';

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
    const paymentStore = usePaymentStore();
    const payments = ref([]);
    const showPaymentForm = ref(false);

    const fetchPayments = async () => {
      try {
        await paymentStore.fetchPayments();
        payments.value = paymentStore.payments;
      } catch (error) {
        console.error('Failed to fetch payments:', error);
      }
    };

    const handlePaymentSubmit = async (paymentData) => {
    const handleEdit = (payment) => {
      // TODO: 实现编辑功能
      console.log('Edit payment:', payment);
    };

    const handleDelete = async (payment) => {
      try {
        await paymentStore.deletePayment(payment.id);
        await fetchPayments();
      } catch (error) {
        console.error('Failed to delete payment:', error);
      }
    };
      try {
        await paymentStore.createPayment(paymentData);
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
      handlePaymentSubmit,
      handleEdit,
      handleDelete
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