<template>
  <div class="payment-history">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>支付记录</span>
        </div>
      </template>

      <el-table
        :data="historyData"
        border
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="member_id" label="会员ID" width="100" />
        <el-table-column prop="member_name" label="会员姓名" />
        <el-table-column prop="amount" label="金额" width="120" />
        <el-table-column prop="payment_type" label="支付类型" width="120">
          <template #default="scope">
            {{ formatPaymentType(scope.row.payment_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="payment_date" label="支付日期" width="180" />
        <el-table-column prop="description" label="备注" />
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[5, 10, 20]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchHistory"
          @current-change="fetchHistory"
        />
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getPaymentHistory } from '../api/payments'

const paymentTypeMap = {
  membership: '会员费',
  course: '课程费'
}

export default {
  name: 'PaymentHistory',
  props: {
    memberId: {
      type: [String, Number],
      default: null
    }
  },
  setup(props) {
    const historyData = ref([])
    const loading = ref(false)
    const currentPage = ref(1)
    const pageSize = ref(5)
    const total = ref(0)

    const formatPaymentType = (type) => {
      return paymentTypeMap[type] || type
    }

    const fetchHistory = async () => {
      try {
        loading.value = true
        const params = {
          page: currentPage.value,
          size: pageSize.value,
          member_id: props.memberId
        }
        const response = await getPaymentHistory(params)
        historyData.value = response.data.items
        total.value = response.data.total
      } catch (error) {
        console.error('获取支付记录失败:', error)
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      fetchHistory()
    })

    return {
      historyData,
      loading,
      currentPage,
      pageSize,
      total,
      formatPaymentType,
      fetchHistory
    }
  }
}
</script>

<style scoped>
.payment-history {
  margin-top: 20px;
}
.pagination-container {
  margin-top: 20px;
  text-align: right;
}
</style>