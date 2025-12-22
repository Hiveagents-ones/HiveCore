<template>
  <div class="online-payment">
    <div class="payment-container">
      <h2>在线支付</h2>
      
      <!-- Payment Amount Section -->
      <div class="payment-amount">
        <h3>支付金额</h3>
        <div class="amount-display">
          <span class="currency">¥</span>
          <input 
            v-model="paymentAmount" 
            type="number" 
            step="0.01" 
            min="0.01"
            class="amount-input"
            placeholder="0.00"
          />
        </div>
      </div>

      <!-- Payment Methods Section -->
      <div class="payment-methods">
        <h3>选择支付方式</h3>
        <div class="methods-grid">
          <div 
            v-for="method in paymentMethods" 
            :key="method.id"
            class="method-card"
            :class="{ active: selectedMethod?.id === method.id }"
            @click="selectPaymentMethod(method)"
          >
            <div class="method-icon">
              <i :class="method.icon"></i>
            </div>
            <div class="method-info">
              <h4>{{ method.name }}</h4>
              <p>{{ method.description }}</p>
            </div>
            <div class="method-radio">
              <input 
                type="radio" 
                :value="method.id" 
                v-model="selectedMethodId"
                name="payment-method"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Payment Details Section -->
      <div v-if="selectedMethod" class="payment-details">
        <h3>支付详情</h3>
        <div class="details-form">
          <div class="form-group">
            <label>会员ID</label>
            <input 
              v-model="paymentDetails.memberId" 
              type="text" 
              placeholder="请输入会员ID"
            />
          </div>
          <div class="form-group">
            <label>支付说明</label>
            <textarea 
              v-model="paymentDetails.description" 
              placeholder="请输入支付说明（选填）"
              rows="3"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="payment-actions">
        <button 
          class="btn-cancel" 
          @click="cancelPayment"
        >
          取消
        </button>
        <button 
          class="btn-confirm" 
          @click="processPayment"
          :disabled="!canProcessPayment"
        >
          确认支付
        </button>
      </div>

      <!-- Loading Overlay -->
      <div v-if="isProcessing" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p>正在处理支付...</p>
      </div>
    </div>

    <!-- Success Modal -->
    <div v-if="showSuccessModal" class="modal-overlay" @click="closeSuccessModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>支付成功</h3>
          <button class="close-btn" @click="closeSuccessModal">×</button>
        </div>
        <div class="modal-body">
          <p>您的支付已成功处理</p>
          <p>支付金额: ¥{{ paymentAmount }}</p>
          <p>支付方式: {{ selectedMethod?.name }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="closeSuccessModal">确定</button>
        </div>
      </div>
    </div>

    <!-- Error Modal -->
    <div v-if="showErrorModal" class="modal-overlay" @click="closeErrorModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>支付失败</h3>
          <button class="close-btn" @click="closeErrorModal">×</button>
        </div>
        <div class="modal-body">
          <p>{{ errorMessage }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="closeErrorModal">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { paymentAPI } from '@/api/payment.js';

export default {
  name: 'OnlinePayment',
  setup() {
    // State
    const paymentAmount = ref('');
    const paymentMethods = ref([]);
    const selectedMethod = ref(null);
    const selectedMethodId = ref(null);
    const isProcessing = ref(false);
    const showSuccessModal = ref(false);
    const showErrorModal = ref(false);
    const errorMessage = ref('');
    
    const paymentDetails = ref({
      memberId: '',
      description: ''
    });

    // Computed
    const canProcessPayment = computed(() => {
      return paymentAmount.value && 
             selectedMethod.value && 
             paymentDetails.value.memberId &&
             !isProcessing.value;
    });

    // Methods
    const fetchPaymentMethods = async () => {
      try {
        const response = await paymentAPI.getPaymentMethods();
        paymentMethods.value = response.methods || [];
      } catch (error) {
        console.error('Error fetching payment methods:', error);
        showError('获取支付方式失败，请稍后重试');
      }
    };

    const selectPaymentMethod = (method) => {
      selectedMethod.value = method;
      selectedMethodId.value = method.id;
    };

    const processPayment = async () => {
      if (!canProcessPayment.value) return;

      isProcessing.value = true;
      
      try {
        const paymentData = {
          amount: parseFloat(paymentAmount.value),
          method: selectedMethod.value.id,
          member_id: paymentDetails.value.memberId,
          description: paymentDetails.value.description,
          type: 'online'
        };

        const response = await paymentAPI.recordPayment(paymentData);
        
        if (response.success) {
          showSuccessModal.value = true;
          resetForm();
        } else {
          showError(response.message || '支付处理失败');
        }
      } catch (error) {
        console.error('Error processing payment:', error);
        showError('支付处理失败，请稍后重试');
      } finally {
        isProcessing.value = false;
      }
    };

    const cancelPayment = () => {
      resetForm();
    };

    const resetForm = () => {
      paymentAmount.value = '';
      selectedMethod.value = null;
      selectedMethodId.value = null;
      paymentDetails.value = {
        memberId: '',
        description: ''
      };
    };

    const showError = (message) => {
      errorMessage.value = message;
      showErrorModal.value = true;
    };

    const closeSuccessModal = () => {
      showSuccessModal.value = false;
    };

    const closeErrorModal = () => {
      showErrorModal.value = false;
      errorMessage.value = '';
    };

    // Lifecycle
    onMounted(() => {
      fetchPaymentMethods();
    });

    return {
      // State
      paymentAmount,
      paymentMethods,
      selectedMethod,
      selectedMethodId,
      isProcessing,
      showSuccessModal,
      showErrorModal,
      errorMessage,
      paymentDetails,
      
      // Computed
      canProcessPayment,
      
      // Methods
      selectPaymentMethod,
      processPayment,
      cancelPayment,
      closeSuccessModal,
      closeErrorModal
    };
  }
};
</script>

<style scoped>
.online-payment {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.payment-container {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

h2 {
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

h3 {
  color: #555;
  margin-bottom: 20px;
  font-size: 1.2rem;
}

.payment-amount {
  margin-bottom: 30px;
}

.amount-display {
  display: flex;
  align-items: center;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
  font-size: 1.5rem;
}

.currency {
  font-weight: bold;
  margin-right: 10px;
  color: #666;
}

.amount-input {
  border: none;
  outline: none;
  font-size: 1.5rem;
  width: 100%;
  font-weight: bold;
}

.payment-methods {
  margin-bottom: 30px;
}

.methods-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.method-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
}

.method-card:hover {
  border-color: #4CAF50;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
}

.method-card.active {
  border-color: #4CAF50;
  background-color: #f8fff8;
}

.method-icon {
  font-size: 2rem;
  margin-right: 15px;
  color: #4CAF50;
}

.method-info {
  flex: 1;
}

.method-info h4 {
  margin: 0 0 5px 0;
  color: #333;
}

.method-info p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.method-radio input {
  width: 20px;
  height: 20px;
  accent-color: #4CAF50;
}

.payment-details {
  margin-bottom: 30px;
}

.details-form {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #4CAF50;
}

.payment-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
}

.btn-cancel,
.btn-confirm {
  padding: 12px 30px;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel {
  background-color: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background-color: #e0e0e0;
}

.btn-confirm {
  background-color: #4CAF50;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background-color: #45a049;
}

.btn-confirm:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-overlay p {
  color: white;
  font-size: 1.2rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.2);
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #eee;
  text-align: right;
}

.btn-primary {
  background-color: #4CAF50;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover {
  background-color: #45a049;
}

@media (max-width: 768px) {
  .online-payment {
    padding: 10px;
  }
  
  .payment-container {
    padding: 20px;
  }
  
  .methods-grid {
    grid-template-columns: 1fr;
  }
  
  .payment-actions {
    flex-direction: column;
  }
  
  .btn-cancel,
  .btn-confirm {
    width: 100%;
  }
}
</style>