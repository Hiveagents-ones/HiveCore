<template>
  <div class="payment-audit-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>支付审计</span>
          <div class="header-actions">
            <el-button type="primary" @click="fetchPayments">刷新</el-button>
            <currency-selector v-model="currency" @change="handleCurrencyChange" />
          </div>
        </div>
      </template>

      <el-table :data="payments" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="member_name" label="会员姓名" />
        <el-table-column prop="amount" label="金额" :formatter="formatAmount" />
        <el-table-column prop="payment_date" label="支付日期" :formatter="formatDate" />
        <el-table-column prop="payment_type" label="支付类型" />
      </el-table>

      <div class="pagination-container">
        <el-pagination
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[10, 20, 50, 100]"
          :page-size="pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalPayments"
        />
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import CurrencySelector from '@/components/CurrencySelector.vue'

export default {
  name: 'PaymentAudit',
  components: {
    CurrencySelector
  },
  setup() {
    const payments = ref([])
    const loading = ref(false)
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalPayments = ref(0)
    const currency = ref('CNY')

    const fetchPayments = async () => {
      try {
        loading.value = true
        const response = await axios.get('/api/v1/payments', {
          params: {
            page: currentPage.value,
            size: pageSize.value,
            currency: currency.value
          }
        })
        payments.value = response.data.items
        totalPayments.value = response.data.total
      } catch (error) {
        ElMessage.error('获取支付记录失败: ' + error.message)
      } finally {
        loading.value = false
      }
    }

    const handleSizeChange = (val) => {
      pageSize.value = val
      fetchPayments()
    }

    const handleCurrentChange = (val) => {
      currentPage.value = val
      fetchPayments()
    }

    const handleCurrencyChange = () => {
      fetchPayments()
    }

    const formatDate = (row, column, cellValue) => {
      return new Date(cellValue).toLocaleString()
    }

    const formatAmount = (row, column, cellValue) => {
      return `${currency.value} ${cellValue.toFixed(2)}`
    }

    onMounted(() => {
      fetchPayments()
    })

    return {
      payments,
      loading,
      currentPage,
      pageSize,
      totalPayments,
      currency,
      fetchPayments,
      handleSizeChange,
      handleCurrentChange,
      handleCurrencyChange,
      formatDate,
      formatAmount
    }
  }
}
</script>

<style scoped>
.payment-audit-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>