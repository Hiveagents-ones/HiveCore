<template>
  <div class="member-list">
    <div class="header">
      <h2>会员管理</h2>
      <div class="actions">
        <el-button type="primary" @click="showCreateDialog">新增会员</el-button>
        <el-button @click="showImportDialog">批量导入</el-button>
        <el-button @click="handleExport">批量导出</el-button>
      </div>
    </div>

    <div class="filters">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="搜索">
          <el-input
            v-model="filters.keyword"
            placeholder="姓名/手机号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="会员状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="活跃" value="active" />
            <el-option label="冻结" value="frozen" />
            <el-option label="过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item label="会员卡类型">
          <el-select v-model="filters.cardType" placeholder="全部" clearable>
            <el-option label="月卡" value="monthly" />
            <el-option label="季卡" value="quarterly" />
            <el-option label="年卡" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value">{{ memberStats.total }}</div>
            <div class="stat-label">总会员数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value active">{{ memberStats.active }}</div>
            <div class="stat-label">活跃会员</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value frozen">{{ memberStats.frozen }}</div>
            <div class="stat-label">冻结会员</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value expired">{{ memberStats.expired }}</div>
            <div class="stat-label">过期会员</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="members"
        @selection-change="handleSelectionChange"
        stripe
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="{ row }">
            {{ row.gender === 'male' ? '男' : '女' }}
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="cardType" label="会员卡类型" width="120">
          <template #default="{ row }">
            {{ getCardTypeLabel(row.cardType) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expireDate" label="到期日期" width="120" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewMember(row.id)">详情</el-button>
            <el-button size="small" type="primary" @click="editMember(row)">编辑</el-button>
            <el-dropdown @command="(command) => handleCommand(command, row)">
              <el-button size="small">
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="renew">续费</el-dropdown-item>
                  <el-dropdown-item command="upgrade">升级</el-dropdown-item>
                  <el-dropdown-item command="toggle">
                    {{ row.status === 'frozen' ? '解冻' : '冻结' }}
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 新增/编辑会员对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑会员' : '新增会员'"
      width="600px"
    >
      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="memberRules"
        label-width="100px"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="memberForm.name" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="memberForm.gender">
            <el-radio label="male">男</el-radio>
            <el-radio label="female">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年龄" prop="age">
          <el-input-number v-model="memberForm.age" :min="1" :max="120" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="memberForm.phone" />
        </el-form-item>
        <el-form-item label="会员卡类型" prop="cardType">
          <el-select v-model="memberForm.cardType">
            <el-option label="月卡" value="monthly" />
            <el-option label="季卡" value="quarterly" />
            <el-option label="年卡" value="yearly" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMember" :loading="loading">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="批量导入会员" width="500px">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            请上传xlsx或xls格式的会员信息文件
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="loading">
          导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 续费对话框 -->
    <el-dialog v-model="renewDialogVisible" title="会员卡续费" width="400px">
      <el-form :model="renewForm" label-width="100px">
        <el-form-item label="续费时长">
          <el-select v-model="renewForm.duration">
            <el-option label="1个月" value="1" />
            <el-option label="3个月" value="3" />
            <el-option label="6个月" value="6" />
            <el-option label="12个月" value="12" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="renewForm.paymentMethod">
            <el-option label="现金" value="cash" />
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="银行卡" value="card" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRenew" :loading="loading">
          确认续费
        </el-button>
      </template>
    </el-dialog>

    <!-- 升级对话框 -->
    <el-dialog v-model="upgradeDialogVisible" title="升级会员卡" width="400px">
      <el-form :model="upgradeForm" label-width="100px">
        <el-form-item label="目标卡类型">
          <el-select v-model="upgradeForm.targetType">
            <el-option label="季卡" value="quarterly" />
            <el-option label="年卡" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="upgradeForm.paymentMethod">
            <el-option label="现金" value="cash" />
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="银行卡" value="card" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="upgradeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpgrade" :loading="loading">
          确认升级
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, UploadFilled } from '@element-plus/icons-vue'
import { useMemberStore } from '../stores/member'
import * as memberApi from '../api/member'

const router = useRouter()
const memberStore = useMemberStore()

// 响应式数据
const loading = ref(false)
const selectedMembers = ref([])
const dialogVisible = ref(false)
const importDialogVisible = ref(false)
const renewDialogVisible = ref(false)
const upgradeDialogVisible = ref(false)
const isEdit = ref(false)
const currentMemberId = ref(null)

// 筛选条件
const filters = reactive({
  keyword: '',
  status: '',
  cardType: ''
})

// 会员表单
const memberFormRef = ref()
const memberForm = reactive({
  name: '',
  gender: 'male',
  age: 20,
  phone: '',
  cardType: 'monthly'
})

// 表单验证规则
const memberRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  age: [{ required: true, message: '请输入年龄', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  cardType: [{ required: true, message: '请选择会员卡类型', trigger: 'change' }]
}

// 续费表单
const renewForm = reactive({
  duration: '1',
  paymentMethod: 'cash'
})

// 升级表单
const upgradeForm = reactive({
  targetType: 'quarterly',
  paymentMethod: 'cash'
})

// 上传引用
const uploadRef = ref()

// 计算属性
const members = computed(() => memberStore.members)
const pagination = computed(() => memberStore.pagination)
const memberStats = computed(() => memberStore.memberStats)

// 方法
const fetchMembers = async () => {
  try {
    loading.value = true
    await memberStore.fetchMembers(filters)
  } catch (error) {
    ElMessage.error('获取会员列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.value.page = 1
  fetchMembers()
}

const resetFilters = () => {
  Object.assign(filters, {
    keyword: '',
    status: '',
    cardType: ''
  })
  handleSearch()
}

const handleSelectionChange = (selection) => {
  selectedMembers.value = selection
}

const handleSizeChange = (size) => {
  pagination.value.pageSize = size
  fetchMembers()
}

const handleCurrentChange = (page) => {
  pagination.value.page = page
  fetchMembers()
}

const showCreateDialog = () => {
  isEdit.value = false
  resetMemberForm()
  dialogVisible.value = true
}

const showImportDialog = () => {
  importDialogVisible.value = true
}

const resetMemberForm = () => {
  Object.assign(memberForm, {
    name: '',
    gender: 'male',
    age: 20,
    phone: '',
    cardType: 'monthly'
  })
}

const saveMember = async () => {
  try {
    await memberFormRef.value.validate()
    loading.value = true
    
    if (isEdit.value) {
      await memberStore.updateMember(currentMemberId.value, memberForm)
      ElMessage.success('更新成功')
    } else {
      await memberStore.createMember(memberForm)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    loading.value = false
  }
}

const editMember = (member) => {
  isEdit.value = true
  currentMemberId.value = member.id
  Object.assign(memberForm, member)
  dialogVisible.value = true
}

const viewMember = (id) => {
  router.push(`/members/${id}`)
}

const handleCommand = async (command, member) => {
  currentMemberId.value = member.id
  
  switch (command) {
    case 'renew':
      renewDialogVisible.value = true
      break
    case 'upgrade':
      upgradeDialogVisible.value = true
      break
    case 'toggle':
      await toggleMemberStatus(member)
      break
    case 'delete':
      await deleteMember(member)
      break
  }
}

const toggleMemberStatus = async (member) => {
  try {
    const action = member.status === 'frozen' ? '解冻' : '冻结'
    await ElMessageBox.confirm(`确定要${action}该会员吗？`, '提示', {
      type: 'warning'
    })
    
    await memberApi.toggleMemberStatus(member.id, {
      status: member.status === 'frozen' ? 'active' : 'frozen'
    })
    
    ElMessage.success(`${action}成功`)
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const deleteMember = async (member) => {
  try {
    await ElMessageBox.confirm('确定要删除该会员吗？此操作不可恢复', '警告', {
      type: 'warning'
    })
    
    await memberStore.deleteMember(member.id)
    ElMessage.success('删除成功')
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleImport = async () => {
  try {
    const file = uploadRef.value.uploadFiles[0]
    if (!file) {
      ElMessage.warning('请选择要导入的文件')
      return
    }
    
    loading.value = true
    const formData = new FormData()
    formData.append('file', file.raw)
    
    await memberApi.batchImportMembers(formData)
    ElMessage.success('导入成功')
    importDialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error('导入失败')
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  try {
    loading.value = true
    const response = await memberApi.batchExportMembers(filters)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `members_${new Date().getTime()}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    loading.value = false
  }
}

const confirmRenew = async () => {
  try {
    loading.value = true
    await memberApi.renewMembership(currentMemberId.value, renewForm)
    ElMessage.success('续费成功')
    renewDialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error('续费失败')
  } finally {
    loading.value = false
  }
}

const confirmUpgrade = async () => {
  try {
    loading.value = true
    await memberApi.upgradeMembership(currentMemberId.value, upgradeForm)
    ElMessage.success('升级成功')
    upgradeDialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error('升级失败')
  } finally {
    loading.value = false
  }
}

// 辅助函数
const getCardTypeLabel = (type) => {
  const map = {
    monthly: '月卡',
    quarterly: '季卡',
    yearly: '年卡'
  }
  return map[type] || type
}

const getStatusType = (status) => {
  const map = {
    active: 'success',
    frozen: 'info',
    expired: 'danger'
  }
  return map[status] || ''
}

const getStatusLabel = (status) => {
  const map = {
    active: '活跃',
    frozen: '冻结',
    expired: '过期'
  }
  return map[status] || status
}

// 生命周期
onMounted(() => {
  fetchMembers()
})
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.actions {
  display: flex;
  gap: 10px;
}

.filters {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.filter-form {
  margin: 0;
}

.stats {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-value.active {
  color: #67c23a;
}

.stat-value.frozen {
  color: #909399;
}

.stat-value.expired {
  color: #f56c6c;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.table-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-upload-dragger) {
  width: 100%;
}
</style>