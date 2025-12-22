<template>
  <div class="activity-manage">
    <div class="page-header">
      <h2>活动管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建活动
      </el-button>
    </div>

    <div class="filter-bar">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-input
            v-model="searchQuery"
            placeholder="搜索活动名称"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select
            v-model="statusFilter"
            placeholder="活动状态"
            clearable
            @change="handleSearch"
          >
            <el-option label="全部" value="" />
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-col>
      </el-row>
    </div>

    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="activities"
        @selection-change="handleSelectionChange"
        @sort-change="handleSortChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="活动名称" sortable="custom" />
        <el-table-column prop="start_time" label="开始时间" sortable="custom">
          <template #default="{ row }">
            {{ formatDate(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" sortable="custom">
          <template #default="{ row }">
            {{ formatDate(row.end_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="location" label="活动地点" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'draft'"
              size="small"
              type="success"
              @click="handlePublish(row)"
            >
              发布
            </el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              type="warning"
              @click="handleUnpublish(row)"
            >
              下架
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

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
    </div>

    <div v-if="selectedActivities.length > 0" class="batch-actions">
      <span>已选择 {{ selectedActivities.length }} 项</span>
      <el-button type="danger" @click="handleBatchDelete">批量删除</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { activityApi } from '../../services/api'

const router = useRouter()

// 状态管理
const loading = ref(false)
const activities = ref([])
const selectedActivities = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')

// 排序状态
const sortProp = ref('')
const sortOrder = ref('')

// 获取活动列表
const fetchActivities = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value,
    }
    
    if (sortProp.value) {
      params.sort_by = sortProp.value
      params.sort_order = sortOrder.value
    }

    const response = await activityApi.getActivities(params)
    activities.value = response.items || []
    total.value = response.total || 0
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  fetchActivities()
}

// 重置筛选
const resetFilter = () => {
  searchQuery.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  fetchActivities()
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchActivities()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchActivities()
}

// 排序处理
const handleSortChange = ({ prop, order }) => {
  sortProp.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  fetchActivities()
}

// 选择处理
const handleSelectionChange = (selection) => {
  selectedActivities.value = selection
}

// 创建活动
const handleCreate = () => {
  router.push('/merchant/activities/create')
}

// 编辑活动
const handleEdit = (row) => {
  router.push(`/merchant/activities/${row.id}/edit`)
}

// 发布活动
const handlePublish = async (row) => {
  try {
    await activityApi.publishActivity(row.id)
    ElMessage.success('活动发布成功')
    fetchActivities()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

// 下架活动
const handleUnpublish = async (row) => {
  try {
    await activityApi.unpublishActivity(row.id)
    ElMessage.success('活动下架成功')
    fetchActivities()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

// 删除活动
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个活动吗？',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await activityApi.deleteActivity(row.id)
    ElMessage.success('删除成功')
    fetchActivities()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message)
    }
  }
}

// 批量删除
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedActivities.value.length} 个活动吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    const deletePromises = selectedActivities.value.map(activity => 
      activityApi.deleteActivity(activity.id)
    )
    
    await Promise.all(deletePromises)
    ElMessage.success('批量删除成功')
    selectedActivities.value = []
    fetchActivities()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message)
    }
  }
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    draft: 'info',
    published: 'success',
    ended: 'warning',
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    draft: '草稿',
    published: '已发布',
    ended: '已结束',
  }
  return statusMap[status] || status
}

// 初始化
onMounted(() => {
  fetchActivities()
})
</script>

<style scoped>
.activity-manage {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filter-bar {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.table-container {
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.pagination-container {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}

.batch-actions {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  padding: 10px 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-actions span {
  color: #606266;
  font-size: 14px;
}
</style>