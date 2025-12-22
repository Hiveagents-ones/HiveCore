<template>
  <div class="member-list-container">
    <el-card class="filter-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="searchForm.contact" placeholder="请输入联系方式" clearable />
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input v-model="searchForm.id_card" placeholder="请输入身份证号" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <div class="table-header">
        <h3>会员列表</h3>
        <el-button type="primary" @click="handleAdd">新增会员</el-button>
      </div>
      
      <el-table 
        :data="memberList" 
        v-loading="loading" 
        style="width: 100%"
        stripe
        border
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="contact" label="联系方式" width="150" />
        <el-table-column prop="id_card" label="身份证号" width="180" />
        <el-table-column prop="health_status" label="健康状况" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const router = useRouter()

const loading = ref(false)
const memberList = ref([])

const searchForm = reactive({
  name: '',
  contact: '',
  id_card: ''
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const fetchMembers = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      size: pagination.pageSize,
      ...searchForm
    }
    
    const response = await request.get('/api/members', { params })
    memberList.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    ElMessage.error('获取会员列表失败')
    console.error('Error fetching members:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.currentPage = 1
  fetchMembers()
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.contact = ''
  searchForm.id_card = ''
  pagination.currentPage = 1
  fetchMembers()
}

const handleAdd = () => {
  router.push('/members/register')
}

const handleEdit = (row) => {
  router.push(`/members/edit/${row.id}`)
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除会员 ${row.name} 吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await request.delete(`/api/members/${row.id}`)
    ElMessage.success('删除成功')
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error('Error deleting member:', error)
    }
  }
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  pagination.currentPage = 1
  fetchMembers()
}

const handleCurrentChange = (val) => {
  pagination.currentPage = val
  fetchMembers()
}

onMounted(() => {
  fetchMembers()
})
</script>

<style scoped>
.member-list-container {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.table-card {
  min-height: 500px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-header h3 {
  margin: 0;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>