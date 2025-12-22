<template>
  <el-select
    v-model="selectedCurrency"
    placeholder="Select currency"
    @change="handleCurrencyChange"
    class="currency-selector"
  >
    <el-option
      v-for="currency in supportedCurrencies"
      :key="currency.code"
      :label="`${currency.code} - ${currency.symbol}`"
      :value="currency.code"
    />
  </el-select>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElSelect, ElOption } from 'element-plus';
import { getSupportedCurrencies } from '@/api/payments';

export default {
  name: 'CurrencySelector',
  components: { ElSelect, ElOption },
  emits: ['currency-change'],
  setup(props, { emit }) {
    const selectedCurrency = ref('USD');
    const supportedCurrencies = ref([
      { code: 'USD', symbol: '$' },
      { code: 'EUR', symbol: '€' },
      { code: 'GBP', symbol: '£' },
      { code: 'JPY', symbol: '¥' },
    ]);

    const handleCurrencyChange = (currency) => {
      emit('currency-change', currency);
    };

    onMounted(async () => {
      try {
        const response = await getSupportedCurrencies();
        if (response.data && response.data.length > 0) {
          supportedCurrencies.value = response.data;
        }
      } catch (error) {
        console.error('Failed to fetch supported currencies:', error);
      }
    });

    return {
      selectedCurrency,
      supportedCurrencies,
      handleCurrencyChange,
    };
  },
};
</script>

<style scoped>
.currency-selector {
  width: 200px;
  margin-right: 20px;
}
</style>