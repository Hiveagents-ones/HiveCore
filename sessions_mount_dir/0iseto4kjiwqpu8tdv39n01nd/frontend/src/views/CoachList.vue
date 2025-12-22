<template>
  <div class="coach-list">
    <div class="page-header">
      <h1>教练列表</h1>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        添加教练
      </el-button>
    </div>

    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索教练姓名或手机号"
        @input="handleSearch"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <el-table
      v-loading="loading"
      :data="coachList"
      style="width: 100%"
      stripe
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" min-width="120" />
      <el-table-column prop="phone" label="手机号" min-width="120" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="specialties" label="专长" min-width="150">
        <template #default="{ row }">
          <el-tag
            v-for="specialty in row.specialties"
            :key="specialty"
            size="small"
            class="mr-1"
          >
            {{ specialty }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
            {{ row.status === 'active' ? '在职' : '离职' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            @click="handleView(row.id)"
          >
            查看
          </el-button>
          <el-button
            type="warning"
            size="small"
            @click="handleEdit(row.id)"
          >
            编辑
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { getCoaches, deleteCoach } from '@/api/coach'

const router = useRouter()
const loading = ref(false)
const coachList = ref([])
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const fetchCoaches = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value
    }
    const response = await getCoaches(params)
    coachList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取教练列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchCoaches()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchCoaches()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchCoaches()
}

const handleCreate = () => {
  router.push('/coaches/create')
}

const handleView = (id) => {
  router.push(`/coaches/${id}`)
}

const handleEdit = (id) => {
  router.push(`/coaches/${id}/edit`)
}

const handleDelete = (coach) => {
  ElMessageBox.confirm(
    `确定要删除教练 "${coach.name}" 吗？此操作不可恢复。`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteCoach(coach.id)
      ElMessage.success('删除成功')
      fetchCoaches()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 用户取消删除
  })
}

onMounted(() => {
  fetchCoaches()
})
</script>

<style scoped>
.coach-list {
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

.search-bar {
  margin-bottom: 20px;
}

.search-bar .el-input {
  max-width: 400px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.mr-1 {
  margin-right: 4px;
}
</style>