<template>
  <div class="merchant-list-container">
    <h1 class="page-title">商家管理</h1>
    
    <!-- 搜索和筛选 -->
    <div class="filters-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-input
            v-model="searchQuery"
            placeholder="搜索商家名称或ID"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </el-col>
        <el-col :span="4">
          <el-select v-model="statusFilter" placeholder="审核状态" clearable @change="handleFilter">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已下线" value="offline" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 商家列表 -->
    <el-table
      v-loading="loading"
      :data="merchantList"
      style="width: 100%"
      stripe
      border
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="商家名称" min-width="150" />
      <el-table-column prop="contact_name" label="联系人" width="120" />
      <el-table-column prop="contact_phone" label="联系电话" width="130" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip />
      <el-table-column label="审核状态" width="100">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <el-button
            size="small"
            type="primary"
            link
            @click="handleView(scope.row)"
          >
            查看
          </el-button>
          <el-button
            v-if="scope.row.status === 'pending'"
            size="small"
            type="success"
            link
            @click="handleApprove(scope.row)"
          >
            通过
          </el-button>
          <el-button
            v-if="scope.row.status === 'pending'"
            size="small"
            type="danger"
            link
            @click="handleReject(scope.row)"
          >
            拒绝
          </el-button>
          <el-button
            v-if="scope.row.status === 'approved'"
            size="small"
            type="warning"
            link
            @click="handleOffline(scope.row)"
          >
            下线
          </el-button>
          <el-button
            size="small"
            type="info"
            link
            @click="handleEdit(scope.row)"
          >
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 查看/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="merchantFormRef"
        :model="merchantForm"
        :rules="merchantRules"
        label-width="100px"
      >
        <el-form-item label="商家名称" prop="name">
          <el-input v-model="merchantForm.name" :disabled="dialogMode === 'view'" />
        </el-form-item>
        <el-form-item label="联系人" prop="contact_name">
          <el-input v-model="merchantForm.contact_name" :disabled="dialogMode === 'view'" />
        </el-form-item>
        <el-form-item label="联系电话" prop="contact_phone">
          <el-input v-model="merchantForm.contact_phone" :disabled="dialogMode === 'view'" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="merchantForm.email" :disabled="dialogMode === 'view'" />
        </el-form-item>
        <el-form-item label="地址" prop="address">
          <el-input
            v-model="merchantForm.address"
            type="textarea"
            :rows="3"
            :disabled="dialogMode === 'view'"
          />
        </el-form-item>
        <el-form-item label="营业执照" prop="business_license">
          <el-input v-model="merchantForm.business_license" :disabled="dialogMode === 'view'" />
        </el-form-item>
        <el-form-item label="审核状态" prop="status" v-if="dialogMode === 'edit'">
          <el-select v-model="merchantForm.status">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已下线" value="offline" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button v-if="dialogMode === 'edit'" type="primary" @click="handleSave">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getMerchantList, updateMerchantStatus, updateMerchant } from '@/api/merchant'

// 响应式数据
const loading = ref(false)
const merchantList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const statusFilter = ref('')

// 对话框相关
const dialogVisible = ref(false)
const dialogMode = ref('view') // 'view' | 'edit'
const dialogTitle = ref('')
const merchantFormRef = ref(null)
const merchantForm = reactive({
  id: null,
  name: '',
  contact_name: '',
  contact_phone: '',
  email: '',
  address: '',
  business_license: '',
  status: ''
})

// 表单验证规则
const merchantRules = {
  name: [{ required: true, message: '请输入商家名称', trigger: 'blur' }],
  contact_name: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  contact_phone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  address: [{ required: true, message: '请输入地址', trigger: 'blur' }],
  business_license: [{ required: true, message: '请输入营业执照号', trigger: 'blur' }]
}

// 获取商家列表
const fetchMerchantList = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value
    }
    const response = await getMerchantList(params)
    merchantList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取商家列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  fetchMerchantList()
}

// 筛选处理
const handleFilter = () => {
  currentPage.value = 1
  fetchMerchantList()
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  fetchMerchantList()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchMerchantList()
}

// 查看商家详情
const handleView = (row) => {
  dialogMode.value = 'view'
  dialogTitle.value = '查看商家详情'
  Object.assign(merchantForm, row)
  dialogVisible.value = true
}

// 编辑商家
const handleEdit = (row) => {
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑商家信息'
  Object.assign(merchantForm, row)
  dialogVisible.value = true
}

// 保存编辑
const handleSave = async () => {
  if (!merchantFormRef.value) return
  
  await merchantFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await updateMerchant(merchantForm.id, merchantForm)
        ElMessage.success('保存成功')
        dialogVisible.value = false
        fetchMerchantList()
      } catch (error) {
        ElMessage.error('保存失败')
        console.error(error)
      }
    }
  })
}

// 审核通过
const handleApprove = async (row) => {
  try {
    await ElMessageBox.confirm('确认通过该商家审核？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await updateMerchantStatus(row.id, { status: 'approved' })
    ElMessage.success('审核通过')
    fetchMerchantList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
      console.error(error)
    }
  }
}

// 审核拒绝
const handleReject = async (row) => {
  try {
    await ElMessageBox.confirm('确认拒绝该商家审核？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await updateMerchantStatus(row.id, { status: 'rejected' })
    ElMessage.success('审核拒绝')
    fetchMerchantList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
      console.error(error)
    }
  }
}

// 下线商家
const handleOffline = async (row) => {
  try {
    await ElMessageBox.confirm('确认下线该商家？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await updateMerchantStatus(row.id, { status: 'offline' })
    ElMessage.success('商家已下线')
    fetchMerchantList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
      console.error(error)
    }
  }
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    offline: '已下线'
  }
  return statusMap[status] || status
}

// 获取状态标签类型
const getStatusType = (status) => {
  const typeMap = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    offline: 'info'
  }
  return typeMap[status] || ''
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 初始化
onMounted(() => {
  fetchMerchantList()
})
</script>

<style scoped>
.merchant-list-container {
  padding: 20px;
}

.page-title {
  margin-bottom: 20px;
  font-size: 24px;
  font-weight: bold;
}

.filters-section {
  margin-bottom: 20px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>