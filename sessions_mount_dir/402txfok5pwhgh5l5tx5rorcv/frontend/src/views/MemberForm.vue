<template>
  <div class="member-form-container">
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <h2>{{ isEdit ? '编辑会员' : '新建会员' }}</h2>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="姓名" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入会员姓名"
            :disabled="submitting"
          />
        </el-form-item>
        
        <el-form-item label="联系方式" prop="contact">
          <el-input
            v-model="formData.contact"
            placeholder="请输入手机号码"
            :disabled="submitting"
          />
        </el-form-item>
        
        <el-form-item label="会员等级" prop="level">
          <el-select
            v-model="formData.level"
            placeholder="请选择会员等级"
            :disabled="submitting"
          >
            <el-option label="普通会员" value="regular" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="会员状态" prop="status">
          <el-select
            v-model="formData.status"
            placeholder="请选择会员状态"
            :disabled="submitting"
          >
            <el-option label="活跃" value="active" />
            <el-option label="冻结" value="frozen" />
            <el-option label="过期" value="expired" />
          </el-select>
        </el-form-item>

        <!-- 动态字段 -->
        <el-form-item
          v-for="field in dynamicFields"
          :key="field.key"
          :label="field.label"
          :prop="`metadata.${field.key}`"
        >
          <el-input
            v-if="field.type === 'string'"
            v-model="formData.metadata[field.key]"
            :placeholder="`请输入${field.label}`"
            :disabled="submitting"
          />
          <el-input
            v-else-if="field.type === 'number'"
            v-model.number="formData.metadata[field.key]"
            type="number"
            :placeholder="`请输入${field.label}`"
            :disabled="submitting"
          />
          <el-date-picker
            v-else-if="field.type === 'date'"
            v-model="formData.metadata[field.key]"
            type="date"
            :placeholder="`请选择${field.label}`"
            :disabled="submitting"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="submitting"
            :disabled="submitting"
          >
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { memberApi } from '@/api/members'
import { metadataApi } from '@/api/metadata'

const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const submitting = ref(false)
const isEdit = ref(false)

const formData = reactive({
  name: '',
  contact: '',
  level: '',
  status: 'active',
  metadata: {}
})

const dynamicFields = ref([])

const validatePhone = (rule, value, callback) => {
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!value) {
    callback(new Error('请输入联系方式'))
  } else if (!phoneRegex.test(value)) {
    callback(new Error('请输入有效的手机号码'))
  } else {
    callback()
  }
}

const rules = reactive({
  name: [
    { required: true, message: '请输入会员姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '姓名长度应在2-20个字符之间', trigger: 'blur' }
  ],
  contact: [
    { validator: validatePhone, trigger: 'blur' }
  ],
  level: [
    { required: true, message: '请选择会员等级', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择会员状态', trigger: 'change' }
  ]
})

const handleSubmit = async () => {
  if (submitting.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    if (isEdit.value) {
      await memberApi.updateMember(route.params.id, formData)
      ElMessage.success('会员信息更新成功')
    } else {
      await memberApi.createMember(formData)
      ElMessage.success('会员创建成功')
    }
    
    router.push('/members')
  } catch (error) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleCancel = () => {
  router.push('/members')
}

const loadMetadata = async () => {
  try {
    const metadata = await metadataApi.getMemberMetadata()
    dynamicFields.value = metadata.fields || []
  } catch (error) {
    console.error('加载元数据失败:', error)
  }
}

const loadMember = async (id) => {
  try {
    const member = await memberApi.getMember(id)
    Object.assign(formData, {
      name: member.name,
      contact: member.contact,
      level: member.level,
      status: member.status,
      metadata: member.metadata || {}
    })
  } catch (error) {
    ElMessage.error('加载会员信息失败')
    router.push('/members')
  }
}

onMounted(async () => {
  await loadMetadata()
  if (route.params.id) {
    isEdit.value = true
    loadMember(route.params.id)
  }
})
</script>

<style scoped>
.member-form-container {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.form-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-button) {
  margin-right: 10px;
}
</style>