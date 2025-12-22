<template>
  <div class="course-management">
    <div class="header">
      <h1>课程管理</h1>
      <el-button type="primary" @click="showAddDialog">添加课程</el-button>
    </div>

    <el-table :data="courses" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="课程名称" />
      <el-table-column prop="description" label="课程描述" />
      <el-table-column prop="duration" label="时长(分钟)" />
      <el-table-column prop="capacity" label="容量" />
      <el-table-column prop="price" label="价格" />
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="editCourse(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteCourse(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      :title="dialogTitle"
      v-model="dialogVisible"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="课程名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="课程描述" prop="description">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="时长" prop="duration">
          <el-input-number v-model="form.duration" :min="1" />
        </el-form-item>
        <el-form-item label="容量" prop="capacity">
          <el-input-number v-model="form.capacity" :min="1" />
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="form.price" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useCourseStore } from '@/stores/course'

const courseStore = useCourseStore()
const courses = computed(() => courseStore.getAllCourses)
const loading = computed(() => courseStore.loading)

const dialogVisible = ref(false)
const dialogTitle = ref('添加课程')
const formRef = ref(null)
const isEdit = ref(false)
const currentId = ref(null)

const form = ref({
  name: '',
  description: '',
  duration: 60,
  capacity: 20,
  price: 0,
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入课程描述', trigger: 'blur' }],
  duration: [{ required: true, message: '请输入课程时长', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入课程容量', trigger: 'blur' }],
  price: [{ required: true, message: '请输入课程价格', trigger: 'blur' }]
}

onMounted(() => {
  fetchCourses()
})

const fetchCourses = async () => {
  try {
    await courseStore.fetchCourses()
  } catch (error) {
    ElMessage.error('获取课程列表失败')
  }
}

const showAddDialog = () => {
  isEdit.value = false
  dialogTitle.value = '添加课程'
  dialogVisible.value = true
}

const editCourse = (course) => {
  isEdit.value = true
  currentId.value = course.id
  dialogTitle.value = '编辑课程'
  form.value = { ...course }
  dialogVisible.value = true
}

const deleteCourse = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个课程吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await courseStore.deleteCourse(id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (isEdit.value) {
      await courseStore.updateCourse(currentId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await courseStore.createCourse(form.value)
      ElMessage.success('添加成功')
    }
    
    dialogVisible.value = false
    resetForm()
  } catch (error) {
    if (error !== false) {
      ElMessage.error(isEdit.value ? '更新失败' : '添加失败')
    }
  }
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  form.value = {
    name: '',
    description: '',
    duration: 60,
    capacity: 20,
    price: 0,
    is_active: true
  }
  currentId.value = null
}
</script>

<style scoped>
.course-management {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
}
</style>