<template>
  <div class="payment-confirmation">
    <div v-if="loading" class="loading">
      处理中...
    </div>
    
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    
    <div v-else class="confirmation-content">
      <h2>付款确认</h2>
      
      <div class="payment-details">
        <div class="detail-row">
          <span class="label">会员ID:</span>
          <span class="value">{{ paymentDetails.member_id }}</span>
        </div>
        
        <div class="detail-row">
          <span class="label">金额:</span>
          <span class="value">¥{{ paymentDetails.amount }}</span>
        </div>
        
        <div class="detail-row">
          <span class="label">支付方式:</span>
          <span class="value">{{ paymentDetails.payment_method }}</span>
        </div>
        
        <div class="detail-row">
          <span class="label">支付日期:</span>
          <span class="value">{{ formattedDate }}</span>
        </div>
      </div>
      
      <div class="actions">
        <button @click="confirmPayment" class="confirm-btn">确认支付</button>
        <button @click="cancelPayment" class="cancel-btn">取消</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { createPayment } from '../api/payments';

export default {
  name: 'PaymentConfirmation',
  
  props: {
    memberId: {
      type: Number,
      required: true
    },
    amount: {
      type: Number,
      required: true
    },
    paymentMethod: {
      type: String,
      required: true
    }
  },
  
  setup(props) {
    const router = useRouter();
    const loading = ref(false);
    const error = ref(null);
    const paymentDetails = ref({
      member_id: props.memberId,
      amount: props.amount,
      payment_method: props.paymentMethod,
      payment_date: new Date().toISOString()
    });
    
    const formattedDate = computed(() => {
      return new Date(paymentDetails.value.payment_date).toLocaleString();
    });
    
    const confirmPayment = async () => {
      loading.value = true;
      error.value = null;
      
      try {
        await createPayment(paymentDetails.value);
        router.push({ name: 'PaymentSuccess' });
      } catch (err) {
        error.value = '支付失败: ' + (err.response?.data?.message || err.message);
      } finally {
        loading.value = false;
      }
    };
    
    const cancelPayment = () => {
      router.go(-1);
    };
    
    return {
      loading,
      error,
      paymentDetails,
      formattedDate,
      confirmPayment,
      cancelPayment
    };
  }
};
</script>

<style scoped>
.payment-confirmation {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.loading, .error {
  text-align: center;
  padding: 20px;
}

.error {
  color: #ff4444;
}

.confirmation-content h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.payment-details {
  margin-bottom: 30px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.label {
  font-weight: bold;
  color: #666;
}

.value {
  color: #333;
}

.actions {
  display: flex;
  justify-content: space-between;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.confirm-btn {
  background-color: #4CAF50;
  color: white;
}

.confirm-btn:hover {
  background-color: #45a049;
}

.cancel-btn {
  background-color: #f44336;
  color: white;
}

.cancel-btn:hover {
  background-color: #d32f2f;
}
</style>