<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="120px"
    class="course-form"
  >
    <el-form-item label="课程名称" prop="name">
      <el-input v-model="form.name" placeholder="请输入课程名称" />
    </el-form-item>

    <el-form-item label="课程类型" prop="type">
      <el-select v-model="form.type" placeholder="请选择课程类型">
        <el-option
          v-for="type in courseTypes"
          :key="type.value"
          :label="type.label"
          :value="type.value"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="课程描述" prop="description">
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="3"
        placeholder="请输入课程描述"
      />
    </el-form-item>

    <el-form-item label="教练" prop="coach_id">
      <el-select v-model="form.coach_id" placeholder="请选择教练">
        <el-option
          v-for="coach in coaches"
          :key="coach.id"
          :label="coach.name"
          :value="coach.id"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="上课地点" prop="location">
      <el-input v-model="form.location" placeholder="请输入上课地点" />
    </el-form-item>

    <el-form-item label="上课时间" prop="schedule">
      <el-date-picker
        v-model="form.schedule"
        type="datetime"
        placeholder="选择上课时间"
        format="YYYY-MM-DD HH:mm"
        value-format="YYYY-MM-DD HH:mm:ss"
      />
    </el-form-item>

    <el-form-item label="课程时长" prop="duration">
      <el-input-number
        v-model="form.duration"
        :min="30"
        :max="300"
        :step="30"
        controls-position="right"
      />
      <span class="ml-2">分钟</span>
    </el-form-item>

    <el-form-item label="最大人数" prop="max_participants">
      <el-input-number
        v-model="form.max_participants"
        :min="1"
        :max="100"
        controls-position="right"
      />
    </el-form-item>

    <el-form-item label="课程状态" prop="status">
      <el-radio-group v-model="form.status">
        <el-radio
          v-for="status in courseStatus"
          :key="status.value"
          :label="status.value"
        >
          {{ status.label }}
        </el-radio>
      </el-radio-group>
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="submitForm">保存</el-button>
      <el-button @click="resetForm">重置</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useCourseStore } from '@/stores/course'
import { useCoachStore } from '@/stores/coach'

const props = defineProps({
  courseId: {
    type: [String, Number],
    default: null
  }
})

const emit = defineEmits(['success'])

const formRef = ref()
const courseStore = useCourseStore()
const coachStore = useCoachStore()

const form = reactive({
  name: '',
  type: '',
  description: '',
  coach_id: null,
  location: '',
  schedule: '',
  duration: 60,
  max_participants: 20,
  status: 'active'
})

const rules = {
  name: [
    { required: true, message: '请输入课程名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择课程类型', trigger: 'change' }
  ],
  coach_id: [
    { required: true, message: '请选择教练', trigger: 'change' }
  ],
  location: [
    { required: true, message: '请输入上课地点', trigger: 'blur' }
  ],
  schedule: [
    { required: true, message: '请选择上课时间', trigger: 'change' }
  ],
  duration: [
    { required: true, message: '请输入课程时长', trigger: 'blur' }
  ],
  max_participants: [
    { required: true, message: '请输入最大人数', trigger: 'blur' }
  ]
}

const courseTypes = [
  { label: '瑜伽', value: 'yoga' },
  { label: '动感单车', value: 'cycling' },
  { label: '游泳', value: 'swimming' },
  { label: '力量训练', value: 'strength' },
  { label: '有氧操', value: 'aerobics' },
  { label: '普拉提', value: 'pilates' }
]

const courseStatus = [
  { label: '正常', value: 'active' },
  { label: '暂停', value: 'paused' },
  { label: '已取消', value: 'cancelled' }
]

const coaches = ref([])

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid, fields) => {
    if (valid) {
      try {
        if (props.courseId) {
          await courseStore.updateCourse(props.courseId, form)
          ElMessage.success('课程更新成功')
        } else {
          await courseStore.createCourse(form)
          ElMessage.success('课程创建成功')
        }
        emit('success')
      } catch (error) {
        ElMessage.error(error.message || '操作失败')
      }
    } else {
      console.log('验证失败:', fields)
    }
  })
}

const resetForm = () => {
  if (!formRef.value) return
  formRef.value.resetFields()
}

const loadCourse = async () => {
  if (!props.courseId) return
  
  try {
    const course = await courseStore.getCourseById(props.courseId)
    if (course) {
      Object.assign(form, course)
    }
  } catch (error) {
    ElMessage.error('加载课程信息失败')
  }
}

const loadCoaches = async () => {
  try {
    coaches.value = await coachStore.fetchCoaches()
  } catch (error) {
    ElMessage.error('加载教练列表失败')
  }
}

onMounted(async () => {
  await loadCoaches()
  if (props.courseId) {
    await loadCourse()
  }
})
</script>

<style scoped>
.course-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.ml-2 {
  margin-left: 8px;
}
</style>