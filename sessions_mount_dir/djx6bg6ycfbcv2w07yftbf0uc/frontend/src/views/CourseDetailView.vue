<template>
  <div class="course-detail">
    <el-page-header @back="goBack" :title="$t('common.back')">
      <template #content>
        <span class="text-large font-600 mr-3">{{ $t('course.courseDetail') }}</span>
      </template>
    </el-page-header>

    <el-card class="detail-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>{{ course.name }}</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleEdit">
              {{ $t('common.edit') }}
            </el-button>
            <el-button type="danger" @click="handleDelete">
              {{ $t('common.delete') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('course.courseName')">
          {{ course.name }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.courseType')">
          {{ courseTypes[course.type] }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.courseTime')">
          {{ formatDateTime(course.time) }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.courseLocation')">
          {{ course.location }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.coach')">
          {{ course.coach }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.coursePrice')">
          {{ formatPrice(course.price) }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.maxCapacity')">
          {{ course.max_capacity }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.currentCapacity')">
          {{ course.current_capacity || 0 }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('course.description')" :span="2">
          {{ course.description || $t('common.noDescription') }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useCourseStore } from '@/stores/course'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const courseStore = useCourseStore()

const loading = ref(false)
const course = ref({})

const courseTypes = computed(() => ({
  yoga: t('course.types.yoga'),
  pilates: t('course.types.pilates'),
  spinning: t('course.types.spinning'),
  swimming: t('course.types.swimming'),
  strength: t('course.types.strength'),
  dance: t('course.types.dance'),
  boxing: t('course.types.boxing'),
  other: t('course.types.other')
}))

const fetchCourse = async () => {
  try {
    loading.value = true
    const courseId = route.params.id
    const response = await courseStore.getCourseById(courseId)
    course.value = response
  } catch (error) {
    ElMessage.error(t('course.messages.fetchError'))
  } finally {
    loading.value = false
  }
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString()
}

const formatPrice = (price) => {
  return `¥${price.toFixed(2)}`
}

const goBack = () => {
  router.push('/courses')
}

const handleEdit = () => {
  router.push(`/courses/${course.value.id}/edit`)
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(
      t('course.messages.deleteConfirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    
    await courseStore.deleteCourse(course.value.id)
    ElMessage.success(t('course.messages.deleteSuccess'))
    router.push('/courses')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('course.messages.deleteError'))
    }
  }
}

onMounted(() => {
  fetchCourse()
})
</script>

<style scoped>
.course-detail {
  padding: 20px;
}

.detail-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.text-large {
  font-size: 16px;
}

.font-600 {
  font-weight: 600;
}

.mr-3 {
  margin-right: 12px;
}
</style>