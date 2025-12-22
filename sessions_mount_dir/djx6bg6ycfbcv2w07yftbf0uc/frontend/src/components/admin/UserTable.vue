<template>
  <div class="user-table">
    <el-table
      v-loading="loading"
      :data="users"
      stripe
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
            {{ row.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
            {{ row.status === 'active' ? '正常' : '已封禁' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'active'"
            type="danger"
            size="small"
            @click="handleBan(row)"
          >
            封禁
          </el-button>
          <el-button
            v-else
            type="success"
            size="small"
            @click="handleUnban(row)"
          >
            解封
          </el-button>
          <el-button
            type="primary"
            size="small"
            @click="handleViewDetails(row)"
          >
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper">
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
import { ref, defineProps, defineEmits } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({
  users: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  total: {
    type: Number,
    default: 0
  },
  currentPage: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 10
  }
})

const emit = defineEmits([
  'selection-change',
  'ban',
  'unban',
  'view-details',
  'update:currentPage',
  'update:pageSize',
  'size-change',
  'current-change'
])

const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

const handleBan = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要封禁用户 "${user.username}" 吗？`,
      '确认封禁',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    emit('ban', user)
    ElMessage.success('封禁成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('封禁失败')
    }
  }
}

const handleUnban = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要解封用户 "${user.username}" 吗？`,
      '确认解封',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    emit('unban', user)
    ElMessage.success('解封成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('解封失败')
    }
  }
}

const handleViewDetails = (user) => {
  emit('view-details', user)
}

const handleSizeChange = (val) => {
  emit('update:pageSize', val)
  emit('size-change', val)
}

const handleCurrentChange = (val) => {
  emit('update:currentPage', val)
  emit('current-change', val)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.user-table {
  background: #fff;
  border-radius: 4px;
  padding: 20px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>