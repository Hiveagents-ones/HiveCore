<template>
  <div class="schedule-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="课程" prop="courseId">
        <el-select
          v-model="formData.courseId"
          placeholder="请选择课程"
          style="width: 100%"
          @change="handleCourseChange"
        >
          <el-option
            v-for="course in courses"
            :key="course.id"
            :label="course.name"
            :value="course.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="教练" prop="coachId">
        <el-select
          v-model="formData.coachId"
          placeholder="请选择教练"
          style="width: 100%"
          :disabled="!formData.courseId"
        >
          <el-option
            v-for="coach in coaches"
            :key="coach.id"
            :label="coach.name"
            :value="coach.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="上课日期" prop="date">
        <el-date-picker
          v-model="formData.date"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
          :disabled-date="disabledDate"
          @change="handleDateChange"
        />
      </el-form-item>

      <el-form-item label="上课时间" prop="timeSlot">
        <el-select
          v-model="formData.timeSlot"
          placeholder="请选择时间段"
          style="width: 100%"
          :disabled="!formData.date"
        >
          <el-option
            v-for="slot in timeSlots"
            :key="slot.value"
            :label="slot.label"
            :value="slot.value"
            :disabled="slot.disabled"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="上课地点" prop="locationId">
        <el-select
          v-model="formData.locationId"
          placeholder="请选择地点"
          style="width: 100%"
          :disabled="!formData.date"
        >
          <el-option
            v-for="location in locations"
            :key="location.id"
            :label="location.name"
            :value="location.id"
            :disabled="location.disabled"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="最大人数" prop="maxParticipants">
        <el-input-number
          v-model="formData.maxParticipants"
          :min="1"
          :max="selectedLocation?.capacity || 999"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          {{ isEdit ? '更新' : '创建' }}排课
        </el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 冲突提示 -->
    <el-dialog
      v-model="conflictDialogVisible"
      title="排课冲突"
      width="500px"
    >
      <div v-if="conflicts.length > 0">
        <p>检测到以下冲突：</p>
        <ul>
          <li v-for="(conflict, index) in conflicts" :key="index">
            {{ conflict.message }}
          </li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="conflictDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="forceSubmit">强制提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useCourseStore } from '@/stores/course'
import { useCoachStore } from '@/stores/coach'
import { useLocationStore } from '@/stores/location'
import { useScheduleStore } from '@/stores/schedule'

const props = defineProps({
  initialData: {
    type: Object,
    default: () => ({})
  },
  isEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['success', 'cancel'])

// Store
const courseStore = useCourseStore()
const coachStore = useCoachStore()
const locationStore = useLocationStore()
const scheduleStore = useScheduleStore()

// Refs
const formRef = ref(null)
const loading = ref(false)
const conflictDialogVisible = ref(false)
const conflicts = ref([])

// Form data
const formData = reactive({
  courseId: '',
  coachId: '',
  date: '',
  timeSlot: '',
  locationId: '',
  maxParticipants: 20
})

// Rules
const rules = {
  courseId: [{ required: true, message: '请选择课程', trigger: 'change' }],
  coachId: [{ required: true, message: '请选择教练', trigger: 'change' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  timeSlot: [{ required: true, message: '请选择时间段', trigger: 'change' }],
  locationId: [{ required: true, message: '请选择地点', trigger: 'change' }],
  maxParticipants: [{ required: true, message: '请设置最大人数', trigger: 'blur' }]
}

// Computed
const courses = computed(() => courseStore.courses)
const coaches = computed(() => coachStore.coaches)
const locations = computed(() => locationStore.locations)
const selectedCourse = computed(() => 
  courses.value.find(c => c.id === formData.courseId)
)
const selectedLocation = computed(() => 
  locations.value.find(l => l.id === formData.locationId)
)

// Time slots
const timeSlots = ref([
  { label: '08:00-09:30', value: '08:00-09:30', disabled: false },
  { label: '10:00-11:30', value: '10:00-11:30', disabled: false },
  { label: '14:00-15:30', value: '14:00-15:30', disabled: false },
  { label: '16:00-17:30', value: '16:00-17:30', disabled: false },
  { label: '19:00-20:30', value: '19:00-20:30', disabled: false }
])

// Methods
const disabledDate = (time) => {
  return time.getTime() < Date.now() - 8.64e7
}

const handleCourseChange = async () => {
  if (formData.courseId) {
    await coachStore.fetchCoachesByCourse(formData.courseId)
    formData.coachId = ''
  }
}

const handleDateChange = async () => {
  if (formData.date) {
    await checkConflicts()
  }
}

const checkConflicts = async () => {
  if (!formData.date || !formData.timeSlot || !formData.locationId) return
  
  try {
    const conflictData = await scheduleStore.checkConflicts({
      date: formData.date,
      timeSlot: formData.timeSlot,
      locationId: formData.locationId,
      coachId: formData.coachId,
      excludeId: props.isEdit ? props.initialData.id : null
    })
    
    conflicts.value = conflictData
    
    // Update time slots and locations disabled status
    timeSlots.value.forEach(slot => {
      slot.disabled = conflictData.some(c => 
        c.type === 'location' && c.timeSlot === slot.value
      )
    })
    
    locationStore.locations.forEach(location => {
      location.disabled = conflictData.some(c => 
        c.type === 'location' && c.locationId === location.id
      )
    })
  } catch (error) {
    console.error('检查冲突失败:', error)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (conflicts.value.length > 0) {
      conflictDialogVisible.value = true
      return
    }
    
    await submitSchedule()
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

const forceSubmit = async () => {
  conflictDialogVisible.value = false
  await submitSchedule(true)
}

const submitSchedule = async (force = false) => {
  loading.value = true
  
  try {
    const scheduleData = {
      courseId: formData.courseId,
      coachId: formData.coachId,
      date: formData.date,
      timeSlot: formData.timeSlot,
      locationId: formData.locationId,
      maxParticipants: formData.maxParticipants,
      force
    }
    
    if (props.isEdit) {
      await scheduleStore.updateSchedule(props.initialData.id, scheduleData)
      ElMessage.success('排课更新成功')
    } else {
      await scheduleStore.createSchedule(scheduleData)
      ElMessage.success('排课创建成功')
    }
    
    emit('success')
    handleReset()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  conflicts.value = []
  timeSlots.value.forEach(slot => slot.disabled = false)
  locationStore.locations.forEach(location => location.disabled = false)
}

// Watch for conflicts
watch([() => formData.timeSlot, () => formData.locationId], () => {
  checkConflicts()
})

// Initialize
onMounted(async () => {
  await Promise.all([
    courseStore.fetchCourses(),
    coachStore.fetchCoaches(),
    locationStore.fetchLocations()
  ])
  
  if (props.isEdit && props.initialData) {
    Object.assign(formData, props.initialData)
    await handleCourseChange()
  }
})
</script>

<style scoped>
.schedule-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.el-form-item {
  margin-bottom: 24px;
}

.el-select {
  width: 100%;
}

.el-date-picker {
  width: 100%;
}
</style>