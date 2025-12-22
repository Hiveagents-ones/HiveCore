<template>
  <div class="payment-form">
    <h2>支付表单</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="memberId">会员ID</label>
        <input 
          type="text" 
          id="memberId" 
          v-model="formData.member_id" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="amount">金额</label>
        <input 
          type="number" 
          id="amount" 
          v-model="formData.amount" 
          min="0" 
          step="0.01" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="paymentType">支付类型</label>
        <select 
          id="paymentType" 
          v-model="formData.payment_type" 
          required
        >
          <option value="membership">会员费</option>
          <option value="course">课程费</option>
          <option value="other">其他</option>
        </select>
      </div>
      
      <button type="submit" class="submit-btn">提交支付</button>
    </form>
    
    <div v-if="successMessage" class="success-message">
      {{ successMessage }}
    </div>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { usePaymentStore } from '../stores/payment';

export default {
  name: 'PaymentForm',
  setup() {
    const paymentStore = usePaymentStore();
    
    const formData = ref({
      member_id: '',
      amount: 0,
      payment_type: 'membership'
    });
    
    const successMessage = ref('');
    const errorMessage = ref('');
    
    const handleSubmit = async () => {
      try {
        await paymentStore.createPayment({
          member_id: formData.value.member_id,
          amount: parseFloat(formData.value.amount),
          payment_type: formData.value.payment_type
        });
        
        successMessage.value = '支付成功！';
        errorMessage.value = '';
        
        // 重置表单
        formData.value = {
          member_id: '',
          amount: 0,
          payment_type: 'membership'
        };
        
        setTimeout(() => {
          successMessage.value = '';
        }, 3000);
      } catch (error) {
        errorMessage.value = '支付失败: ' + error.message;
        setTimeout(() => {
          errorMessage.value = '';
        }, 3000);
      }
    };
    
    return {
      formData,
      successMessage,
      errorMessage,
      handleSubmit
    };
  }
};
</script>

<style scoped>
.payment-form {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

input, select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.submit-btn {
  width: 100%;
  padding: 10px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.submit-btn:hover {
  background-color: #45a049;
}

.success-message {
  margin-top: 15px;
  padding: 10px;
  background-color: #dff0d8;
  color: #3c763d;
  border-radius: 4px;
  text-align: center;
}

.error-message {
  margin-top: 15px;
  padding: 10px;
  background-color: #f2dede;
  color: #a94442;
  border-radius: 4px;
  text-align: center;
}
</style>