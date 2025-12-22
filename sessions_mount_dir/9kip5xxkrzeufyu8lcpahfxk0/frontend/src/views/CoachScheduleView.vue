<template>
  <div class="coach-schedule-container">
    <h1>教练排班管理</h1>
    
    <div class="action-bar">
      <el-button type="primary" @click="handleCreate">新增排班</el-button>
      <el-date-picker
        v-model="queryDate"
        type="date"
        placeholder="选择日期"
        @change="fetchSchedules"
      />
    </div>
    
    <el-table :data="schedules" style="width: 100%" border stripe>
      <el-table-column prop="coach_name" label="教练姓名" width="120" sortable />
      <el-table-column prop="course_name" label="课程名称" width="120" sortable />
      <el-table-column prop="start_time" label="开始时间" width="180" sortable />
      <el-table-column prop="end_time" label="结束时间" width="180" sortable />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 新增/编辑排班对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle">
      <el-form :model="form" label-width="120px">
        <el-form-item label="教练">
          <el-select v-model="form.coach_id" placeholder="请选择教练">
            <el-option
              v-for="coach in coaches"
              :key="coach.id"
              :label="coach.name"
              :value="coach.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="课程">
          <el-select v-model="form.course_id" placeholder="请选择课程">
            <el-option
              v-for="course in courses"
              :key="course.id"
              :label="course.name"
              :value="course.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="form.start_time"
            type="datetime"
            placeholder="选择开始时间"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="form.end_time"
            type="datetime"
            placeholder="选择结束时间"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { 
  getCoachSchedules, 
  createCoachSchedule, 
  updateCoachSchedule,
  deleteCoachSchedule,
  getCoaches
} from '@/api/coaches'
import { ElMessage, ElMessageBox } from 'element-plus'

const defaultForm = {
  id: null,
  coach_id: null,
  course_id: null,
  start_time: null,
  end_time: null
}

export default {
  name: 'CoachScheduleView',
  
  setup() {
    const schedules = ref([])
    const coaches = ref([])
    const courses = ref([])
    const queryDate = ref(new Date())
    const dialogVisible = ref(false)
    const dialogTitle = ref('新增排班')
    const form = ref({ ...defaultForm })
    
    const fetchSchedules = async () => {
      try {
        const { data } = await getCoachSchedules({ 
          date: queryDate.value.toISOString().split('T')[0] 
        })
        schedules.value = data
      } catch (error) {
        ElMessage.error('获取排班信息失败')
      }
    }
    
    const fetchCoaches = async () => {
    
    const fetchCourses = async () => {
      try {
        const { data } = await getCourses()
        courses.value = data
      } catch (error) {
        ElMessage.error('获取课程列表失败')
      }
    }
      try {
        const { data } = await getCoaches()
        coaches.value = data
      } catch (error) {
        ElMessage.error('获取教练列表失败')
      }
    }
      try {
        const { data } = await getCoaches()
        coaches.value = data
      } catch (error) {
        ElMessage.error('获取教练列表失败')
      }
    }








    
    const handleCreate = () => {
      form.value = { ...defaultForm }
      dialogTitle.value = '新增排班'
      dialogVisible.value = true
    }
    
    const handleEdit = (row) => {
      form.value = { ...row }
      dialogTitle.value = '编辑排班'
      dialogVisible.value = true
    }
    
    const handleDelete = async (row) => {
      try {
        await ElMessageBox.confirm('确认删除该排班吗？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning'
        })
        await deleteCoachSchedule(row.id)
        ElMessage.success('删除成功')
        fetchSchedules()
      } catch (error) {
        console.error(error)
      }
    }
    
    const submitForm = async () => {
      try {
        if (form.value.id) {
          await updateCoachSchedule(form.value.id, form.value)
          ElMessage.success('更新成功')
        } else {
          await createCoachSchedule(form.value)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchSchedules()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }
    
    onMounted(() => {
      fetchSchedules()
      fetchCoaches()
      fetchCourses()
    })
    
    return {
      schedules,
      coaches,
      courses,
      queryDate,
      dialogVisible,
      dialogTitle,
      form,
      fetchSchedules,
      fetchCourses,
      handleCreate,
      handleEdit,
      handleDelete,
      submitForm
    }
  }
}
</script>

<style scoped>
.coach-schedule-container {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.action-bar {
  margin-top: 20px;
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}
</style>