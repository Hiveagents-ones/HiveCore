<template>
  <div class="payment-form">
    <h2 v-if="!paymentId">新增缴费记录</h2>
    <h2 v-else>编辑缴费记录</h2>
    
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="memberId">会员ID</label>
        <input 
          type="number" 
          id="memberId" 
          v-model="formData.member_id" 
          required
          min="1"
        />
      </div>
      
      <div class="form-group">
        <label for="amount">缴费金额</label>
        <input 
          type="number" 
          id="amount" 
          v-model="formData.amount" 
          required
          min="0"
          step="0.01"
        />
      </div>
      
      <div class="form-group">
        <label for="paymentMethod">支付方式</label>
        <select 
          id="paymentMethod" 
          v-model="formData.payment_method" 
          required
        >
          <option value="">请选择支付方式</option>
          <option value="现金">现金</option>
          <option value="微信">微信</option>
          <option value="支付宝">支付宝</option>
          <option value="银行卡">银行卡</option>
        </select>
      </div>
      
      <div class="form-actions">
        <button type="submit" class="submit-btn">
          {{ paymentId ? '更新' : '提交' }}
        </button>
        <button 
          type="button" 
          class="cancel-btn" 
          @click="$emit('cancel')"
          v-if="paymentId"
        >
          取消
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { createPayment, updatePayment, getPaymentById } from '../api/payments';
import { encryptData } from '../utils/crypto';

const props = defineProps({
  paymentId: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['success', 'cancel']);

const formData = ref({
  member_id: '',
  amount: '',
  payment_method: ''
});

const fetchPaymentDetails = async () => {
  if (props.paymentId) {
    try {
      const payment = await getPaymentById(props.paymentId);
      formData.value = {
        member_id: payment.member_id,
        amount: payment.amount,
        payment_method: payment.payment_method
      };
      
      // 验证获取的数据
      if (!formData.value.member_id || !formData.value.amount || !formData.value.payment_method) {
        throw new Error('获取的支付数据不完整');
      }
    } catch (error) {
      console.error('Error fetching payment details:', error);
      alert('获取支付详情时出错: ' + error.message);
    }
  }
};

const validateForm = () => {
  if (!formData.value.member_id || formData.value.member_id <= 0) {
    throw new Error('会员ID必须为正整数');
  }
  if (!formData.value.amount || formData.value.amount <= 0) {
    throw new Error('缴费金额必须大于0');
  }
  if (!formData.value.payment_method) {
    throw new Error('请选择支付方式');
  }
};

const handleSubmit = async () => {
  try {
    validateForm();
    
    const encryptedData = {
      ...formData.value,
      amount: encryptData(formData.value.amount.toString()),
      payment_method: encryptData(formData.value.payment_method)
    };
    
    if (props.paymentId) {
      await updatePayment(props.paymentId, encryptedData);
    } else {
      await createPayment(encryptedData);
    }
    emit('success');
  } catch (error) {
    console.error('Error submitting payment:', error);
    alert(error.message || '提交支付信息时出错');
  }
};

onMounted(() => {
  fetchPaymentDetails();
});
</script>

<style scoped>
.payment-form {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

input, select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.submit-btn {
  background-color: #4CAF50;
  color: white;
}

.submit-btn:hover {
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