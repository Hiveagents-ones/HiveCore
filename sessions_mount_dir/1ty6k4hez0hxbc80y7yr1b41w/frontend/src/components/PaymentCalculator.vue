<template>
  <div class="payment-calculator">
    <h3>会员费用结算</h3>
    <div class="form-group">
      <label for="member-select">选择会员:</label>
      <select id="member-select" v-model="selectedMemberId" @change="fetchMemberDetails">
        <option value="" disabled>请选择会员</option>
        <option v-for="member in members" :key="member.id" :value="member.id">
          {{ member.name }} ({{ member.phone }})
        </option>
      </select>
    </div>

    <div v-if="selectedMember" class="member-details">
      <p>会员姓名: {{ selectedMember.name }}</p>
      <p>联系电话: {{ selectedMember.phone }}</p>
      <p>加入日期: {{ formatDate(selectedMember.join_date) }}</p>
    </div>

    <div class="form-group">
      <label for="amount">金额:</label>
      <input 
        id="amount" 
        type="number" 
        v-model="paymentAmount" 
        placeholder="请输入金额"
        min="0"
      />
    </div>

    <div class="form-group">
      <label>支付方式:</label>
      <div class="payment-methods">
        <label v-for="method in paymentMethods" :key="method.value">
          <input 
            type="radio" 
            v-model="paymentMethod" 
            :value="method.value"
          />
          {{ method.label }}
        </label>
      </div>
    </div>

    <button 
      class="submit-btn" 
      @click="submitPayment" 
      :disabled="!isFormValid"
    >
      确认支付
    </button>

    <div v-if="paymentSuccess" class="success-message">
      支付成功！
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getMembers, createPayment } from '../api/payments';

export default {
  name: 'PaymentCalculator',
  setup() {
    const members = ref([]);
    const selectedMemberId = ref('');
    const selectedMember = ref(null);
    const paymentAmount = ref(0);
    const paymentMethod = ref('cash');
    const paymentSuccess = ref(false);

    const paymentMethods = [
      { value: 'cash', label: '现金' },
      { value: 'card', label: '银行卡' },
      { value: 'wechat', label: '微信支付' },
      { value: 'alipay', label: '支付宝' },
    ];

    const isFormValid = ref(false);

    const fetchMembers = async () => {
      try {
        const response = await getMembers();
        members.value = response.data;
      } catch (error) {
        console.error('获取会员列表失败:', error);
      }
    };

    const fetchMemberDetails = async () => {
      if (!selectedMemberId.value) return;
      
      const member = members.value.find(m => m.id === selectedMemberId.value);
      if (member) {
        selectedMember.value = member;
      }
      validateForm();
    };

    const validateForm = () => {
      isFormValid.value = 
        selectedMemberId.value !== '' && 
        paymentAmount.value > 0 && 
        paymentMethod.value !== '';
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    };

    const submitPayment = async () => {
      if (!isFormValid.value) return;
      
      try {
        const paymentData = {
          member_id: selectedMemberId.value,
          amount: paymentAmount.value,
          payment_method: paymentMethod.value,
        };
        
        await createPayment(paymentData);
        paymentSuccess.value = true;
        
        // 重置表单
        setTimeout(() => {
          resetForm();
        }, 2000);
      } catch (error) {
        console.error('支付失败:', error);
      }
    };

    const resetForm = () => {
      selectedMemberId.value = '';
      selectedMember.value = null;
      paymentAmount.value = 0;
      paymentMethod.value = 'cash';
      paymentSuccess.value = false;
    };

    onMounted(() => {
      fetchMembers();
    });

    // 监听表单变化
    watch([selectedMemberId, paymentAmount, paymentMethod], () => {
      validateForm();
    });

    return {
      members,
      selectedMemberId,
      selectedMember,
      paymentAmount,
      paymentMethod,
      paymentMethods,
      paymentSuccess,
      isFormValid,
      fetchMemberDetails,
      formatDate,
      submitPayment,
    };
  },
};
</script>

<style scoped>
.payment-calculator {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

h3 {
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

select, input[type="number"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.payment-methods {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-top: 5px;
}

.payment-methods label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: normal;
  cursor: pointer;
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
  margin-top: 15px;
}

.submit-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.member-details {
  margin: 15px 0;
  padding: 10px;
  background-color: #f0f0f0;
  border-radius: 4px;
}

.success-message {
  margin-top: 15px;
  padding: 10px;
  background-color: #dff0d8;
  color: #3c763d;
  border-radius: 4px;
  text-align: center;
}
</style>