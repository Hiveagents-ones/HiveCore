<template>
  <div class="coach-form">
    <el-page-header @back="handleBack">
      <template #content>
        <span class="text-large font-600 mr-3">
          {{ isEdit ? '编辑教练' : '添加教练' }}
        </span>
      </template>
    </el-page-header>

    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
      class="mt-20"
    >
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="姓名" prop="name">
            <el-input v-model="formData.name" placeholder="请输入教练姓名" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="formData.phone" placeholder="请输入手机号" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="formData.email" placeholder="请输入邮箱" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态" prop="status">
            <el-select v-model="formData.status" placeholder="请选择状态">
              <el-option label="在职" value="active" />
              <el-option label="离职" value="inactive" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="专长" prop="specialties">
        <el-select
          v-model="formData.specialties"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="请选择或输入专长"
        >
          <el-option
            v-for="item in specialtyOptions"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="简介" prop="bio">
        <el-input
          v-model="formData.bio"
          type="textarea"
          :rows="4"
          placeholder="请输入教练简介"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
        <el-button @click="handleBack">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCoach, createCoach, updateCoach } from '@/api/coach'

const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const loading = ref(false)
const isEdit = ref(false)

const formData = ref({
  name: '',
  phone: '',
  email: '',
  status: 'active',
  specialties: [],
  bio: ''
})

const specialtyOptions = [
  '瑜伽',
  '普拉提',
  '动感单车',
  '力量训练',
  '有氧运动',
  '游泳',
  '拳击',
  '舞蹈'
]

const rules = {
  name: [
    { required: true, message: '请输入教练姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ],
  specialties: [
    { type: 'array', required: true, message: '请至少选择一个专长', trigger: 'change' }
  ]
}

const fetchCoach = async (id) => {
  try {
    loading.value = true
    const response = await getCoach(id)
    formData.value = response.data
  } catch (error) {
    ElMessage.error('获取教练信息失败')
    router.push('/coaches')
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    loading.value = true

    if (isEdit.value) {
      await updateCoach(route.params.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await createCoach(formData.value)
      ElMessage.success('创建成功')
    }

    router.push('/coaches')
  } catch (error) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    }
  } finally {
    loading.value = false
  }
}

const handleBack = () => {
  router.push('/coaches')
}

onMounted(() => {
  const { id } = route.params
  if (id) {
    isEdit.value = true
    fetchCoach(id)
  }
})
</script>

<style scoped>
.coach-form {
  padding: 20px;
}

.mt-20 {
  margin-top: 20px;
}

.text-large {
  font-size: 18px;
}

.font-600 {
  font-weight: 600;
}

.mr-3 {
  margin-right: 12px;
}
</style>