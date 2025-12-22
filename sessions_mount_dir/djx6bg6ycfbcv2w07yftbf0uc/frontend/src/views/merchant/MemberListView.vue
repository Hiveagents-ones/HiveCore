<template>
  <div class="member-list-view">
    <div class="page-header">
      <h1>会员管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          添加会员
        </el-button>
      </div>
    </div>

    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索会员姓名、手机号"
        @input="handleSearch"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="stats-cards">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value">{{ stats.totalMembers }}</div>
            <div class="stat-label">总会员数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value">{{ stats.activeMembers }}</div>
            <div class="stat-label">活跃会员</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value">¥{{ stats.totalConsumption }}</div>
            <div class="stat-label">总消费金额</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-value">{{ stats.newMembers }}</div>
            <div class="stat-label">本月新增</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-table
      v-loading="loading"
      :data="members"
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="phone" label="手机号" width="150" />
      <el-table-column prop="email" label="邮箱" width="200" />
      <el-table-column label="标签" width="200">
        <template #default="{ row }">
          <el-tag
            v-for="tag in row.tags"
            :key="tag"
            size="small"
            class="mr-1"
          >
            {{ tag }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="totalConsumption" label="消费金额" width="120">
        <template #default="{ row }">
          ¥{{ row.totalConsumption || 0 }}
        </template>
      </el-table-column>
      <el-table-column prop="appointmentCount" label="预约次数" width="120" />
      <el-table-column prop="createdAt" label="注册时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.createdAt) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewMemberDetail(row)">
            查看
          </el-button>
          <el-button size="small" type="primary" @click="editMember(row)">
            编辑
          </el-button>
          <el-button size="small" type="danger" @click="deleteMember(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 会员详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="会员详情"
      width="80%"
      destroy-on-close
    >
      <div v-if="selectedMember" class="member-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ selectedMember.name }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ selectedMember.phone }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ selectedMember.email }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ formatDate(selectedMember.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="消费金额">¥{{ selectedMember.totalConsumption || 0 }}</el-descriptions-item>
          <el-descriptions-item label="预约次数">{{ selectedMember.appointmentCount }}</el-descriptions-item>
        </el-descriptions>

        <div class="mt-4">
          <h3>标签管理</h3>
          <TagManager
            :tags="selectedMember.tags"
            @update="(tags) => updateMemberTags(selectedMember.id, tags)"
          />
        </div>

        <div class="mt-4">
          <h3>备注</h3>
          <NoteManager
            :note="selectedMember.note"
            @update="(note) => updateMemberNote(selectedMember.id, note)"
          />
        </div>

        <el-tabs v-model="activeTab" class="mt-4">
          <el-tab-pane label="预约记录" name="appointments">
            <el-table :data="appointments" v-loading="appointmentsLoading">
              <el-table-column prop="service" label="服务项目" />
              <el-table-column prop="date" label="预约日期" />
              <el-table-column prop="status" label="状态">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="消费记录" name="consumption">
            <el-table :data="consumption" v-loading="consumptionLoading">
              <el-table-column prop="item" label="消费项目" />
              <el-table-column prop="amount" label="金额">
                <template #default="{ row }">
                  ¥{{ row.amount }}
                </template>
              </el-table-column>
              <el-table-column prop="date" label="消费日期" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 创建/编辑会员对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingMember ? '编辑会员' : '添加会员'"
      width="50%"
      destroy-on-close
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
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="memberForm.phone" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="memberForm.email" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveMember" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { memberAPI } from '@/services/api'
import TagManager from '@/components/TagManager.vue'
import NoteManager from '@/components/NoteManager.vue'

// 数据状态
const loading = ref(false)
const members = ref([])
const selectedMember = ref(null)
const showDetailDialog = ref(false)
const showCreateDialog = ref(false)
const editingMember = ref(null)
const saving = ref(false)
const searchQuery = ref('')
const activeTab = ref('appointments')
const appointments = ref([])
const consumption = ref([])
const appointmentsLoading = ref(false)
const consumptionLoading = ref(false)
const selectedMembers = ref([])

// 统计数据
const stats = reactive({
  totalMembers: 0,
  activeMembers: 0,
  totalConsumption: 0,
  newMembers: 0
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 表单
const memberFormRef = ref(null)
const memberForm = reactive({
  name: '',
  phone: '',
  email: ''
})

const memberRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ]
}

// 方法
const fetchMembers = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      search: searchQuery.value
    }
    const response = await memberAPI.getMembers(params)
    members.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    ElMessage.error('获取会员列表失败')
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const response = await memberAPI.getMemberStats()
    Object.assign(stats, response)
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchMembers()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchMembers()
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  fetchMembers()
}

