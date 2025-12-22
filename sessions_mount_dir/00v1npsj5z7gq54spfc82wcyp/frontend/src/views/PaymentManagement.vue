<template>
  <div class="payment-management">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>收费管理</span>
        </div>
      </template>

      <div class="filter-container">
        <el-form :inline="true" :model="filterParams" class="filter-form">
          <el-form-item label="会员ID">
            <el-input v-model="filterParams.member_id" placeholder="请输入会员ID" clearable />
          </el-form-item>
          <el-form-item label="支付类型">
            <el-select v-model="filterParams.payment_type" placeholder="请选择支付类型" clearable>
              <el-option label="会员费" value="membership" />
              <el-option label="课程费" value="course" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="filterParams.date_range"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchPayments">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="operation-container">
        <el-button type="primary" @click="handleCreate">新增收费</el-button>
        <el-button type="success" @click="generateReport">生成报表</el-button>
      </div>

      <el-table
        :data="paymentList"
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
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchPayments"
          @current-change="fetchPayments"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="50%"
    >
      <el-form :model="paymentForm" :rules="rules" ref="paymentFormRef" label-width="100px">
        <el-form-item label="会员" prop="member_id">
          <el-select
            v-model="paymentForm.member_id"
            filterable
            remote
            reserve-keyword
            placeholder="请输入会员姓名或手机号"
            :remote-method="searchMembers"
            :loading="memberLoading"
            @change="handleMemberChange"
          >
            <el-option
              v-for="item in memberOptions"
              :key="item.id"
              :label="`${item.name} (${item.phone})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="支付类型" prop="payment_type">
          <el-radio-group v-model="paymentForm.payment_type">
            <el-radio label="membership">会员费</el-radio>
            <el-radio label="course">课程费</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="paymentForm.amount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="支付日期" prop="payment_date">
          <el-date-picker
            v-model="paymentForm.payment_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPayments, createPayment, updatePayment, deletePayment, generatePaymentReport } from '../api/payment'
import { searchMembers as apiSearchMembers } from '../api/member'

// 表格数据
const paymentList = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 筛选条件
const filterParams = reactive({
  member_id: '',
  payment_type: '',
  date_range: []
})

// 表单相关
const dialogVisible = ref(false)
const dialogTitle = ref('新增收费')
const paymentFormRef = ref(null)
const paymentForm = reactive({
  id: null,
  member_id: '',
  member_name: '',
  amount: 0,
  payment_type: 'membership',
  payment_date: new Date().toISOString().split('T')[0]
})

const rules = reactive({
  member_id: [{ required: true, message: '请选择会员', trigger: 'change' }],
  payment_type: [{ required: true, message: '请选择支付类型', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  payment_date: [{ required: true, message: '请选择支付日期', trigger: 'change' }]
})

// 会员搜索相关
const memberOptions = ref([])
const memberLoading = ref(false)

// 初始化加载数据
onMounted(() => {
  fetchPayments()
})

// 获取支付记录
const fetchPayments = async () => {
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      member_id: filterParams.member_id,
      payment_type: filterParams.payment_type
    }

    if (filterParams.date_range && filterParams.date_range.length === 2) {
      params.start_date = filterParams.date_range[0]
      params.end_date = filterParams.date_range[1]
    }

    const response = await getPayments(params)
    paymentList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取支付记录失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  filterParams.member_id = ''
  filterParams.payment_type = ''
  filterParams.date_range = []
  fetchPayments()
}

// 格式化支付类型
const formatPaymentType = (type) => {
  return type === 'membership' ? '会员费' : '课程费'
}

// 搜索会员
const searchMembers = async (query) => {
  if (query) {
    memberLoading.value = true
    try {
      const response = await apiSearchMembers({ query })
      memberOptions.value = response.data
    } catch (error) {
      ElMessage.error('搜索会员失败：' + error.message)
    } finally {
      memberLoading.value = false
    }
  }
}

// 会员选择变化
const handleMemberChange = (memberId) => {
  const selectedMember = memberOptions.value.find(member => member.id === memberId)
  if (selectedMember) {
    paymentForm.member_name = selectedMember.name
  }
}

// 新增收费
const handleCreate = () => {
  dialogTitle.value = '新增收费'
  resetForm()
  dialogVisible.value = true
}

// 编辑收费
const handleEdit = (row) => {
  dialogTitle.value = '编辑收费'
  Object.assign(paymentForm, row)
  dialogVisible.value = true
}

// 删除收费
const handleDelete = (row) => {
  ElMessageBox.confirm('确认删除该收费记录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deletePayment(row.id)
      ElMessage.success('删除成功')
      fetchPayments()
    } catch (error) {
      ElMessage.error('删除失败：' + error.message)
    }
  }).catch(() => {})
}

// 生成报表
const generateReport = async () => {
  try {
    loading.value = true
    const params = {
      member_id: filterParams.member_id,
      payment_type: filterParams.payment_type
    }

    if (filterParams.date_range && filterParams.date_range.length === 2) {
      params.start_date = filterParams.date_range[0]
      params.end_date = filterParams.date_range[1]
    }

    const response = await generatePaymentReport(params)
    // 这里应该处理报表下载，假设API返回的是文件流
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `payment_report_${new Date().toISOString().split('T')[0]}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('报表生成成功')
  } catch (error) {
    ElMessage.error('生成报表失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 重置表单
const resetForm = () => {
  paymentForm.id = null
  paymentForm.member_id = ''
  paymentForm.member_name = ''
  paymentForm.amount = 0
  paymentForm.payment_type = 'membership'
  paymentForm.payment_date = new Date().toISOString().split('T')[0]
}

// 提交表单
const submitForm = async () => {
  try {
    await paymentFormRef.value.validate()
    
    if (paymentForm.id) {
      // 更新
      await updatePayment(paymentForm.id, paymentForm)
      ElMessage.success('更新成功')
    } else {
      // 新增
      await createPayment(paymentForm)
      ElMessage.success('新增成功')
    }
    
    dialogVisible.value = false
    fetchPayments()
  } catch (error) {
    if (error.message) {
      ElMessage.error('操作失败：' + error.message)
    }
  }
}
</script>

<style scoped>
.payment-management {
  padding: 20px;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.filter-container {
  margin-bottom: 20px;
}

.operation-container {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}
</style>