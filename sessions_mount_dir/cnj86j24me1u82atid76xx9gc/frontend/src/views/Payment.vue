<template>
  <div class="payment-container">
    <div class="payment-header">
      <h2>选择支付方式</h2>
      <p class="payment-amount">¥{{ formattedAmount }}</p>
    </div>

    <div class="payment-methods" v-if="!loading">
      <div 
        v-for="method in paymentStore.paymentMethods" 
        :key="method.code"
        class="payment-method"
        :class="{ active: paymentStore.selectedPaymentMethod === method.code }"
        @click="selectPaymentMethod(method.code)"
      >
        <div class="method-icon">
          <img :src="getMethodIcon(method.code)" :alt="method.name" />
        </div>
        <div class="method-info">
          <h3>{{ method.name }}</h3>
          <p>{{ method.description }}</p>
        </div>
        <div class="method-radio">
          <input 
            type="radio" 
            :value="method.code" 
            v-model="paymentStore.selectedPaymentMethod"
            :id="`method-${method.code}`"
          />
          <label :for="`method-${method.code}`"></label>
        </div>
      </div>
    </div>

    <div class="payment-loading" v-else>
      <div class="spinner"></div>
      <p>加载支付方式中...</p>
    </div>

    <div class="payment-form" v-if="paymentStore.selectedPaymentMethod">
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="email">电子邮箱</label>
          <input 
            type="email" 
            id="email" 
            v-model="paymentForm.email" 
            required 
            placeholder="请输入您的电子邮箱"
          />
        </div>

        <div class="form-group" v-if="paymentStore.selectedPaymentMethod === 'stripe'">
          <label for="cardNumber">卡号</label>
          <input 
            type="text" 
            id="cardNumber" 
            v-model="paymentForm.cardNumber" 
            required 
            placeholder="1234 5678 9012 3456"
            maxlength="19"
            @input="formatCardNumber"
          />
        </div>

        <div class="form-row" v-if="paymentStore.selectedPaymentMethod === 'stripe'">
          <div class="form-group">
            <label for="expiryDate">有效期</label>
            <input 
              type="text" 
              id="expiryDate" 
              v-model="paymentForm.expiryDate" 
              required 
              placeholder="MM/YY"
              maxlength="5"
              @input="formatExpiryDate"
            />
          </div>
          <div class="form-group">
            <label for="cvv">CVV</label>
            <input 
              type="text" 
              id="cvv" 
              v-model="paymentForm.cvv" 
              required 
              placeholder="123"
              maxlength="4"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="notes">备注（选填）</label>
          <textarea 
            id="notes" 
            v-model="paymentForm.notes" 
            placeholder="如有特殊需求请在此说明"
            rows="3"
          ></textarea>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-cancel" @click="handleCancel">
            取消
          </button>
          <button type="submit" class="btn-submit" :disabled="processing">
            {{ processing ? '处理中...' : '确认支付' }}
          </button>
        </div>
      </form>
    </div>

    <div class="payment-status" v-if="paymentStatus">
      <div class="status-message" :class="paymentStatus.type">
        {{ paymentStatus.message }}
      </div>
      <div class="status-actions" v-if="paymentStatus.type === 'success'">
        <button class="btn-view" @click="viewPaymentDetails">
          查看支付详情
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePaymentStore } from '@/stores/payment';
import { 
  getPaymentMethods, 
  createPayment, 
  getPaymentStatus 
} from '@/api/payment.js';

