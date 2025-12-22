<template>
  <div class="course-selector">
    <el-select
      v-model="selectedCourses"
      multiple
      filterable
      clearable
      placeholder="请选择课程"
      @change="handleChange"
    >
      <el-option
        v-for="course in courseList"
        :key="course.id"
        :label="course.name"
        :value="course.id"
      >
        <span>{{ course.name }}</span>
        <span class="course-type">({{ course.type }})</span>
      </el-option>
    </el-select>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getCourseList } from '@/api/course'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  coachId: {
    type: [String, Number],
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const selectedCourses = ref([])
const courseList = ref([])
const loading = ref(false)

const fetchCourses = async () => {
  try {
    loading.value = true
    const response = await getCourseList()
    courseList.value = response.data || []
  } catch (error) {
    console.error('获取课程列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleChange = (value) => {
  emit('update:modelValue', value)
  emit('change', value)
}

watch(() => props.modelValue, (newVal) => {
  selectedCourses.value = newVal || []
}, { immediate: true })

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.course-selector {
  width: 100%;
}

.course-type {
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}
</style>