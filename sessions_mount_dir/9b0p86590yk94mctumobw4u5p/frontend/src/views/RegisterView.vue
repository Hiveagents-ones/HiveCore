<template>
  <div class="register-view">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>会员注册</h2>
        </div>
      </template>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="rules"
        label-width="120px"
        size="large"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="registerForm.name" placeholder="请输入您的姓名" />
        </el-form-item>
        
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="registerForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        
        <el-form-item label="身份证号" prop="idCard">
          <el-input v-model="registerForm.idCard" placeholder="请输入身份证号" />
        </el-form-item>
        
        <el-form-item label="会员套餐" prop="plan">
          <el-radio-group v-model="registerForm.plan">
            <el-radio label="monthly">月度会员 - ¥299</el-radio>
            <el-radio label="quarterly">季度会员 - ¥799</el-radio>
            <el-radio label="yearly">年度会员 - ¥2999</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="支付方式" prop="paymentMethod">
          <el-select v-model="registerForm.paymentMethod" placeholder="请选择支付方式">
            <el-option label="支付宝" value="alipay" />
            <el-option label="微信支付" value="wechat" />
            <el-option label="银行卡" value="bank" />
          </el-select>
        </el-form-item>
        
        <el-form-item prop="agreement">
          <el-checkbox v-model="registerForm.agreement">
            我已阅读并同意
            <el-link type="primary" @click="showPrivacyPolicy">隐私政策</el-link>
            和
            <el-link type="primary" @click="showTerms">服务条款</el-link>
          </el-checkbox>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="submitForm"
            style="width: 100%"
          >
            立即注册
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 隐私政策对话框 -->
    <el-dialog
      v-model="privacyDialogVisible"
      title="隐私政策"
      width="50%"
    >
      <div class="policy-content">
        <h3>1. 信息收集</h3>
        <p>我们收集您的个人信息仅用于会员注册和服务提供。</p>
        
        <h3>2. 信息使用</h3>
        <p>您的信息将用于会员管理、服务通知和账单处理。</p>
        
        <h3>3. 信息保护</h3>
        <p>我们采用行业标准的安全措施保护您的个人信息。</p>
        
        <h3>4. 信息共享</h3>
        <p>未经您的同意，我们不会向第三方共享您的个人信息。</p>
      </div>
      <template #footer>
        <el-button @click="privacyDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 服务条款对话框 -->
    <el-dialog
      v-model="termsDialogVisible"
      title="服务条款"
      width="50%"
    >
      <div class="terms-content">
        <h3>1. 服务说明</h3>
        <p>本健身房提供专业的健身设施和指导服务。</p>
        
        <h3>2. 会员权利</h3>
        <p>会员享有使用健身房设施和参加团体课程的权利。</p>
        
        <h3>3. 会员义务</h3>
        <p>会员应遵守健身房规定，爱护设施，尊重他人。</p>
        
        <h3>4. 退费政策</h3>
        <p>会员卡一经售出，不予退费，可转让。</p>
      </div>
      <template #footer>
        <el-button @click="termsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const registerFormRef = ref(null)
const loading = ref(false)
const privacyDialogVisible = ref(false)
const termsDialogVisible = ref(false)

const registerForm = reactive({
  name: '',
  phone: '',
  idCard: '',
  plan: 'monthly',
  paymentMethod: '',
  agreement: false
})

const validatePhone = (rule, value, callback) => {
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!value) {
    callback(new Error('请输入手机号'))
  } else if (!phoneRegex.test(value)) {
    callback(new Error('请输入正确的手机号'))
  } else {
    callback()
  }
}

const validateIdCard = (rule, value, callback) => {
  const idCardRegex = /(^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}$)/
  if (!value) {
    callback(new Error('请输入身份证号'))
  } else if (!idCardRegex.test(value)) {
    callback(new Error('请输入正确的身份证号'))
  } else {
    callback()
  }
}

const rules = reactive({
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  phone: [
    { validator: validatePhone, trigger: 'blur' }
  ],
  idCard: [
    { validator: validateIdCard, trigger: 'blur' }
  ],
  plan: [
    { required: true, message: '请选择会员套餐', trigger: 'change' }
  ],
  paymentMethod: [
    { required: true, message: '请选择支付方式', trigger: 'change' }
  ],
  agreement: [
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请同意隐私政策和服务条款'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
})

const showPrivacyPolicy = () => {
  privacyDialogVisible.value = true
}

const showTerms = () => {
  termsDialogVisible.value = true
}

const submitForm = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await axios.post('/api/register', {
          name: registerForm.name,
          phone: registerForm.phone,
          id_card: registerForm.idCard,
          plan: registerForm.plan,
          payment_method: registerForm.paymentMethod
        })
        
        ElMessage.success('注册成功！')
        router.push('/success')
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '注册失败，请重试')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.register-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 600px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #303133;
  font-weight: 600;
}

.policy-content,
.terms-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 0 20px;
}

.policy-content h3,
.terms-content h3 {
  color: #409EFF;
  margin-top: 20px;
  margin-bottom: 10px;
}

.policy-content p,
.terms-content p {
  line-height: 1.6;
  color: #606266;
  margin-bottom: 15px;
}

:deep(.el-radio) {
  display: block;
  margin-bottom: 10px;
  margin-right: 0;
}

:deep(.el-form-item__content) {
  flex-wrap: wrap;
}
</style>