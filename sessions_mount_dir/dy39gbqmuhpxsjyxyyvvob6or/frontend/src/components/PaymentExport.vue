<template>
  <div class="payment-export">
    <div class="export-controls">
      <v-select
        v-model="exportFormat"
        :items="exportFormats"
        label="Export Format"
        outlined
        dense
        class="format-select"
      />
      <v-btn
        color="primary"
        :loading="isExporting"
        @click="handleExport"
      >
        Export Payments
      </v-btn>
    </div>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { usePaymentStore } from '@/stores/payment';
import { saveAs } from 'file-saver';

export default {
  name: 'PaymentExport',
  
  setup() {
    const paymentStore = usePaymentStore();
    const exportFormat = ref('csv');
    const isExporting = ref(false);
    const errorMessage = ref('');
    
    const exportFormats = [
      { text: 'CSV', value: 'csv' },
      { text: 'Excel', value: 'xlsx' },
      { text: 'JSON', value: 'json' }
    ];
    
    const formatData = (data, format) => {
      switch (format) {
        case 'csv':
          return data.map(payment => ({
            'Member ID': payment.member_id,
            'Amount': payment.amount,
            'Payment Date': payment.payment_date,
            'Payment Method': payment.payment_method
          }));
        case 'xlsx':
          return data.map(payment => ({
            'Member ID': payment.member_id,
            'Amount': payment.amount,
            'Payment Date': payment.payment_date,
            'Payment Method': payment.payment_method
          }));
        case 'json':
          return data;
        default:
          return data;
      }
    };
    
    const handleExport = async () => {
      isExporting.value = true;
      errorMessage.value = '';
      
      try {
        const payments = await paymentStore.fetchPayments();
        const formattedData = formatData(payments, exportFormat.value);
        
        let blob, filename;
        
        if (exportFormat.value === 'csv') {
          const { jsonToCSV } = await import('@/utils/csvExport');
          const csvContent = jsonToCSV(formattedData);
          blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
          filename = `payments_${new Date().toISOString().slice(0, 10)}.csv`;
        } else if (exportFormat.value === 'xlsx') {
          const { utils, writeFileXLSX } = await import('xlsx');
          const worksheet = utils.json_to_sheet(formattedData);
          const workbook = utils.book_new();
          utils.book_append_sheet(workbook, worksheet, 'Payments');
          const xlsxContent = writeFileXLSX(workbook, { type: 'array' });
          blob = new Blob([xlsxContent], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
          filename = `payments_${new Date().toISOString().slice(0, 10)}.xlsx`;
        } else {
          blob = new Blob([JSON.stringify(formattedData, null, 2)], { type: 'application/json' });
          filename = `payments_${new Date().toISOString().slice(0, 10)}.json`;
        }
        
        saveAs(blob, filename);
      } catch (error) {
        console.error('Export failed:', error);
        errorMessage.value = 'Failed to export payments. Please try again.';
      } finally {
        isExporting.value = false;
      }
    };
    
    return {
      exportFormat,
      exportFormats,
      isExporting,
      errorMessage,
      handleExport
    };
  }
};
</script>

<style scoped>
.payment-export {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 4px;
}

.export-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.format-select {
  min-width: 150px;
}

.error-message {
  margin-top: 10px;
  color: #ff5252;
}
</style>