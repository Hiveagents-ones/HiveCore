<template>
  <div class="payment-method-selector">
    <h3 class="selector-title">{{ $t('payment.selectMethod') }}</h3>
    <div class="payment-options">
      <div 
        v-for="method in paymentMethods" 
        :key="method.id"
        class="payment-option"
        :class="{ 'selected': selectedMethod === method.id }"
        @click="selectPaymentMethod(method.id)"
      >
        <div class="payment-icon">
          <img :src="method.icon" :alt="method.name" />
        </div>
        <div class="payment-info">
          <h4>{{ method.name }}</h4>
          <p>{{ method.description }}</p>
        </div>
        <div class="payment-radio">
          <input 
            type="radio" 
            :name="'payment-method'" 
            :value="method.id" 
            :checked="selectedMethod === method.id"
          />
          <span class="radio-custom"></span>
        </div>
      </div>
    </div>
    <div class="payment-actions">
      <button 
        class="btn btn-primary" 
        :disabled="!selectedMethod"
        @click="proceedToPayment"
      >
        {{ $t('payment.proceed') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, defineEmits, defineProps } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'payment-selected']);

const selectedMethod = ref(props.modelValue);

const paymentMethods = [
  {
    id: 'wechat',
    name: t('payment.wechat'),
    description: t('payment.wechatDesc'),
    icon: '/icons/wechat-pay.svg'
  },
  {
    id: 'alipay',
    name: t('payment.alipay'),
    description: t('payment.alipayDesc'),
    icon: '/icons/alipay.svg'
  }
];

const selectPaymentMethod = (methodId) => {
  selectedMethod.value = methodId;
  emit('update:modelValue', methodId);
};

const proceedToPayment = () => {
  if (selectedMethod.value) {
    emit('payment-selected', selectedMethod.value);
  }
};
</script>

<style scoped>
.payment-method-selector {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.selector-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
  text-align: center;
}

.payment-options {
  margin-bottom: 30px;
}

.payment-option {
  display: flex;
  align-items: center;
  padding: 15px;
  margin-bottom: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.payment-option:hover {
  border-color: #1976d2;
  background-color: #f5f9ff;
}

.payment-option.selected {
  border-color: #1976d2;
  background-color: #e3f2fd;
}

.payment-icon {
  width: 50px;
  height: 50px;
  margin-right: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.payment-icon img {
  max-width: 100%;
  max-height: 100%;
}

.payment-info {
  flex: 1;
}

.payment-info h4 {
  margin: 0 0 5px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.payment-info p {
  margin: 0;
  font-size: 0.9rem;
  color: #666;
}

.payment-radio {
  position: relative;
}

.payment-radio input[type="radio"] {
  position: absolute;
  opacity: 0;
}

.radio-custom {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid #ccc;
  border-radius: 50%;
  position: relative;
  transition: all 0.3s ease;
}

.payment-option.selected .radio-custom {
  border-color: #1976d2;
}

.payment-option.selected .radio-custom::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #1976d2;
}

.payment-actions {
  text-align: center;
}

.btn {
  padding: 12px 24px;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background-color: #1976d2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1565c0;
}

.btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .payment-method-selector {
    padding: 15px;
  }
  
  .payment-option {
    padding: 12px;
  }
  
  .payment-icon {
    width: 40px;
    height: 40px;
    margin-right: 12px;
  }
  
  .payment-info h4 {
    font-size: 1rem;
  }
  
  .payment-info p {
    font-size: 0.8rem;
  }
}
</style>