<template>
  <div class="member-list">
    <div class="header">
      <h2>{{ $t('member.list.title') }}</h2>
      <el-button type="primary" @click="handleCreate">{{ $t('member.list.create') }}</el-button>
    </div>

    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        :placeholder="$t('member.list.searchPlaceholder')"
        @input="handleSearch"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <el-table
      v-loading="memberStore.loading"
      :data="filteredMembers"
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="id" :label="$t('member.list.id')" width="80" />
      <el-table-column prop="name" :label="$t('member.list.name')" sortable="custom" />
      <el-table-column prop="phone" :label="$t('member.list.phone')" />
      <el-table-column prop="level" :label="$t('member.list.level')" sortable="custom">
        <template #default="scope">
          <el-tag :type="getLevelType(scope.row.level)">{{ scope.row.level }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remainingMembership" :label="$t('member.list.remainingMembership')" sortable="custom">
        <template #default="scope">
          {{ formatMembership(scope.row.remainingMembership) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('member.list.actions')" width="200">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">{{ $t('member.list.edit') }}</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">{{ $t('member.list.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="totalMembers"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="handleDialogClose"
    >
      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="memberRules"
        label-width="120px"
      >
        <el-form-item :label="$t('member.form.name')" prop="name">
          <el-input v-model="memberForm.name" />
        </el-form-item>
        <el-form-item :label="$t('member.form.phone')" prop="phone">
          <el-input v-model="memberForm.phone" />
        </el-form-item>
        <el-form-item :label="$t('member.form.level')" prop="level">
          <el-select v-model="memberForm.level" :placeholder="$t('member.form.selectLevel')">
            <el-option label="Bronze" value="Bronze" />
            <el-option label="Silver" value="Silver" />
            <el-option label="Gold" value="Gold" />
            <el-option label="Platinum" value="Platinum" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('member.form.remainingMembership')" prop="remainingMembership">
          <el-input-number v-model="memberForm.remainingMembership" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleSubmit">{{ $t('common.confirm') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMemberStore } from '@/stores/member'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const memberStore = useMemberStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const memberFormRef = ref(null)
const isEdit = ref(false)
const currentEditId = ref(null)

const memberForm = ref({
  name: '',
  phone: '',
  level: '',
  remainingMembership: 0
})

const memberRules = {
  name: [
    { required: true, message: t('member.form.nameRequired'), trigger: 'blur' }
  ],
  phone: [
    { required: true, message: t('member.form.phoneRequired'), trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: t('member.form.phoneInvalid'), trigger: 'blur' }
  ],
  level: [
    { required: true, message: t('member.form.levelRequired'), trigger: 'change' }
  ],
  remainingMembership: [
    { required: true, message: t('member.form.membershipRequired'), trigger: 'blur' }
  ]
}

const filteredMembers = computed(() => {
  let members = memberStore.members
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    members = members.filter(member => 
      member.name.toLowerCase().includes(query) ||
      member.phone.includes(query) ||
      member.level.toLowerCase().includes(query)
    )
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return members.slice(start, end)
})

const totalMembers = computed(() => {
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    return memberStore.members.filter(member => 
      member.name.toLowerCase().includes(query) ||
      member.phone.includes(query) ||
      member.level.toLowerCase().includes(query)
    ).length
  }
  return memberStore.members.length
})

const getLevelType = (level) => {
  const types = {
    Bronze: 'info',
    Silver: '',
    Gold: 'warning',
    Platinum: 'success'
  }
  return types[level] || ''
}

const formatMembership = (days) => {
  return t('member.list.membershipDays', { days })
}

const handleSearch = () => {
  currentPage.value = 1
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

const handleSortChange = ({ prop, order }) => {
  memberStore.members.sort((a, b) => {
    if (order === 'ascending') {
      return a[prop] > b[prop] ? 1 : -1
    } else if (order === 'descending') {
      return a[prop] < b[prop] ? 1 : -1
    }
    return 0
  })
}

const handleCreate = () => {
  isEdit.value = false
  dialogTitle.value = t('member.list.createMember')
  memberForm.value = {
    name: '',
    phone: '',
    level: '',
    remainingMembership: 0
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  currentEditId.value = row.id
  dialogTitle.value = t('member.list.editMember')
  memberForm.value = { ...row }
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    t('member.list.deleteConfirm'),
    t('common.warning'),
    {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    }
  ).then(async () => {
    try {
      await memberStore.deleteMember(row.id)
      ElMessage.success(t('member.list.deleteSuccess'))
    } catch (error) {
      ElMessage.error(t('member.list.deleteError'))
    }
  }).catch(() => {
    ElMessage.info(t('common.cancelled'))
  })
}

const handleSubmit = async () => {
  if (!memberFormRef.value) return
  
  await memberFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          await memberStore.updateMember(currentEditId.value, memberForm.value)
          ElMessage.success(t('member.list.updateSuccess'))
        } else {
          await memberStore.createMember(memberForm.value)
          ElMessage.success(t('member.list.createSuccess'))
        }
        dialogVisible.value = false
      } catch (error) {
        ElMessage.error(isEdit.value ? t('member.list.updateError') : t('member.list.createError'))
      }
    }
  })
}

const handleDialogClose = () => {
  if (memberFormRef.value) {
    memberFormRef.value.resetFields()
  }
}

onMounted(() => {
  memberStore.fetchMembers()
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

.search-bar {
  margin-bottom: 20px;
  max-width: 400px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>