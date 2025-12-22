<template>
  <div class="member-list">
    <div class="page-header">
      <h1>{{ $t('members.title') }}</h1>
      <el-button type="primary" @click="handleAdd" v-if="hasPermission('member:create')">
        {{ $t('common.add') }}
      </el-button>
    </div>

    <div class="filter-bar">
      <el-form :inline="true" :model="filters" @submit.prevent="handleSearch">
        <el-form-item :label="$t('members.name')">
          <el-input v-model="filters.name" :placeholder="$t('members.namePlaceholder')" clearable />
        </el-form-item>
        <el-form-item :label="$t('members.level')">
          <el-select v-model="filters.level" :placeholder="$t('members.levelPlaceholder')" clearable>
            <el-option v-for="level in memberLevels" :key="level.value" :label="level.label" :value="level.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('members.status')">
          <el-select v-model="filters.status" :placeholder="$t('members.statusPlaceholder')" clearable>
            <el-option :label="$t('members.active')" value="active" />
            <el-option :label="$t('members.expired')" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">{{ $t('common.search') }}</el-button>
          <el-button @click="resetFilters">{{ $t('common.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table
      v-loading="loading"
      :data="members"
      stripe
      border
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="id" :label="$t('members.id')" width="80" sortable="custom" />
      <el-table-column prop="name" :label="$t('members.name')" min-width="120" sortable="custom" />
      <el-table-column prop="phone" :label="$t('members.phone')" min-width="120" />
      <el-table-column prop="email" :label="$t('members.email')" min-width="180" />
      <el-table-column prop="level" :label="$t('members.level')" width="100">
        <template #default="{ row }">
          <el-tag :type="getLevelTagType(row.level)">{{ getLevelLabel(row.level) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="effective_date" :label="$t('members.effectiveDate')" width="120" sortable="custom" />
      <el-table-column prop="expiry_date" :label="$t('members.expiryDate')" width="120" sortable="custom" />
      <el-table-column :label="$t('members.status')" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row)">{{ getStatusLabel(row) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.actions')" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleView(row)">{{ $t('common.view') }}</el-button>
          <el-button size="small" type="primary" @click="handleEdit(row)" v-if="hasPermission('member:update')">
            {{ $t('common.edit') }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)" v-if="hasPermission('member:delete')">
            {{ $t('common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- Member Form Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :close-on-click-modal="false"
    >
      <member-form
        ref="memberFormRef"
        :member="currentMember"
        :is-edit="isEdit"
        @submit="handleSubmit"
        @cancel="dialogVisible = false"
      />
    </el-dialog>

    <!-- Member Detail Dialog -->
    <el-dialog
      v-model="detailVisible"
      :title="$t('members.memberDetail')"
      width="600px"
    >
      <member-detail :member="currentMember" @close="detailVisible = false" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/composables/usePermission'
import { getMembers, deleteMember } from '@/api/members'
import MemberForm from '@/components/MemberForm.vue'
import MemberDetail from '@/components/MemberDetail.vue'

const { t } = useI18n()
const { hasPermission } = usePermission()

// State
const loading = ref(false)
const members = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const isEdit = ref(false)
const currentMember = ref(null)
const memberFormRef = ref(null)

// Filters
const filters = reactive({
  name: '',
  level: '',
  status: ''
})

// Pagination
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// Sorting
const sortBy = ref('id')
const sortOrder = ref('asc')

// Member levels
const memberLevels = computed(() => [
  { value: 'bronze', label: t('members.bronze') },
  { value: 'silver', label: t('members.silver') },
  { value: 'gold', label: t('members.gold') },
  { value: 'platinum', label: t('members.platinum') }
])

// Dialog title
const dialogTitle = computed(() => {
  return isEdit.value ? t('members.editMember') : t('members.addMember')
})

// Methods
const fetchMembers = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.size,
      limit: pagination.size,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      ...filters
    }
    
    // Remove empty filter values
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    
    const response = await getMembers(params)
    members.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    ElMessage.error(t('common.fetchError'))
    console.error('Error fetching members:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchMembers()
}

const resetFilters = () => {
  filters.name = ''
  filters.level = ''
  filters.status = ''
  pagination.page = 1
  fetchMembers()
}

const handleSortChange = ({ prop, order }) => {
  sortBy.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
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

const handleAdd = () => {
  isEdit.value = false
  currentMember.value = null
  dialogVisible.value = true
}

const handleEdit = (member) => {
  isEdit.value = true
  currentMember.value = { ...member }
  dialogVisible.value = true
}

const handleView = (member) => {
  currentMember.value = { ...member }
  detailVisible.value = true
}

const handleDelete = async (member) => {
  try {
    await ElMessageBox.confirm(
      t('members.deleteConfirm', { name: member.name }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    
    await deleteMember(member.id)
    ElMessage.success(t('common.deleteSuccess'))
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('common.deleteError'))
      console.error('Error deleting member:', error)
    }
  }
}

const handleSubmit = async () => {
  try {
    await memberFormRef.value.submit()
    dialogVisible.value = false
    ElMessage.success(isEdit.value ? t('common.updateSuccess') : t('common.createSuccess'))
    fetchMembers()
  } catch (error) {
    console.error('Error submitting form:', error)
  }
}

const getLevelTagType = (level) => {
  const types = {
    bronze: '',
    silver: 'info',
    gold: 'warning',
    platinum: 'success'
  }
  return types[level] || ''
}

const getLevelLabel = (level) => {
  const labels = {
    bronze: t('members.bronze'),
    silver: t('members.silver'),
    gold: t('members.gold'),
    platinum: t('members.platinum')
  }
  return labels[level] || level
}

const getStatusTagType = (member) => {
  const now = new Date()
  const expiryDate = new Date(member.expiry_date)
  return expiryDate >= now ? 'success' : 'danger'
}

const getStatusLabel = (member) => {
  const now = new Date()
  const expiryDate = new Date(member.expiry_date)
  return expiryDate >= now ? t('members.active') : t('members.expired')
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

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>