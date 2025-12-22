<template>
  <div class="payment-container">
    <div class="payment-header">
      <h2>支付确认</h2>
      <div class="order-summary">
        <h3>订单摘要</h3>
        <div class="plan-info">
          <span class="plan-name">{{ selectedPlan?.name || '基础会员' }}</span>
          <span class="plan-price">\u00a5{{ selectedPlan?.price || '99' }}</span>
        </div>
        <div class="plan-duration">
          有效期：{{ selectedPlan?.duration || '1个月' }}
        </div>
      </div>
    </div>

    <div class="payment-methods">
      <h3>选择支付方式</h3>
      <div class="method-list">
        <div 
          v-for="method in paymentMethods" 
          :key="method.id"
          class="method-item"
          :class="{ active: selectedMethod === method.id }"
          @click="selectPaymentMethod(method.id)"
        >
          <div class="method-icon">
            <img :src="method.icon" :alt="method.name" />
          </div>
          <div class="method-info">
            <span class="method-name">{{ method.name }}</span>
            <span class="method-desc">{{ method.description }}</span>
          </div>
          <div class="method-radio">
            <input 
              type="radio" 
              :value="method.id" 
              v-model="selectedMethod"
              :name="'payment-method'"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="payment-form" v-if="selectedMethod">
      <h3>支付信息</h3>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="email">邮箱地址</label>
          <input 
            type="email" 
            id="email" 
            v-model="paymentInfo.email" 
            required
            placeholder="请输入您的邮箱"
          />
        </div>

        <div class="form-group" v-if="selectedMethod === 'alipay'">
          <label for="alipay-account">支付宝账号</label>
          <input 
            type="text" 
            id="alipay-account" 
            v-model="paymentInfo.alipayAccount" 
            required
            placeholder="请输入支付宝账号"
          />
        </div>

        <div class="form-group" v-if="selectedMethod === 'wechat'">
          <label for="wechat-id">微信号</label>
          <input 
            type="text" 
            id="wechat-id" 
            v-model="paymentInfo.wechatId" 
            required
            placeholder="请输入微信号"
          />
        </div>

        <div class="form-group" v-if="selectedMethod === 'stripe'">
          <label for="card-number">卡号</label>
          <input 
            type="text" 
            id="card-number" 
            v-model="paymentInfo.cardNumber" 
            required
            placeholder="1234 5678 9012 3456"
            maxlength="19"
            @input="formatCardNumber"
          />
        </div>

        <div class="form-row" v-if="selectedMethod === 'stripe'">
          <div class="form-group">
            <label for="expiry">有效期</label>
            <input 
              type="text" 
              id="expiry" 
              v-model="paymentInfo.expiry" 
              required
              placeholder="MM/YY"
              maxlength="5"
              @input="formatExpiry"
            />
          </div>
          <div class="form-group">
            <label for="cvv">CVV</label>
            <input 
              type="text" 
              id="cvv" 
              v-model="paymentInfo.cvv" 
              required
              placeholder="123"
              maxlength="3"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="name">持卡人姓名</label>
          <input 
            type="text" 
            id="name" 
            v-model="paymentInfo.name" 
            required
            placeholder="请输入持卡人姓名"
          />
        </div>

        <div class="form-actions">
          <button type="button" class="btn-cancel" @click="handleCancel">
            取消
          </button>
          <button type="submit" class="btn-confirm" :disabled="isProcessing">
            {{ isProcessing ? '处理中...' : '确认支付' }}
          </button>
        </div>
      </form>
    </div>

    <div class="payment-security">
      <div class="security-item">
        <i class="icon-lock"></i>
        <span>SSL加密保护</span>
      </div>
      <div class="security-item">
        <i class="icon-shield"></i>
        <span>安全支付保障</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSubscriptionStore } from '@/stores/subscription'

const route = useRoute()
const router = useRouter()
const subscriptionStore = useSubscriptionStore()

const selectedPlan = ref(null)
const selectedMethod = ref('')
const isProcessing = ref(false)

const paymentMethods = ref([
  {
    id: 'alipay',
    name: '支付宝',
    description: '使用支付宝安全支付',
    icon: '/icons/alipay.svg'
  },
  {
    id: 'wechat',
    name: '微信支付',
    description: '使用微信安全支付',
    icon: '/icons/wechat.svg'
  },
  {
    id: 'stripe',
    name: '信用卡/借记卡',
    description: '支持Visa、MasterCard等',
    icon: '/icons/stripe.svg'
  }
])

