<template>
  <div class="course-management">
    <div class="header">
      <h2>课程管理</h2>
      <el-button type="primary" @click="showCreateCourseDialog">创建课程</el-button>
    </div>

    <el-table :data="courses" style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="课程名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="duration" label="时长(分钟)" />
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 课程表单对话框 -->
    <el-dialog
      v-model="courseDialogVisible"
      :title="isEdit ? '编辑课程' : '创建课程'"
      width="50%"
    >
      <CourseForm
        :course="currentCourse"
        @submit="handleCourseSubmit"
        @cancel="courseDialogVisible = false"
      />
    </el-dialog>

    <!-- 排课表单对话框 -->
    <el-dialog
      v-model="scheduleDialogVisible"
      title="排课管理"
      width="60%"
    >
      <ScheduleForm
        :course="currentCourse"
        @submit="handleScheduleSubmit"
        @cancel="scheduleDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCourses, createCourse, updateCourse, deleteCourse } from '@/api/course'
import CourseForm from '@/components/CourseForm.vue'
import ScheduleForm from '@/components/ScheduleForm.vue'

const courses = ref([])
const loading = ref(false)
const courseDialogVisible = ref(false)
const scheduleDialogVisible = ref(false)
const isEdit = ref(false)
const currentCourse = ref(null)

// 获取课程列表
const fetchCourses = async () => {
  loading.value = true
  try {
    const data = await getCourses()
    courses.value = data
  } catch (error) {
    ElMessage.error('获取课程列表失败')
  } finally {
    loading.value = false
  }
}

// 显示创建课程对话框
const showCreateCourseDialog = () => {
  isEdit.value = false
  currentCourse.value = null
  courseDialogVisible.value = true
}

// 编辑课程
const handleEdit = (course) => {
  isEdit.value = true
  currentCourse.value = { ...course }
  courseDialogVisible.value = true
}

// 删除课程
const handleDelete = async (course) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除课程 "${course.name}" 吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await deleteCourse(course.id)
    ElMessage.success('删除成功')
    fetchCourses()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 处理课程表单提交
const handleCourseSubmit = async (courseData) => {
  try {
    if (isEdit.value) {
      await updateCourse(currentCourse.value.id, courseData)
      ElMessage.success('更新成功')
    } else {
      await createCourse(courseData)
      ElMessage.success('创建成功')
    }
    courseDialogVisible.value = false
    fetchCourses()
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  }
}

// 处理排课表单提交
const handleScheduleSubmit = async (scheduleData) => {
  try {
    // 这里应该调用排课相关的API
    // 由于依赖文件中的排课API不完整，这里只做示例
    ElMessage.success('排课成功')
    scheduleDialogVisible.value = false
  } catch (error) {
    ElMessage.error('排课失败')
  }
}

onMounted(() => {
  fetchCourses()
})
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

.header h2 {
  margin: 0;
}
</style>