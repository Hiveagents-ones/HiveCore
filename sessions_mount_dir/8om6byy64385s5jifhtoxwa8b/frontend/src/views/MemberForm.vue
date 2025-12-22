<template>
  <div class="member-form">
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑会员' : '会员注册' }}</span>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        class="member-form-content"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入会员姓名" />
        </el-form-item>
        
        <el-form-item label="联系方式" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入手机号码" />
        </el-form-item>
        
        <el-form-item label="会员卡号" prop="card_number">
          <el-input v-model="formData.card_number" placeholder="请输入会员卡号" />
        </el-form-item>
        
        <el-form-item label="会员等级" prop="level">
          <el-select v-model="formData.level" placeholder="请选择会员等级">
            <el-option label="普通会员" value="regular" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="会员类型" prop="member_type">
          <el-radio-group v-model="formData.member_type">
            <el-radio label="time">课时制</el-radio>
            <el-radio label="period">有效期制</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item 
          v-if="formData.member_type === 'time'" 
          label="剩余课时" 
          prop="remaining_sessions"
        >
          <el-input-number 
            v-model="formData.remaining_sessions" 
            :min="0" 
            :max="999"
            placeholder="请输入剩余课时"
          />
        </el-form-item>
        
        <el-form-item 
          v-if="formData.member_type === 'period'" 
          label="有效期至" 
          prop="expiry_date"
        >
          <el-date-picker
            v-model="formData.expiry_date"
            type="date"
            placeholder="选择有效期截止日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        
        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="formData.notes"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息（选填）"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit">{{ isEdit ? '保存修改' : '注册会员' }}</el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  getMemberDetail, 
  createMember, 
  updateMember,
  registerMember 
} from '@/api/member'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const isEdit = ref(false)

const formData = reactive({
  name: '',
  phone: '',
  card_number: '',
  level: 'regular',
  member_type: 'time',
  remaining_sessions: 0,
  expiry_date: '',
  notes: ''
})

const rules = {
  name: [
    { required: true, message: '请输入会员姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
  ],
  card_number: [
    { required: true, message: '请输入会员卡号', trigger: 'blur' },
    { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  level: [
    { required: true, message: '请选择会员等级', trigger: 'change' }
  ],
  member_type: [
    { required: true, message: '请选择会员类型', trigger: 'change' }
  ],
  remaining_sessions: [
    { 
      validator: (rule, value, callback) => {
        if (formData.member_type === 'time' && (!value || value < 0)) {
          callback(new Error('请输入有效的课时数'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ],
  expiry_date: [
    { 
      validator: (rule, value, callback) => {
        if (formData.member_type === 'period' && !value) {
          callback(new Error('请选择有效期'))
        } else {
          callback()
        }
      }, 
      trigger: 'change' 
    }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    const submitData = { ...formData }
    if (submitData.member_type === 'time') {
      delete submitData.expiry_date
    } else {
      delete submitData.remaining_sessions
    }
    
    if (isEdit.value) {
      await updateMember(route.params.id, submitData)
      ElMessage.success('会员信息更新成功')
    } else {
      await registerMember(submitData)
      ElMessage.success('会员注册成功')
    }
    
    router.push('/members')
  } catch (error) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error(isEdit.value ? '更新失败' : '注册失败')
    }
  }
}

const handleCancel = () => {
  router.push('/members')
}

const loadMemberDetail = async (id) => {
  try {
    const response = await getMemberDetail(id)
    Object.assign(formData, response.data)
  } catch (error) {
    ElMessage.error('获取会员信息失败')
    router.push('/members')
  }
}

onMounted(() => {
  if (route.params.id) {
    isEdit.value = true
    loadMemberDetail(route.params.id)
  }
})
</script>

<style scoped>
.member-form {
  padding: 20px;
}

.form-card {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.member-form-content {
  padding: 20px;
}

.el-form-item {
  margin-bottom: 24px;
}
</style>