const paymentInfo = ref({
  email: '',
  alipayAccount: '',
  wechatId: '',
  cardNumber: '',
  expiry: '',
  cvv: '',
  name: ''
})

onMounted(() => {
  // 从路由参数或状态管理中获取选中的计划
  const planId = route.query.plan
  if (planId) {
    selectedPlan.value = subscriptionStore.getPlanById(planId)
  }
  
  // 默认选择第一个支付方式
  if (paymentMethods.value.length > 0) {
    selectedMethod.value = paymentMethods.value[0].id
  }
})

const selectPaymentMethod = (methodId) => {
  selectedMethod.value = methodId
}

const formatCardNumber = (e) => {
  let value = e.target.value.replace(/\s/g, '')
  let formattedValue = value.match(/.{1,4}/g)?.join(' ') || value
  paymentInfo.value.cardNumber = formattedValue
}

const formatExpiry = (e) => {
  let value = e.target.value.replace(/\D/g, '')
  if (value.length >= 2) {
    value = value.slice(0, 2) + '/' + value.slice(2, 4)
  }
  paymentInfo.value.expiry = value
}

const handleSubmit = async () => {
  if (!selectedMethod.value) {
    alert('请选择支付方式')
    return
  }

  isProcessing.value = true
  
  try {
    // 准备支付数据
    const paymentData = {
      planId: selectedPlan.value?.id,
      method: selectedMethod.value,
      info: paymentInfo.value
    }

    // 调用支付API
    const result = await subscriptionStore.processPayment(paymentData)
    
    if (result.success) {
      // 支付成功，跳转到成功页面
      router.push({
        name: 'PaymentSuccess',
        query: { orderId: result.orderId }
      })
    } else {
      // 支付失败，显示错误信息
      alert(result.message || '支付失败，请重试')
    }
  } catch (error) {
    console.error('Payment error:', error)
    alert('支付过程中发生错误，请重试')
  } finally {
    isProcessing.value = false
  }
}

const handleCancel = () => {
  router.push({ name: 'PlanSelection' })
}
</script>

<style scoped>
.payment-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.payment-header {
  margin-bottom: 2rem;
}

.payment-header h2 {
  font-size: 1.8rem;
  color: #333;
  margin-bottom: 1rem;
}

.order-summary {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
}

.order-summary h3 {
  font-size: 1.2rem;
  color: #555;
  margin-bottom: 0.5rem;
}

.plan-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.plan-name {
  font-weight: 600;
  color: #333;
}

.plan-price {
  font-size: 1.2rem;
  font-weight: 700;
  color: #e74c3c;
}

.plan-duration {
  color: #666;
  font-size: 0.9rem;
}

.payment-methods {
  margin-bottom: 2rem;
}

.payment-methods h3 {
  font-size: 1.4rem;
  color: #333;
  margin-bottom: 1rem;
}

.method-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.method-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.method-item:hover {
  border-color: #3498db;
  background: #f8f9fa;
}

.method-item.active {
  border-color: #3498db;
  background: #e3f2fd;
}

.method-icon {
  width: 40px;
  height: 40px;
  margin-right: 1rem;
}

.method-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.method-info {
  flex: 1;
}

.method-name {
  display: block;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.method-desc {
  display: block;
  font-size: 0.9rem;
  color: #666;
}

.method-radio input[type="radio"] {
  width: 20px;
  height: 20px;
  accent-color: #3498db;
}

.payment-form {
  margin-bottom: 2rem;
}

.payment-form h3 {
  font-size: 1.4rem;
  color: #333;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-row .form-group {
  flex: 1;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-cancel,
.btn-confirm {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel {
  background: #e0e0e0;
  color: #333;
}

.btn-cancel:hover {
  background: #d0d0d0;
}

.btn-confirm {
  background: #3498db;
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #2980b9;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.payment-security {
  display: flex;
  justify-content: center;
  gap: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.security-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.icon-lock,
.icon-shield {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

@media (max-width: 768px) {
  .payment-container {
    padding: 1rem;
  }
  
  .form-row {
    flex-direction: column;
  }
  
  .payment-security {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>