const handleSelectionChange = (selection) => {
  selectedMembers.value = selection
}

const viewMemberDetail = async (member) => {
  selectedMember.value = member
  showDetailDialog.value = true
  activeTab.value = 'appointments'
  await fetchMemberAppointments(member.id)
  await fetchMemberConsumption(member.id)
}

const fetchMemberAppointments = async (memberId) => {
  appointmentsLoading.value = true
  try {
    appointments.value = await memberAPI.getMemberAppointments(memberId)
  } catch (error) {
    ElMessage.error('获取预约记录失败')
  } finally {
    appointmentsLoading.value = false
  }
}

const fetchMemberConsumption = async (memberId) => {
  consumptionLoading.value = true
  try {
    consumption.value = await memberAPI.getMemberConsumption(memberId)
  } catch (error) {
    ElMessage.error('获取消费记录失败')
  } finally {
    consumptionLoading.value = false
  }
}

const editMember = (member) => {
  editingMember.value = member
  Object.assign(memberForm, {
    name: member.name,
    phone: member.phone,
    email: member.email
  })
  showCreateDialog.value = true
}

const saveMember = async () => {
  if (!memberFormRef.value) return
  
  try {
    await memberFormRef.value.validate()
    saving.value = true
    
    if (editingMember.value) {
      await memberAPI.updateMember(editingMember.value.id, memberForm)
      ElMessage.success('会员信息更新成功')
    } else {
      await memberAPI.createMember(memberForm)
      ElMessage.success('会员创建成功')
    }
    
    showCreateDialog.value = false
    editingMember.value = null
    resetForm()
    fetchMembers()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

const deleteMember = async (member) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除会员 "${member.name}" 吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await memberAPI.deleteMember(member.id)
    ElMessage.success('删除成功')
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const updateMemberTags = async (memberId, tags) => {
  try {
    await memberAPI.updateMemberTags(memberId, tags)
    ElMessage.success('标签更新成功')
    if (selectedMember.value?.id === memberId) {
      selectedMember.value.tags = tags
    }
    fetchMembers()
  } catch (error) {
    ElMessage.error('标签更新失败')
  }
}

const updateMemberNote = async (memberId, note) => {
  try {
    await memberAPI.updateMemberNote(memberId, note)
    ElMessage.success('备注更新成功')
    if (selectedMember.value?.id === memberId) {
      selectedMember.value.note = note
    }
    fetchMembers()
  } catch (error) {
    ElMessage.error('备注更新失败')
  }
}

const resetForm = () => {
  Object.assign(memberForm, {
    name: '',
    phone: '',
    email: ''
  })
  if (memberFormRef.value) {
    memberFormRef.value.resetFields()
  }
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const getStatusType = (status) => {
  const statusMap = {
    '已完成': 'success',
    '进行中': 'warning',
    '已取消': 'danger',
    '待确认': 'info'
  }
  return statusMap[status] || 'info'
}

// 监听对话框关闭
watch(showCreateDialog, (val) => {
  if (!val) {
    editingMember.value = null
    resetForm()
  }
})

// 初始化
onMounted(() => {
  fetchMembers()
  fetchStats()
})
</script>

<style scoped>
.member-list-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.search-bar {
  margin-bottom: 20px;
  max-width: 400px;
}

.stats-cards {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.member-detail {
  padding: 20px 0;
}

.mr-1 {
  margin-right: 4px;
}

.mt-4 {
  margin-top: 16px;
}
</style>