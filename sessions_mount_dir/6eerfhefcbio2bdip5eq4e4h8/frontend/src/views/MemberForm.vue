<template>
  <div class="member-form-container">
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? $t('member.editTitle') : $t('member.createTitle') }}</span>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        label-position="right"
        @submit.prevent="handleSubmit"
      >
        <el-form-item :label="$t('member.name')" prop="name">
          <el-input
            v-model="formData.name"
            :placeholder="$t('member.namePlaceholder')"
            clearable
          />
        </el-form-item>
        
        <el-form-item :label="$t('member.phone')" prop="phone">
          <el-input
            v-model="formData.phone"
            :placeholder="$t('member.phonePlaceholder')"
            clearable
          />
        </el-form-item>
        
        <el-form-item :label="$t('member.email')" prop="email">
          <el-input
            v-model="formData.email"
            :placeholder="$t('member.emailPlaceholder')"
            clearable
          />
        </el-form-item>
        
        <el-form-item :label="$t('member.level')" prop="level">
          <el-select
            v-model="formData.level"
            :placeholder="$t('member.levelPlaceholder')"
            @change="handleLevelChange"
          >
            <el-option
              v-for="level in memberLevels"
              :key="level.value"
              :label="level.label"
              :value="level.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item :label="$t('member.effectiveDate')" prop="effective_date">
          <el-date-picker
            v-model="formData.effective_date"
            type="date"
            :placeholder="$t('member.effectiveDatePlaceholder')"
            @change="handleEffectiveDateChange"
          />
        </el-form-item>
        
        <el-form-item :label="$t('member.expiryDate')" prop="expiry_date">
          <el-date-picker
            v-model="formData.expiry_date"
            type="date"
            :placeholder="$t('member.expiryDatePlaceholder')"
            :disabled="isEdit"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            {{ isEdit ? $t('common.update') : $t('common.create') }}
          </el-button>
          <el-button @click="handleCancel">
            {{ $t('common.cancel') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { getMember, createMember, updateMember } from '@/api/members'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const isEdit = computed(() => !!route.params.id)

const memberLevels = [
  { value: 'bronze', label: t('member.levels.bronze') },
  { value: 'silver', label: t('member.levels.silver') },
  { value: 'gold', label: t('member.levels.gold') },
  { value: 'platinum', label: t('member.levels.platinum') }
]

const levelDurations = {
  bronze: 365,
  silver: 365,
  gold: 730,
  platinum: 1095
}

const formData = reactive({
  name: '',
  phone: '',
  email: '',
  level: '',
  effective_date: '',
  expiry_date: ''
})

const rules = {
  name: [
    { required: true, message: t('member.nameRequired'), trigger: 'blur' },
    { min: 2, max: 50, message: t('member.nameLength'), trigger: 'blur' }
  ],
  phone: [
    { required: true, message: t('member.phoneRequired'), trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: t('member.phoneFormat'), trigger: 'blur' }
  ],
  email: [
    { required: true, message: t('member.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('member.emailFormat'), trigger: 'blur' }
  ],
  level: [
    { required: true, message: t('member.levelRequired'), trigger: 'change' }
  ],
  effective_date: [
    { required: true, message: t('member.effectiveDateRequired'), trigger: 'change' }
  ],
  expiry_date: [
    { required: true, message: t('member.expiryDateRequired'), trigger: 'change' }
  ]
}

const calculateExpiryDate = (effectiveDate, level) => {
  if (!effectiveDate || !level) return ''
  
  const duration = levelDurations[level] || 365
  const expiry = new Date(effectiveDate)
  expiry.setDate(expiry.getDate() + duration)
  
  return expiry
}

const handleLevelChange = () => {
  if (formData.effective_date && !isEdit.value) {
    formData.expiry_date = calculateExpiryDate(formData.effective_date, formData.level)
  }
}

const handleEffectiveDateChange = () => {
  if (formData.level && !isEdit.value) {
    formData.expiry_date = calculateExpiryDate(formData.effective_date, formData.level)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    const submitData = {
      ...formData,
      effective_date: formData.effective_date ? new Date(formData.effective_date).toISOString() : null,
      expiry_date: formData.expiry_date ? new Date(formData.expiry_date).toISOString() : null
    }
    
    if (isEdit.value) {
      await updateMember(route.params.id, submitData)
      ElMessage.success(t('member.updateSuccess'))
    } else {
      await createMember(submitData)
      ElMessage.success(t('member.createSuccess'))
    }
    
    router.push('/members')
  } catch (error) {
    console.error('Submit error:', error)
    ElMessage.error(error.response?.data?.detail || t('common.error'))
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  router.push('/members')
}

const loadMember = async () => {
  if (!isEdit.value) return
  
  try {
    loading.value = true
    const data = await getMember(route.params.id)
    
    Object.assign(formData, {
      name: data.name || '',
      phone: data.phone || '',
      email: data.email || '',
      level: data.level || '',
      effective_date: data.effective_date ? new Date(data.effective_date) : '',
      expiry_date: data.expiry_date ? new Date(data.expiry_date) : ''
    })
  } catch (error) {
    console.error('Load member error:', error)
    ElMessage.error(t('member.loadError'))
    router.push('/members')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMember()
})
</script>

<style scoped>
.member-form-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.form-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 18px;
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