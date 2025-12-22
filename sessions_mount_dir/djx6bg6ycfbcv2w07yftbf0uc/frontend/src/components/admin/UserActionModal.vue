<template>
  <el-dialog
    v-model="dialogVisible"
    :title="modalTitle"
    width="500px"
    :before-close="handleClose"
  >
    <div class="modal-content">
      <p class="action-message">
        {{ actionMessage }}
      </p>
      <div class="user-info">
        <p><strong>用户名:</strong> {{ user.username }}</p>
        <p><strong>邮箱:</strong> {{ user.email }}</p>
        <p><strong>当前状态:</strong>
          <el-tag :type="user.status === 'active' ? 'success' : 'danger'">
            {{ user.status === 'active' ? '正常' : '已封禁' }}
          </el-tag>
        </p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="action-form"
      >
        <el-form-item label="操作原因" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="4"
            placeholder="请输入操作原因"
          />
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          确认{{ actionType === 'ban' ? '封禁' : '解封' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  user: {
    type: Object,
    required: true
  },
  actionType: {
    type: String,
    required: true,
    validator: (value) => ['ban', 'unban'].includes(value)
  }
})

const emit = defineEmits(['update:visible', 'confirm'])

const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const form = ref({
  reason: ''
})

const rules = {
  reason: [
    { required: true, message: '请输入操作原因', trigger: 'blur' },
    { min: 5, max: 200, message: '长度在 5 到 200 个字符', trigger: 'blur' }
  ]
}

const modalTitle = computed(() => {
  return props.actionType === 'ban' ? '封禁用户' : '解封用户'
})

const actionMessage = computed(() => {
  if (props.actionType === 'ban') {
    return `您确定要封禁用户 "${props.user.username}" 吗？封禁后该用户将无法登录系统。`
  }
  return `您确定要解封用户 "${props.user.username}" 吗？解封后该用户将恢复正常使用。`
})

watch(() => props.visible, (newVal) => {
  dialogVisible.value = newVal
  if (newVal) {
    form.value.reason = ''
  }
})

watch(dialogVisible, (newVal) => {
  emit('update:visible', newVal)
})

const handleClose = () => {
  dialogVisible.value = false
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    emit('confirm', {
      userId: props.user.id,
      action: props.actionType,
      reason: form.value.reason
    })
    
    ElMessage.success(`${props.actionType === 'ban' ? '封禁' : '解封'}操作已提交`)
    handleClose()
  } catch (error) {
    console.error('表单验证失败:', error)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-content {
  padding: 20px 0;
}

.action-message {
  margin-bottom: 20px;
  color: #606266;
  line-height: 1.6;
}

.user-info {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.user-info p {
  margin: 8px 0;
  color: #606266;
}

.action-form {
  margin-top: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>