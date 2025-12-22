<template>
  <div class="checkin-view">
    <el-card class="checkin-card">
      <template #header>
        <div class="card-header">
          <h2>{{ $t('checkin.title') }}</h2>
        </div>
      </template>

      <el-form
        ref="checkinFormRef"
        :model="checkinForm"
        :rules="rules"
        label-width="120px"
        class="checkin-form"
      >
        <el-form-item :label="$t('checkin.searchMethod')" prop="search_method">
          <el-radio-group v-model="checkinForm.search_method">
            <el-radio label="phone">{{ $t('checkin.byPhone') }}</el-radio>
            <el-radio label="member_id">{{ $t('checkin.byId') }}</el-radio>
            <el-radio label="id_card">{{ $t('checkin.byIdCard') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          :label="getInputLabel()"
          prop="identifier"
        >
          <el-input
            v-model="checkinForm.identifier"
            :placeholder="getInputPlaceholder()"
            @keyup.enter="handleCheckin"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="handleCheckin"
            size="large"
          >
            {{ $t('checkin.confirmButton') }}
          </el-button>
          <el-button @click="resetForm" size="large">
            {{ $t('checkin.resetButton') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { checkin } from '@/api/checkin'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const checkinFormRef = ref()
const loading = ref(false)

const checkinForm = reactive({
  search_method: 'phone',
  identifier: '',
})

const rules = computed(() => {
  const baseRules = {
    search_method: [{ required: true, message: t('checkin.rules.methodRequired'), trigger: 'change' }],
    identifier: [{ required: true, message: t('checkin.rules.identifierRequired'), trigger: 'blur' }],
  }
  
  if (checkinForm.search_method === 'phone') {
    baseRules.identifier.push({
      pattern: /^1[3-9]\d{9}$/,
      message: t('checkin.rules.phoneFormat'),
      trigger: 'blur'
    });
  }
  
  if (checkinForm.search_method === 'id_card') {
    baseRules.identifier.push({
      pattern: /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/,
      message: t('checkin.rules.idCardFormat'),
      trigger: 'blur',
    });
  }

  return baseRules
})

const getInputLabel = () => {
  switch (checkinForm.search_method) {
    case 'phone': return t('member.phone')
    case 'member_id': return t('member.id')
    case 'id_card': return t('member.idCard')
    default: return ''
  }
}

const getInputPlaceholder = () => {
  switch (checkinForm.search_method) {
    case 'phone': return t('checkin.phonePlaceholder')
    case 'member_id': return t('checkin.memberIdPlaceholder')
    case 'id_card': return t('checkin.idCardPlaceholder')
    default: return ''
  }
}

const handleCheckin = async () => {
  if (!checkinFormRef.value) return

  try {
    await checkinFormRef.value.validate()
    loading.value = true

    const payload = {}
    payload[checkinForm.search_method] = checkinForm.identifier

    const response = await checkin(payload)

    const { member_name, checkin_time } = response.data
    ElMessage.success(
      t('checkin.success', {
        name: member_name,
        time: new Date(checkin_time).toLocaleString(),
      })
    )
    
    resetForm()
  } catch (error) {
    if (error.name === 'ElMessageError') {
      // Validation error, message is already shown by ElMessage
      return
    }
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail

      if (status === 404 || detail?.includes('not found')) {
        ElMessage.error(t('checkin.errors.memberNotFound'))
      } else if (detail) {
        ElMessage.error(detail)
      } else {
        ElMessage.error(t('checkin.errors.failed'))
      }
    } else {
      ElMessage.error(t('checkin.errors.network'))
    }
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  if (!checkinFormRef.value) return
  checkinFormRef.value.resetFields()
}
</script>

<style scoped>
.checkin-view {
  padding: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  background-color: #f5f7fa;
}

.checkin-card {
  width: 100%;
  max-width: 500px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: center;
  align-items: center;
}

.checkin-form {
  padding: 20px;
}

.el-form-item {
  margin-bottom: 24px;
}
</style>
