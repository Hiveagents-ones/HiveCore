<template>
  <div class="course-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      label-position="right"
    >
      <el-form-item :label="$t('course.courseName')" prop="name">
        <el-input
          v-model="formData.name"
          :placeholder="$t('course.validation.nameRequired')"
          clearable
        />
      </el-form-item>

      <el-form-item :label="$t('course.courseType')" prop="type">
        <el-select
          v-model="formData.type"
          :placeholder="$t('course.validation.typeRequired')"
          style="width: 100%"
        >
          <el-option
            v-for="(label, value) in courseTypes"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
      </el-form-item>

      <el-form-item :label="$t('course.courseTime')" prop="time">
        <el-date-picker
          v-model="formData.time"
          type="datetime"
          :placeholder="$t('course.validation.timeRequired')"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DD HH:mm:ss"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item :label="$t('course.courseLocation')" prop="location">
        <el-input
          v-model="formData.location"
          :placeholder="$t('course.validation.locationRequired')"
          clearable
        />
      </el-form-item>

      <el-form-item :label="$t('course.coach')" prop="coach">
        <el-input
          v-model="formData.coach"
          :placeholder="$t('course.validation.coachRequired')"
          clearable
        />
      </el-form-item>

      <el-form-item :label="$t('course.coursePrice')" prop="price">
        <el-input-number
          v-model="formData.price"
          :min="0"
          :precision="2"
          :step="10"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item :label="$t('course.maxCapacity')" prop="max_capacity">
        <el-input-number
          v-model="formData.max_capacity"
          :min="1"
          :step="1"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item :label="$t('course.description')" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="4"
          :placeholder="$t('course.description')"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          {{ $t('common.save') }}
        </el-button>
        <el-button @click="handleReset">
          {{ $t('common.reset') }}
        </el-button>
        <el-button @click="handleCancel">
          {{ $t('common.cancel') }}
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const props = defineProps({
  initialData: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['submit', 'cancel'])

const { t } = useI18n()
const formRef = ref()

const formData = reactive({
  name: '',
  type: '',
  time: '',
  location: '',
  coach: '',
  price: 0,
  max_capacity: 1,
  description: ''
})

const courseTypes = computed(() => {
  return {
    yoga: t('course.type.yoga'),
    pilates: t('course.type.pilates'),
    spinning: t('course.type.spinning'),
    swimming: t('course.type.swimming'),
    strength: t('course.type.strength'),
    dance: t('course.type.dance'),
    boxing: t('course.type.boxing'),
    other: t('course.type.other')
  }
})

const rules = reactive({
  name: [
    { required: true, message: t('course.validation.nameRequired'), trigger: 'blur' }
  ],
  type: [
    { required: true, message: t('course.validation.typeRequired'), trigger: 'change' }
  ],
  time: [
    { required: true, message: t('course.validation.timeRequired'), trigger: 'change' }
  ],
  location: [
    { required: true, message: t('course.validation.locationRequired'), trigger: 'blur' }
  ],
  coach: [
    { required: true, message: t('course.validation.coachRequired'), trigger: 'blur' }
  ],
  price: [
    { required: true, message: t('course.validation.priceRequired'), trigger: 'blur' },
    { type: 'number', min: 0, message: t('course.validation.priceInvalid'), trigger: 'blur' }
  ],
  max_capacity: [
    { required: true, message: t('course.validation.capacityRequired'), trigger: 'blur' },
    { type: 'number', min: 1, message: t('course.validation.capacityInvalid'), trigger: 'blur' }
  ]
})

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    emit('submit', { ...formData })
  } catch (error) {
    ElMessage.error(t('common.error'))
  }
}

const handleReset = () => {
  if (!formRef.value) return
  formRef.value.resetFields()
  if (props.initialData && Object.keys(props.initialData).length > 0) {
    Object.assign(formData, props.initialData)
  }
}

const handleCancel = () => {
  emit('cancel')
}

onMounted(() => {
  if (props.initialData && Object.keys(props.initialData).length > 0) {
    Object.assign(formData, props.initialData)
  }
})
</script>

<style scoped>
.course-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.el-form-item {
  margin-bottom: 24px;
}

.el-button {
  margin-right: 12px;
}
</style>