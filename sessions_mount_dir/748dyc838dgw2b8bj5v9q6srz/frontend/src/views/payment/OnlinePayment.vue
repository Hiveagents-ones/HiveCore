<template>
  <div class="online-payment">
    <h1 class="page-title">续费配置</h1>

    <div class="config-section">
      <h2>支付方式</h2>
      <div class="payment-methods">
        <div
          v-for="method in paymentMethods"
          :key="method.id"
          class="method-card"
          :class="{ 'active': selectedPaymentMethod === method.id }"
          @click="selectedPaymentMethod = method.id"
        >
          <div class="method-icon">
            <i :class="`icon-${method.icon}`"></i>
          </div>
          <div class="method-name">{{ method.name }}</div>
        </div>
      </div>
    </div>

    <div class="config-section">
      <h2>套餐选择</h2>
      <div class="package-options">
        <div
          v-for="pkg in packages"
          :key="pkg.id"
          class="package-card"
          :class="{ 'active': selectedPackage === pkg.id }"
          @click="selectedPackage = pkg.id"
        >
          <div class="package-name">{{ pkg.name }}</div>
          <div class="package-price">{{ pkg.price }}</div>
          <div v-if="pkg.discount" class="discount-tag">{{ pkg.discount }}</div>
        </div>
      </div>
    </div>

    <div class="config-section">
      <h2>优惠规则</h2>
      <div class="rules">
        <p>续费半年送1个月，续费年付送3个月</p>
        <p>到期前7天自动提醒，支持信用卡/支付宝/微信支付</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const selectedPaymentMethod = ref('alipay');
const selectedPackage = ref('annual');

const paymentMethods = [
  { id: 'credit_card', name: '信用卡', icon: 'credit-card' },
  { id: 'alipay', name: '支付宝', icon: 'alipay' },
  { id: 'wechat', name: '微信支付', icon: 'wechat' }
];

const packages = [
  { id: 'monthly', name: '月付', price: '¥100', discount: '' },
  { id: 'quarterly', name: '季付', price: '¥250', discount: '送1个月' },
  { id: 'annual', name: '年付', price: '¥900', discount: '送3个月' }
];
</script>

<style scoped>
.online-payment {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

.page-title {
  text-align: center;
  margin-bottom: 32px;
  color: #333;
}

.config-section {
  margin-bottom: 32px;
}

h2 {
  margin-bottom: 16px;
  color: #444;
  font-size: 1.2rem;
}

.payment-methods {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.method-card {
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.method-card.active {
  border-color: #409EFF;
  background-color: #e6f7ff;
}

.method-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.method-name {
  font-weight: 500;
}

.package-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.package-card {
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.package-card.active {
  border-color: #409EFF;
  background-color: #e6f7ff;
}

.package-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.package-price {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.discount-tag {
  background-color: #e6f7ff;
  color: #409EFF;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  margin-top: 4px;
}

.rules {
  background-color: #f0f9ff;
  padding: 16px;
  border-radius: 8px;
  border-left: 3px solid #409EFF;
}
</style>