<template>
  <div class="payment-list-container">
    <div class="filter-section">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="会员ID">
          <el-input v-model="filterForm.memberId" placeholder="请输入会员ID" clearable />
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="filterForm.paymentMethod" placeholder="请选择支付方式" clearable>
            <el-option
              v-for="method in paymentMethods"
              :key="method.value"
              :label="method.label"
              :value="method.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table :data="paymentList" border style="width: 100%">
      <el-table-column prop="id" label="支付ID" width="120" />
      <el-table-column prop="memberId" label="会员ID" width="120" />
      <el-table-column prop="amount" label="金额" width="120" />
      <el-table-column prop="paymentMethod" label="支付方式" width="120" />
      <el-table-column prop="paymentDate" label="支付日期" width="180" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-section">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPayments } from '../api/payment'

const paymentList = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filterForm = ref({
  memberId: '',
  paymentMethod: '',
  dateRange: []
})

const paymentMethods = [
  { value: 'cash', label: '现金' },
  { value: 'card', label: '银行卡' },
  { value: 'wechat', label: '微信支付' },
  { value: 'alipay', label: '支付宝' }
]

const fetchPayments = async () => {
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      member_id: filterForm.value.memberId,
      payment_method: filterForm.value.paymentMethod,
      start_date: filterForm.value.dateRange ? filterForm.value.dateRange[0] : '',
      end_date: filterForm.value.dateRange ? filterForm.value.dateRange[1] : ''
    }
    
    const response = await getPayments(params)
    paymentList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('获取支付列表失败:', error)
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchPayments()
}

const resetFilters = () => {
  filterForm.value = {
    memberId: '',
    paymentMethod: '',
    dateRange: []
  }
  handleSearch()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchPayments()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchPayments()
}

const handleEdit = (row) => {
  // 编辑逻辑
  console.log('编辑:', row)
}

const handleDelete = (row) => {
  // 删除逻辑
  console.log('删除:', row)
}

onMounted(() => {
  fetchPayments()
})
</script>

<style scoped>
.payment-list-container {
  padding: 20px;
}

.filter-section {
  margin-bottom: 20px;
}

.pagination-section {
  margin-top: 20px;
  text-align: right;
}
</style>