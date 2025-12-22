<template>
  <div class="course-list-container">
    <div class="header">
      <h2>课程管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建课程
      </el-button>
    </div>

    <el-table :data="courseList" stripe style="width: 100%">
      <el-table-column prop="name" label="课程名称" width="180" />
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column prop="time" label="时间" width="180" />
      <el-table-column prop="location" label="地点" width="180" />
      <el-table-column prop="coach" label="教练" width="120" />
      <el-table-column prop="price" label="价格" width="120">
        <template #default="scope">
          ¥{{ scope.row.price }}
        </template>
      </el-table-column>
      <el-table-column prop="capacity" label="容量" width="100" />
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button size="small" @click="handleView(scope.row)">查看</el-button>
          <el-button size="small" type="primary" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="课程名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" placeholder="请选择课程类型">
            <el-option label="瑜伽" value="yoga" />
            <el-option label="普拉提" value="pilates" />
            <el-option label="有氧" value="aerobic" />
            <el-option label="力量训练" value="strength" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker
            v-model="form.time"
            type="datetime"
            placeholder="选择日期时间"
          />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="form.location" />
        </el-form-item>
        <el-form-item label="教练">
          <el-input v-model="form.coach" />
        </el-form-item>
        <el-form-item label="价格">
          <el-input-number v-model="form.price" :min="0" />
        </el-form-item>
        <el-form-item label="容量">
          <el-input-number v-model="form.capacity" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import axios from 'axios'

const courseList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const form = ref({
  name: '',
  type: '',
  time: '',
  location: '',
  coach: '',
  price: 0,
  capacity: 1
})
const editingId = ref(null)

const fetchCourses = async () => {
  try {
    const response = await axios.get('/api/courses')
    courseList.value = response.data
  } catch (error) {
    ElMessage.error('获取课程列表失败')
  }
}

const handleCreate = () => {
  dialogTitle.value = '创建课程'
  form.value = {
    name: '',
    type: '',
    time: '',
    location: '',
    coach: '',
    price: 0,
    capacity: 1
  }
  editingId.value = null
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑课程'
  form.value = { ...row }
  editingId.value = row.id
  dialogVisible.value = true
}

const handleView = (row) => {
  ElMessage.info(`查看课程: ${row.name}`)
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除课程 "${row.name}" 吗?`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await axios.delete(`/api/courses/${row.id}`)
    ElMessage.success('删除成功')
    fetchCourses()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  try {
    if (editingId.value) {
      await axios.put(`/api/courses/${editingId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await axios.post('/api/courses', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchCourses()
  } catch (error) {
    ElMessage.error(editingId.value ? '更新失败' : '创建失败')
  }
}

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.course-list-container {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>