export default {
  name: 'Payment',
  props: {
    planId: {
      type: String,
      required: true
    },
    amount: {
      type: Number,
      required: true
    },
    currency: {
      type: String,
      default: 'CNY'
    }
  },
  setup(props) {
    const router = useRouter();
    const paymentStore = usePaymentStore();
    const loading = ref(true);
    const processing = ref(false);
    const paymentForm = ref({
      email: '',
      cardNumber: '',
      expiryDate: '',
      cvv: '',
      notes: ''
    });
    const paymentStatus = ref(null);

    const formattedAmount = computed(() => {
      return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: props.currency
      }).format(props.amount);
    });

    const fetchPaymentMethods = async () => {
      try {
        await paymentStore.fetchPaymentMethods();
      } catch (error) {
        console.error('获取支付方式失败:', error);
        paymentStatus.value = {
          type: 'error',
          message: '获取支付方式失败，请刷新页面重试'
        };
      } finally {
        loading.value = false;
      }
    };

    const getMethodIcon = (code) => {
      const icons = {
        alipay: '/icons/alipay.png',
        wechat: '/icons/wechat.png',
        stripe: '/icons/stripe.png'
      };
      return icons[code] || '/icons/default-payment.png';
    };

    const selectPaymentMethod = (method) => {
      paymentStore.selectedPaymentMethod = method;
      paymentStatus.value = null;
    };

    const formatCardNumber = (e) => {
      let value = e.target.value.replace(/\s/g, '');
      let formattedValue = value.match(/.{1,4}/g)?.join(' ') || value;
      paymentForm.value.cardNumber = formattedValue;
    };

    const formatExpiryDate = (e) => {
      let value = e.target.value.replace(/\D/g, '');
      if (value.length >= 2) {
        value = value.slice(0, 2) + '/' + value.slice(2, 4);
      }
      paymentForm.value.expiryDate = value;
    };

    const handleSubmit = async () => {
      if (!paymentStore.selectedPaymentMethod) {
        paymentStatus.value = {
          type: 'error',
          message: '请选择支付方式'
        };
        return;
      }

      processing.value = true;
      paymentStatus.value = null;

      try {
        const paymentData = {
          membership_plan_id: props.planId,
          payment_method: paymentStore.selectedPaymentMethod,
          amount: props.amount,
          currency: props.currency,
          email: paymentForm.value.email,
          notes: paymentForm.value.notes
        };

        if (paymentStore.selectedPaymentMethod === 'stripe') {
          paymentData.card_info = {
            number: paymentForm.value.cardNumber.replace(/\s/g, ''),
            expiry: paymentForm.value.expiryDate,
            cvv: paymentForm.value.cvv
          };
        }

        const response = await paymentStore.createPaymentOrder(paymentData);

        // 根据支付方式处理不同的响应
        if (paymentStore.selectedPaymentMethod === 'alipay' || paymentStore.selectedPaymentMethod === 'wechat') {
          // 跳转到第三方支付页面
          window.location.href = response.payment_url;
        } else if (paymentStore.selectedPaymentMethod === 'stripe') {
          // 直接处理支付结果
          await checkPaymentStatus(response.payment_id);
        }
      } catch (error) {
        console.error('支付处理失败:', error);
        paymentStatus.value = {
          type: 'error',
          message: error.response?.data?.message || '支付处理失败，请重试'
        };
      } finally {
        processing.value = false;
      }
    };

    const checkPaymentStatus = async (paymentId) => {
      try {
        const status = await paymentStore.checkPaymentStatus(paymentId);
        if (status.status === 'completed') {
          paymentStatus.value = {
            type: 'success',
            message: '支付成功！'
          };
        } else if (status.status === 'failed') {
          paymentStatus.value = {
            type: 'error',
            message: '支付失败，请重试'
          };
        } else {
          paymentStatus.value = {
            type: 'pending',
            message: '支付处理中，请稍后查看结果'
          };
        }
      } catch (error) {
        console.error('查询支付状态失败:', error);
        paymentStatus.value = {
          type: 'error',
          message: '查询支付状态失败'
        };
      }
    };

    const handleCancel = () => {
      router.push('/member-plans');
    };

    const viewPaymentDetails = () => {
      if (paymentStore.currentPayment?.id) {
        router.push(`/payment-details/${paymentStore.currentPayment.id}`);
      }
    };

    onMounted(() => {
      fetchPaymentMethods();
    });

    return {
      loading,
      processing,
      paymentForm,
      paymentStatus,
      formattedAmount,
      selectPaymentMethod,
      formatCardNumber,
      formatExpiryDate,
      handleSubmit,
      handleCancel,
      viewPaymentDetails
    };
  }
};
</script>

<style scoped>
.payment-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.payment-header {
  text-align: center;
  margin-bottom: 30px;
}

.payment-header h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.payment-amount {
  font-size: 32px;
  font-weight: bold;
  color: #e74c3c;
}

.payment-methods {
  margin-bottom: 30px;
}

.payment-method {
  display: flex;
  align-items: center;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.payment-method:hover {
  border-color: #3498db;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.2);
}

.payment-method.active {
  border-color: #3498db;
  background-color: #f8f9fa;
}

.method-icon {
  width: 50px;
  height: 50px;
  margin-right: 15px;
}

.method-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.method-info {
  flex: 1;
}

.method-info h3 {
  margin: 0 0 5px 0;
  font-size: 16px;
  color: #333;
}

.method-info p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.method-radio {
  margin-left: 15px;
}

.method-radio input[type="radio"] {
  display: none;
}

.method-radio label {
  display: block;
  width: 20px;
  height: 20px;
  border: 2px solid #ccc;
  border-radius: 50%;
  position: relative;
  cursor: pointer;
}

.method-radio input[type="radio"]:checked + label {
  border-color: #3498db;
}

.method-radio input[type="radio"]:checked + label::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  background-color: #3498db;
  border-radius: 50%;
}

.payment-loading {
  text-align: center;
  padding: 40px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.payment-form {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-row .form-group {
  flex: 1;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3498db;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.btn-cancel,
.btn-submit,
.btn-view {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-cancel {
  background-color: #e74c3c;
  color: white;
}

.btn-cancel:hover {
  background-color: #c0392b;
}

.btn-submit {
  background-color: #3498db;
  color: white;
}

.btn-submit:hover {
  background-color: #2980b9;
}

.btn-submit:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.btn-view {
  background-color: #2ecc71;
  color: white;
}

.btn-view:hover {
  background-color: #27ae60;
}

.payment-status {
  margin-top: 20px;
}

.status-message {
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 10px;
}

.status-message.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.status-message.pending {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

.status-actions {
  text-align: center;
}

@media (max-width: 768px) {
  .payment-container {
    padding: 10px;
  }

  .form-row {
    flex-direction: column;
    gap: 0;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-cancel,
  .btn-submit {
    width: 100%;
  }
}
</style>