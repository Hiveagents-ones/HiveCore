<template>
  <div class="member-form">
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

        <el-form-item :label="$t('member.email')" prop="email">
          <el-input
            v-model="formData.email"
            :placeholder="$t('member.emailPlaceholder')"
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

        <el-form-item :label="$t('member.level')" prop="level">
          <el-select
            v-model="formData.level"
            :placeholder="$t('member.levelPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="level in memberLevels"
              :key="level.value"
              :label="level.label"
              :value="level.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('member.membershipBalance')" prop="membership_balance">
          <el-input-number
            v-model="formData.membership_balance"
            :min="0"
            :precision="2"
            :step="0.01"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="memberStore.loading"
          >
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMemberStore } from '@/stores/member'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const memberStore = useMemberStore()
const { t } = useI18n()

const formRef = ref(null)
const isEdit = computed(() => !!route.params.id)

const memberLevels = [
  { value: 'bronze', label: t('member.levels.bronze') },
  { value: 'silver', label: t('member.levels.silver') },
  { value: 'gold', label: t('member.levels.gold') },
  { value: 'platinum', label: t('member.levels.platinum') }
]

const formData = reactive({
  name: '',
  email: '',
  phone: '',
  level: '',
  membership_balance: 0
})

const rules = {
  name: [
    { required: true, message: t('validation.nameRequired'), trigger: 'blur' },
    { min: 2, max: 50, message: t('validation.nameLength'), trigger: 'blur' }
  ],
  email: [
    { required: true, message: t('validation.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('validation.emailFormat'), trigger: 'blur' }
  ],
  phone: [
    { required: true, message: t('validation.phoneRequired'), trigger: 'blur' },
    { pattern: /^[0-9-+()\s]+$/, message: t('validation.phoneFormat'), trigger: 'blur' }
  ],
  level: [
    { required: true, message: t('validation.levelRequired'), trigger: 'change' }
  ],
  membership_balance: [
    { required: true, message: t('validation.balanceRequired'), trigger: 'blur' },
    { type: 'number', min: 0, message: t('validation.balanceMin'), trigger: 'blur' }
  ]
}

const loadMember = async () => {
  if (isEdit.value) {
    try {
      await memberStore.fetchMember(route.params.id)
      if (memberStore.currentMember) {
        Object.assign(formData, memberStore.currentMember)
      }
    } catch (error) {
      ElMessage.error(t('member.loadError'))
      router.push('/members')
    }
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (isEdit.value) {
      await memberStore.updateMember(route.params.id, formData)
      ElMessage.success(t('member.updateSuccess'))
    } else {
      await memberStore.createMember(formData)
      ElMessage.success(t('member.createSuccess'))
    }
    
    router.push('/members')
  } catch (error) {
    if (error.errors) {
      // Validation error
      return
    }
    ElMessage.error(isEdit.value ? t('member.updateError') : t('member.createError'))
  }
}

const handleCancel = () => {
  router.push('/members')
}

onMounted(() => {
  loadMember()
})
</script>

<style scoped>
.member-form {
  padding: 20px;
}

.form-card {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
}
</style>