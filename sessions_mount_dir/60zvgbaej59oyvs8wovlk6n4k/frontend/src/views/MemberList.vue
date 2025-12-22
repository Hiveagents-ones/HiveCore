<template>
  <div class="member-list">
    <el-card class="filter-card">
      <el-form :inline="true" :model="queryParams" class="filter-form">
        <el-form-item :label="$t('member.name')">
          <el-input
            v-model="queryParams.name"
            :placeholder="$t('member.namePlaceholder')"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item :label="$t('member.cardNumber')">
          <el-input
            v-model="queryParams.card_number"
            :placeholder="$t('member.cardNumberPlaceholder')"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item :label="$t('member.level')">
          <el-select
            v-model="queryParams.level"
            :placeholder="$t('member.levelPlaceholder')"
            clearable
          >
            <el-option
              v-for="level in memberLevels"
              :key="level.value"
              :label="level.label"
              :value="level.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">
            {{ $t('common.search') }}
          </el-button>
          <el-button @click="resetQuery">
            {{ $t('common.reset') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <div class="table-header">
        <el-button type="primary" @click="handleAdd">
          {{ $t('common.add') }}
        </el-button>
        <el-button
          type="danger"
          :disabled="!selectedMembers.length"
          @click="handleBatchDelete"
        >
          {{ $t('common.batchDelete') }}
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="memberList"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column
          prop="name"
          :label="$t('member.name')"
          min-width="120"
        />
        <el-table-column
          prop="card_number"
          :label="$t('member.cardNumber')"
          min-width="150"
        />
        <el-table-column
          prop="phone"
          :label="$t('member.phone')"
          min-width="120"
        />
        <el-table-column
          prop="level"
          :label="$t('member.level')"
          min-width="100"
        >
          <template #default="scope">
            <el-tag :type="getLevelTagType(scope.row.level)">
              {{ getLevelLabel(scope.row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="remaining_days"
          :label="$t('member.remainingDays')"
          min-width="120"
        >
          <template #default="scope">
            <span :class="getRemainingDaysClass(scope.row.remaining_days)">
              {{ scope.row.remaining_days }} {{ $t('common.days') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          :label="$t('common.createdAt')"
          min-width="160"
        >
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('common.actions')"
          width="200"
          fixed="right"
        >
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="handleEdit(scope.row)"
            >
              {{ $t('common.edit') }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(scope.row)"
            >
              {{ $t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Member Form Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="memberRules"
        label-width="120px"
      >
        <el-form-item :label="$t('member.name')" prop="name">
          <el-input v-model="memberForm.name" />
        </el-form-item>
        <el-form-item :label="$t('member.phone')" prop="phone">
          <el-input v-model="memberForm.phone" />
        </el-form-item>
        <el-form-item :label="$t('member.cardNumber')" prop="card_number">
          <el-input v-model="memberForm.card_number" />
        </el-form-item>
        <el-form-item :label="$t('member.level')" prop="level">
          <el-select v-model="memberForm.level" style="width: 100%">
            <el-option
              v-for="level in memberLevels"
              :key="level.value"
              :label="level.label"
              :value="level.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('member.remainingDays')" prop="remaining_days">
          <el-input-number
            v-model="memberForm.remaining_days"
            :min="0"
            :max="3650"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">
          {{ $t('common.cancel') }}
        </el-button>
        <el-button type="primary" @click="handleSubmit">
          {{ $t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Query parameters
const queryParams = reactive({
  page: 1,
  size: 10,
  name: '',
  card_number: '',
  level: ''
})

// Data
const loading = ref(false)
const memberList = ref([])
const total = ref(0)
const selectedMembers = ref([])

// Dialog
const dialogVisible = ref(false)
const dialogTitle = ref('')
const memberFormRef = ref(null)
const memberForm = reactive({
  id: null,
  name: '',
  phone: '',
  card_number: '',
  level: '',
  remaining_days: 0
})

// Member levels
const memberLevels = [
  { value: 'bronze', label: t('member.levels.bronze') },
  { value: 'silver', label: t('member.levels.silver') },
  { value: 'gold', label: t('member.levels.gold') },
  { value: 'platinum', label: t('member.levels.platinum') }
]

// Form rules
const memberRules = {
  name: [
    { required: true, message: t('member.rules.nameRequired'), trigger: 'blur' }
  ],
  phone: [
    { required: true, message: t('member.rules.phoneRequired'), trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: t('member.rules.phoneInvalid'), trigger: 'blur' }
  ],
  card_number: [
    { required: true, message: t('member.rules.cardNumberRequired'), trigger: 'blur' }
  ],
  level: [
    { required: true, message: t('member.rules.levelRequired'), trigger: 'change' }
  ],
  remaining_days: [
    { required: true, message: t('member.rules.remainingDaysRequired'), trigger: 'blur' }
  ]
}

// Methods
const fetchMembers = async () => {
  try {
    loading.value = true
    const response = await api.get('/members', queryParams)
    memberList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch members:', error)
  } finally {
    loading.value = false
  }
}

const handleQuery = () => {
  queryParams.page = 1
  fetchMembers()
}

const resetQuery = () => {
  queryParams.name = ''
  queryParams.card_number = ''
  queryParams.level = ''
  handleQuery()
}

const handleSizeChange = (val) => {
  queryParams.size = val
  fetchMembers()
}

const handleCurrentChange = (val) => {
  queryParams.page = val
  fetchMembers()
}

const handleSelectionChange = (selection) => {
  selectedMembers.value = selection
}

const handleAdd = () => {
  dialogTitle.value = t('member.addMember')
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = t('member.editMember')
  Object.assign(memberForm, row)
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      t('member.deleteConfirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    await api.delete(`/members/${row.id}`)
    ElMessage.success(t('member.deleteSuccess'))
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete member:', error)
    }
  }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      t('member.batchDeleteConfirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    const ids = selectedMembers.value.map(item => item.id)
    await api.delete('/members', { data: { ids } })
    ElMessage.success(t('member.batchDeleteSuccess'))
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to batch delete members:', error)
    }
  }
}

const handleSubmit = async () => {
  if (!memberFormRef.value) return
  
  try {
    await memberFormRef.value.validate()
    
    if (memberForm.id) {
      await api.put(`/members/${memberForm.id}`, memberForm)
      ElMessage.success(t('member.updateSuccess'))
    } else {
      await api.post('/members', memberForm)
      ElMessage.success(t('member.createSuccess'))
    }
    
    dialogVisible.value = false
    fetchMembers()
  } catch (error) {
    console.error('Failed to submit form:', error)
  }
}

const handleDialogClose = () => {
  resetForm()
}

const resetForm = () => {
  if (memberFormRef.value) {
    memberFormRef.value.resetFields()
  }
  memberForm.id = null
  memberForm.name = ''
  memberForm.phone = ''
  memberForm.card_number = ''
  memberForm.level = ''
  memberForm.remaining_days = 0
}

// Helper functions
const getLevelTagType = (level) => {
  const types = {
    bronze: 'info',
    silver: '',
    gold: 'warning',
    platinum: 'success'
  }
  return types[level] || ''
}

const getLevelLabel = (level) => {
  const levelObj = memberLevels.find(item => item.value === level)
  return levelObj ? levelObj.label : level
}

const getRemainingDaysClass = (days) => {
  if (days <= 30) return 'text-danger'
  if (days <= 90) return 'text-warning'
  return ''
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString()
}

// Lifecycle
onMounted(() => {
  fetchMembers()
})
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.table-card {
  margin-bottom: 20px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.text-danger {
  color: #f56c6c;
}

.text-warning {
  color: #e6a23c;
}
</style>
