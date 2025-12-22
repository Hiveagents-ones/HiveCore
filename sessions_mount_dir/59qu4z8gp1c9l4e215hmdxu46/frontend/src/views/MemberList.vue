<template>
  <div class="member-list-container">
    <el-card class="box-card">
      <div class="column-selector">
        <el-select v-model="visibleColumns" multiple placeholder="选择显示列" style="margin-bottom: 15px">
          <el-option
            v-for="column in columnOptions"
            :key="column.value"
            :label="column.label"
            :value="column.value"
          />
        </el-select>
      </div>
      <template #header>
        <div class="card-header">
          <span>会员列表</span>
          <el-button type="primary" @click="handleCreate">新增会员</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="memberList" border style="width: 100%" :row-class-name="tableRowClassName" :default-sort="{ prop: 'join_date', order: 'descending' }">
        <el-table-column v-if="visibleColumns.includes('id')" prop="id" label="ID" width="80" sortable />
        <el-table-column v-if="visibleColumns.includes('name')" prop="name" label="姓名" width="120" sortable />
        <el-table-column v-if="visibleColumns.includes('phone')" prop="phone" label="电话" width="150" />
        <el-table-column v-if="visibleColumns.includes('email')" prop="email" label="邮箱" width="200" />
        <el-table-column v-if="visibleColumns.includes('join_date')" prop="join_date" label="加入日期" width="150" sortable />
        <el-table-column v-if="visibleColumns.includes('card_status')" prop="card_status" label="会员卡状态" width="120" :filters="[
          { text: '激活', value: 'active' },
          { text: '冻结', value: 'frozen' },
          { text: '过期', value: 'expired' }
        ]" :filter-method="filterStatus" />
        <el-table-column v-if="visibleColumns.includes('level_name')" prop="level_name" label="会员等级" width="120" :filters="[
          { text: '普通会员', value: '普通会员' },
          { text: '银卡会员', value: '银卡会员' },
          { text: '金卡会员', value: '金卡会员' },
          { text: '钻石会员', value: '钻石会员' }
        ]" :filter-method="filterLevel" />
        <el-table-column v-if="visibleColumns.includes('gender')" prop="gender" label="性别" width="80" :filters="[
          { text: '男', value: 'male' },
          { text: '女', value: 'female' }
        ]" :filter-method="filterGender" />
        <el-table-column v-if="visibleColumns.includes('birth_date')" prop="birth_date" label="生日" width="120" sortable />
        <el-table-column v-if="visibleColumns.includes('address')" prop="address" label="地址" width="200" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="fetchMembers"
        @current-change="fetchMembers"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="30%">
      <el-form :model="form" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="电话" required>
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="会员卡状态">
          <el-select v-model="form.card_status" placeholder="请选择状态">
            <el-option label="激活" value="active" />
            <el-option label="冻结" value="frozen" />
            <el-option label="过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item label="会员等级">
          <el-select v-model="form.level_name" placeholder="请选择等级">
            <el-option label="普通会员" value="普通会员" />
            <el-option label="银卡会员" value="银卡会员" />
            <el-option label="金卡会员" value="金卡会员" />
            <el-option label="钻石会员" value="钻石会员" />
          </el-select>
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
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMembers, createMember, updateMember, deleteMember } from '@/api'
import { useMemberStore } from '@/stores/member'
import { getMemberCards, getMemberLevel } from '@/api'

const memberList = ref([])
const memberStore = useMemberStore()
const visibleColumns = ref([
  'id',
  'name',
  'phone',
  'email',
  'join_date',
  'card_status',
  'level_name',
  'gender',
  'birth_date',
  'address'
])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const form = ref({
  id: null,
  name: '',
  phone: '',
  email: '',
  card_status: '',
  level_name: '',
  gender: '',
  birth_date: '',
  address: ''
})

const fetchMembers = async () => {
  // 使用Pinia缓存优化
  if (memberStore.hasCachedMembers) {
    memberList.value = memberStore.cachedMembers
    total.value = memberStore.cachedTotal
    return
  }
  loading.value = true
  try {
    const DEFAULT_FIELDS = ['id', 'name', 'phone', 'email', 'join_date', 'gender', 'birth_date', 'address']
    const DEFAULT_EXPAND = ['card_status', 'level_name']
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      fields: DEFAULT_FIELDS,
      expand: DEFAULT_EXPAND,
      _cache: true
    }
    const response = await getMembers(params)
    memberList.value = response.data.items
    // 更新Pinia缓存
    memberStore.setCachedMembers(response.data.items)
    memberStore.setCachedTotal(response.data.total)
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取会员列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  form.value = {
    id: null,
    name: '',
    phone: '',
    email: '',
    gender: '',
    birth_date: '',
    address: ''
  }
  dialogTitle.value = '新增会员'
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  try {
    const [cardResponse, levelResponse] = await Promise.all([
      getMemberCards(row.id),
      getMemberLevel(row.id)
    ])
    
    form.value = {
      id: row.id,
      name: row.name,
      phone: row.phone,
      email: row.email,
      gender: row.gender || '',
      birth_date: row.birth_date || '',
      address: row.address || '',
      card_status: cardResponse.data?.status || '',
      level_name: levelResponse.data?.name || ''
    }
    dialogTitle.value = '编辑会员'
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取会员详情失败')
    console.error(error)
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该会员吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteMember(row.id)
      ElMessage.success('删除成功')
      fetchMembers()
    } catch (error) {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }).catch(() => {})
}

const submitForm = async () => {
}

const tableRowClassName = ({ row }) => {
const filterStatus = (value, row) => {
  return row.card_status === value
}

const filterLevel = (value, row) => {
  return row.level_name === value
}

const filterGender = (value, row) => {
  return row.gender === value
}
const columnOptions = [
  { value: 'id', label: 'ID' },
  { value: 'name', label: '姓名' },
  { value: 'phone', label: '电话' },
  { value: 'email', label: '邮箱' },
  { value: 'join_date', label: '加入日期' },
  { value: 'card_status', label: '会员卡状态' },
  { value: 'level_name', label: '会员等级' },
  { value: 'gender', label: '性别' },
  { value: 'birth_date', label: '生日' },
  { value: 'address', label: '地址' }
]
  if (row.card_status === 'expired') {
    return 'warning-row'
  } else if (row.card_status === 'frozen') {
    return 'danger-row'
  }
  return ''
}
  try {
    if (form.value.id) {
      await updateMember(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createMember(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error('操作失败')
    console.error(error)
  }
}

onMounted(() => {
  fetchMembers()
})
</script>

<style scoped>
.el-table .warning-row {
  --el-table-tr-bg-color: var(--el-color-warning-light-9);
}
.el-table .danger-row {
  --el-table-tr-bg-color: var(--el-color-danger-light-9);
}
.member-list-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  display: flex;
  flex-wrap: wrap;
}

.column-selector {
  margin-bottom: 15px;
}
  margin-top: 20px;
  justify-content: flex-end;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
        <el-form-item label="会员卡状态">
          <el-input v-model="form.card_status" />
        </el-form-item>
        <el-form-item label="会员等级">
          <el-input v-model="form.level_name" />
        </el-form-item>