<template>
  <el-dialog
    v-model="dialogVisible"
    title="隐私政策"
    width="600px"
    :before-close="handleClose"
    :close-on-click-modal="false"
  >
    <div class="privacy-content">
      <div class="policy-text">
        <h3>隐私政策</h3>
        <p>感谢您选择成为我们健身房的会员。我们重视您的隐私，并承诺保护您的个人信息安全。</p>
        
        <h4>1. 信息收集</h4>
        <p>当您注册会员时，我们会收集您的个人信息，包括但不限于：</p>
        <ul>
          <li>姓名</li>
          <li>手机号码</li>
          <li>身份证号</li>
          <li>会员套餐选择</li>
        </ul>
        
        <h4>2. 信息使用</h4>
        <p>我们使用您的个人信息用于：</p>
        <ul>
          <li>创建和管理您的会员账户</li>
          <li>提供个性化的健身服务</li>
          <li>与您进行沟通和联系</li>
          <li>改进我们的服务质量</li>
        </ul>
        
        <h4>3. 信息保护</h4>
        <p>我们采取适当的安全措施来保护您的个人信息，防止未授权的访问、使用或泄露。</p>
        
        <h4>4. 信息共享</h4>
        <p>除非获得您的明确同意或法律有关规定要求，我们不会向第三方共享您的个人信息。</p>
        
        <h4>5. 您的权利</h4>
        <p>您有权访问、更新或删除您的个人信息。如需帮助，请联系我们的客服团队。</p>
        
        <h4>6. 联系我们</h4>
        <p>如有任何关于隐私政策的问题，请联系：</p>
        <ul>
          <li>电话：400-123-4567</li>
          <li>邮箱：privacy@gym.com</li>
        </ul>
        
        <p class="update-time">最后更新时间：2024年1月</p>
      </div>
      
      <div class="agreement-section">
        <el-checkbox v-model="agreed" size="large">
          我已阅读并同意以上隐私政策
        </el-checkbox>
      </div>
    </div>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleConfirm"
          :disabled="!agreed"
        >
          确认
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'confirm'])

const dialogVisible = ref(false)
const agreed = ref(false)

// 监听父组件传入的visible属性
watch(() => props.visible, (newVal) => {
  dialogVisible.value = newVal
  if (newVal) {
    agreed.value = false // 每次打开弹窗重置复选框
  }
})

// 监听内部dialogVisible的变化，同步到父组件
watch(dialogVisible, (newVal) => {
  emit('update:visible', newVal)
})

const handleClose = () => {
  dialogVisible.value = false
}

const handleConfirm = () => {
  if (agreed.value) {
    emit('confirm')
    dialogVisible.value = false
  }
}
</script>

<style scoped>
.privacy-content {
  max-height: 60vh;
  overflow-y: auto;
}

.policy-text {
  margin-bottom: 20px;
  padding: 0 10px;
}

.policy-text h3 {
  color: #303133;
  font-size: 18px;
  margin-bottom: 15px;
  text-align: center;
}

.policy-text h4 {
  color: #409EFF;
  font-size: 16px;
  margin: 20px 0 10px 0;
}

.policy-text p {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 10px;
}

.policy-text ul {
  margin: 10px 0;
  padding-left: 20px;
}

.policy-text li {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 5px;
}

.update-time {
  color: #909399 !important;
  font-size: 12px !important;
  margin-top: 20px !important;
  text-align: right;
}

.agreement-section {
  padding: 20px 10px;
  border-top: 1px solid #EBEEF5;
  background-color: #F5F7FA;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 滚动条样式 */
.privacy-content::-webkit-scrollbar {
  width: 6px;
}

.privacy-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.privacy-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.privacy-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>