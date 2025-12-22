<template>
  <div class="refund-approval">
    <h2>退款审批</h2>
    
    <div v-if="loading" class="loading">
      加载中...
    </div>
    
    <div v-else>
      <div class="refund-list">
        <div v-for="payment in pendingRefunds" :key="payment.id" class="refund-item">
          <div class="payment-info">
            <p><strong>支付ID:</strong> {{ payment.id }}</p>
            <p><strong>会员ID:</strong> {{ payment.memberId }}</p>
            <p><strong>类型:</strong> {{ payment.type === 'membership' ? '会员费' : '课程费' }}</p>
            <p><strong>金额:</strong> ¥{{ payment.amount }}</p>
            <p><strong>支付时间:</strong> {{ new Date(payment.createdAt).toLocaleString() }}</p>
            <p><strong>退款原因:</strong> {{ payment.refundReason || '无' }}</p>
            <p><strong>关联ID:</strong> {{ payment.referenceId || '无' }}</p>
          </div>
          
          <div class="action-buttons">
            <button @click="approveRefund(payment.id)" class="btn approve">批准</button>
            <button @click="rejectRefund(payment.id)" class="btn reject">拒绝</button>
          </div>
        </div>
      </div>
      
      <div v-if="pendingRefunds.length === 0" class="no-refunds">
        当前没有待处理的退款申请
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { usePaymentApi } from '../api/payments';
import { useMemberApi } from '../api/members';
import { useAuthStore } from '../stores/auth';
import { useToast } from 'vue-toastification';
import { useRouter } from 'vue-router';

export default {
  name: 'RefundApproval',
  
  setup() {
    const paymentApi = usePaymentApi();
    const authStore = useAuthStore();
    const toast = useToast();
const router = useRouter();
    
    const pendingRefunds = ref([]);
    const loading = ref(true);
    
    const fetchPendingRefunds = async () => {
      try {
        loading.value = true;
        const payments = await paymentApi.getPayments({ status: 'refund_requested', staffId: authStore.user.id });
        pendingRefunds.value = payments;
      } catch (error) {
        toast.error('获取待处理退款失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };
    
    const approveRefund = async (paymentId) => {
      try {
        await paymentApi.updatePayment(paymentId, { status: 'refunded' });
        toast.success('退款已批准');
        fetchPendingRefunds();
        router.push({ name: 'PaymentList' });
      } catch (error) {
        toast.error('批准退款失败: ' + error.message);
      }
    };
    
    const rejectRefund = async (paymentId) => {
      try {
        await paymentApi.updatePayment(paymentId, { status: 'completed' });
        toast.success('退款已拒绝');
        fetchPendingRefunds();
        router.push({ name: 'PaymentList' });
      } catch (error) {
        toast.error('拒绝退款失败: ' + error.message);
      }
    };
    
    onMounted(() => {
      fetchPendingRefunds();
    });
    
    return {
      pendingRefunds,
      loading,
      approveRefund,
      rejectRefund
    };
  }
};
</script>

<style scoped>
.refund-approval {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.loading {
  text-align: center;
  padding: 20px;
}

.refund-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.refund-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.payment-info {
  flex: 1;
}

.payment-info p {
  margin: 5px 0;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.approve {
  background-color: #4CAF50;
  color: white;
}

.reject {
  background-color: #f44336;
  color: white;
}

.no-refunds {
  text-align: center;
  padding: 20px;
  color: #666;
}
</style>