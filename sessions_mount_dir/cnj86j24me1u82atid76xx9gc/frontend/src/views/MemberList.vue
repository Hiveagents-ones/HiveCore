<template>
  <div class="member-list">
    <div class="page-header">
      <h1>会员管理</h1>
      <el-button type="primary" @click="handleAdd" v-if="hasPermission('member:create')">
        <el-icon><Plus /></el-icon>
        新增会员
      </el-button>
    </div>

    <!-- 高级查询区域 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="searchForm.contact" placeholder="请输入联系方式" clearable />
        </el-form-item>
        <el-form-item label="会员等级">
          <el-select v-model="searchForm.level" placeholder="请选择" clearable>
            <el-option label="普通会员" value="normal" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable>
            <el-option label="正常" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 会员列表 -->
    <el-card class="table-card">
      <el-table
        :data="memberList"
        v-loading="loading"
        stripe
        @sort-change="handleSortChange"
      >
        <el-table-column prop="id" label="ID" width="80" sortable="custom" />
        <el-table-column prop="name" label="姓名" min-width="120" sortable="custom" />
        <el-table-column prop="contact" label="联系方式" min-width="150" />
        <el-table-column prop="level" label="会员等级" width="120" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)">{{ getLevelText(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remainingDays" label="剩余会籍(天)" width="140" sortable="custom" />
        <el-table-column prop="status" label="状态" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" sortable="custom" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              @click="handleView(row)"
              v-if="hasPermission('member:view')"
            >
              查看
            </el-button>
            <el-button
              type="primary"
              link
              @click="handleEdit(row)"
              v-if="hasPermission('member:update')"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              link
              @click="handleDelete(row)"
              v-if="hasPermission('member:delete')"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 会员表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      destroy-on-close
    >
      <member-form
        :member="currentMember"
        :mode="formMode"
        @success="handleFormSuccess"
        @cancel="dialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import MemberForm from '@/components/MemberForm.vue'
import { getMemberList, deleteMember } from '@/api/member'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const memberList = ref([])
const dialogVisible = ref(false)
const currentMember = ref(null)
const formMode = ref('create')

// 搜索表单
const searchForm = reactive({
  name: '',
  contact: '',
  level: '',
  status: ''
})

// 排序参数
const sortParams = reactive({
  prop: '',
  order: ''
})

// 分页参数
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 计算属性
const dialogTitle = computed(() => {
  return formMode.value === 'create' ? '新增会员' : '编辑会员'
})

// 权限检查
const hasPermission = (permission) => {
  return userStore.permissions.includes(permission)
}

// 获取会员等级类型
const getLevelType = (level) => {
  const types = {
    normal: '',
    silver: 'info',
    gold: 'warning',
    diamond: 'success'
  }
  return types[level] || ''
}

// 获取会员等级文本
const getLevelText = (level) => {
  const texts = {
    normal: '普通会员',
    silver: '银卡会员',
    gold: '金卡会员',
    diamond: '钻石会员'
  }
  return texts[level] || level
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    active: 'success',
    paused: 'warning',
    expired: 'danger'
  }
  return types[status] || ''
}

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    active: '正常',
    paused: '暂停',
    expired: '过期'
  }
  return texts[status] || status
}

// 获取会员列表
const fetchMemberList = async () => {
  try {
    loading.value = true
    const params = {
      page: pagination.currentPage,
      size: pagination.pageSize,
      ...searchForm,
      sortProp: sortParams.prop,
      sortOrder: sortParams.order
    }
    const res = await getMemberList(params)
    memberList.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    ElMessage.error('获取会员列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.currentPage = 1
  fetchMemberList()
}

// 重置搜索
const resetSearch = () => {
  Object.keys(searchForm).forEach(key => {
    searchForm[key] = ''
  })
  sortParams.prop = ''
  sortParams.order = ''
  pagination.currentPage = 1
  fetchMemberList()
}

// 排序变化
const handleSortChange = ({ prop, order }) => {
  sortParams.prop = prop
  sortParams.order = order
  fetchMemberList()
}

// 分页大小变化
const handleSizeChange = (val) => {
  pagination.pageSize = val
  pagination.currentPage = 1
  fetchMemberList()
}

// 当前页变化
const handleCurrentChange = (val) => {
  pagination.currentPage = val
  fetchMemberList()
}

// 新增会员
const handleAdd = () => {
  formMode.value = 'create'
  currentMember.value = null
  dialogVisible.value = true
}

// 查看会员
const handleView = (row) => {
  formMode.value = 'view'
  currentMember.value = { ...row }
  dialogVisible.value = true
}

// 编辑会员
const handleEdit = (row) => {
  formMode.value = 'edit'
  currentMember.value = { ...row }
  dialogVisible.value = true
}

// 删除会员
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除会员 "${row.name}" 吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteMember(row.id)
      ElMessage.success('删除成功')
      fetchMemberList()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 表单成功回调
const handleFormSuccess = () => {
  dialogVisible.value = false
  fetchMemberList()
}

// 初始化
onMounted(() => {
  fetchMemberList()
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

.search-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>