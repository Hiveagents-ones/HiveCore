<template>
  <div class="system-config-view">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>系统配置</span>
          <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
        </div>
      </template>

      <el-form :model="configForm" label-width="150px" class="config-form">
        <!-- 基本配置 -->
        <el-divider content-position="left">基本配置</el-divider>
        
        <el-form-item label="平台名称">
          <el-input v-model="configForm.platform_name" placeholder="请输入平台名称" />
        </el-form-item>

        <el-form-item label="平台服务费率">
          <el-input-number 
            v-model="configForm.service_fee_rate" 
            :min="0" 
            :max="100" 
            :precision="2"
            :step="0.1"
            class="fee-rate-input"
          />
          <span class="input-suffix">%</span>
        </el-form-item>

        <el-form-item label="默认头像">
          <el-input v-model="configForm.default_avatar" placeholder="请输入默认头像URL" />
        </el-form-item>

        <!-- 公告配置 -->
        <el-divider content-position="left">公告配置</el-divider>
        
        <el-form-item label="系统公告">
          <el-input 
            v-model="configForm.announcement" 
            type="textarea" 
            :rows="4"
            placeholder="请输入系统公告内容"
          />
        </el-form-item>

        <el-form-item label="公告状态">
          <el-switch 
            v-model="configForm.announcement_enabled" 
            active-text="启用" 
            inactive-text="禁用"
          />
        </el-form-item>

        <!-- 第三方服务配置 -->
        <el-divider content-position="left">第三方服务配置</el-divider>
        
        <el-form-item label="支付服务">
          <el-select v-model="configForm.payment_service" placeholder="选择支付服务">
            <el-option label="支付宝" value="alipay" />
            <el-option label="微信支付" value="wechat" />
            <el-option label="银联" value="unionpay" />
          </el-select>
        </el-form-item>

        <el-form-item label="短信服务">
          <el-select v-model="configForm.sms_service" placeholder="选择短信服务">
            <el-option label="阿里云" value="aliyun" />
            <el-option label="腾讯云" value="tencent" />
            <el-option label="华为云" value="huawei" />
          </el-select>
        </el-form-item>

        <el-form-item label="存储服务">
          <el-select v-model="configForm.storage_service" placeholder="选择存储服务">
            <el-option label="阿里云OSS" value="aliyun_oss" />
            <el-option label="腾讯云COS" value="tencent_cos" />
            <el-option label="七牛云" value="qiniu" />
          </el-select>
        </el-form-item>

        <!-- API密钥配置 -->
        <el-divider content-position="left">API密钥配置</el-divider>
        
        <el-form-item label="支付密钥">
          <el-input 
            v-model="configForm.payment_secret" 
            type="password" 
            show-password
            placeholder="请输入支付服务密钥"
          />
        </el-form-item>

        <el-form-item label="短信密钥">
          <el-input 
            v-model="configForm.sms_secret" 
            type="password" 
            show-password
            placeholder="请输入短信服务密钥"
          />
        </el-form-item>

        <el-form-item label="存储密钥">
          <el-input 
            v-model="configForm.storage_secret" 
            type="password" 
            show-password
            placeholder="请输入存储服务密钥"
          />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '@/api/config'

// 配置表单数据
const configForm = ref({
  platform_name: '',
  service_fee_rate: 0,
  default_avatar: '',
  announcement: '',
  announcement_enabled: false,
  payment_service: '',
  sms_service: '',
  storage_service: '',
  payment_secret: '',
  sms_secret: '',
  storage_secret: ''
})

// 保存状态
const saving = ref(false)

// 获取系统配置
const fetchConfig = async () => {
  try {
    const response = await configApi.getConfig()
    if (response.data) {
      configForm.value = { ...configForm.value, ...response.data }
    }
  } catch (error) {
    ElMessage.error('获取系统配置失败')
    console.error('Failed to fetch config:', error)
  }
}

// 保存配置
const handleSave = async () => {
  saving.value = true
  try {
    await configApi.updateConfig(configForm.value)
    ElMessage.success('配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error('Failed to save config:', error)
  } finally {
    saving.value = false
  }
}

// 组件挂载时获取配置
onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.system-config-view {
  padding: 20px;
}

.config-card {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-form {
  padding: 20px;
}

.fee-rate-input {
  width: 200px;
}

.input-suffix {
  margin-left: 10px;
  color: #909399;
}

.el-divider {
  margin: 30px 0 20px 0;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}
</style>