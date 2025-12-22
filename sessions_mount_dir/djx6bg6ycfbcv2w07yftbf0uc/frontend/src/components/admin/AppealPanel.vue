<template>
  <div class="appeal-panel">
    <el-dialog
      v-model="visible"
      title="申诉处理"
      width="800px"
      :before-close="handleClose"
    >
      <div v-loading="loading" class="appeal-content">
        <div class="appeal-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="申诉ID">{{ appeal.id }}</el-descriptions-item>
            <el-descriptions-item label="用户ID">{{ appeal.user_id }}</el-descriptions-item>
            <el-descriptions-item label="用户名">{{ appeal.username }}</el-descriptions-item>
            <el-descriptions-item label="申诉时间">{{ formatDate(appeal.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="申诉状态">
              <el-tag :type="getStatusType(appeal.status)">{{ getStatusText(appeal.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="处理人">{{ appeal.handler || '未处理' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="appeal-details">
          <h4>申诉内容</h4>
          <p>{{ appeal.content }}</p>
        </div>

        <div v-if="appeal.evidence" class="appeal-evidence">
          <h4>证据材料</h4>
          <el-image
            v-for="(img, index) in appeal.evidence"
            :key="index"
            :src="img"
            :preview-src-list="appeal.evidence"
            fit="cover"
            class="evidence-image"
          />
        </div>

        <div v-if="appeal.status === 'pending'" class="appeal-actions">
          <el-form :model="form" label-width="80px">
            <el-form-item label="处理意见">
              <el-input
                v-model="form.comment"
                type="textarea"
                :rows="3"
                placeholder="请输入处理意见"
              />
            </el-form-item>
          </el-form>
        </div>

        <div v-if="appeal.status !== 'pending'" class="appeal-result">
          <h4>处理结果</h4>
          <p>{{ appeal.result || '暂无结果' }}</p>
          <p v-if="appeal.handled_at" class="handle-time">
            处理时间：{{ formatDate(appeal.handled_at) }}
          </p>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleClose">取消</el-button>
          <el-button
            v-if="appeal.status === 'pending'"
            type="success"
            @click="handleApprove"
          >
            通过申诉
          </el-button>
          <el-button
            v-if="appeal.status === 'pending'"
            type="danger"
            @click="handleReject"
          >
            拒绝申诉
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/date'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  appeal: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'refresh'])

const visible = ref(false)
const loading = ref(false)
const form = reactive({
  comment: ''
})

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    form.comment = ''
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const getStatusType = (status) => {
  const map = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    pending: '待处理',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return map[status] || '未知'
}

const handleClose = () => {
  visible.value = false
}

const handleApprove = async () => {
  if (!form.comment.trim()) {
    ElMessage.warning('请输入处理意见')
    return
  }

  try {
    await ElMessageBox.confirm('确认通过该申诉？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    loading.value = true
    // TODO: 调用API处理申诉
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('申诉已通过')
    emit('refresh')
    handleClose()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('处理失败')
    }
  } finally {
    loading.value = false
  }
}

const handleReject = async () => {
  if (!form.comment.trim()) {
    ElMessage.warning('请输入处理意见')
    return
  }

  try {
    await ElMessageBox.confirm('确认拒绝该申诉？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    loading.value = true
    // TODO: 调用API处理申诉
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('申诉已拒绝')
    emit('refresh')
    handleClose()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('处理失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.appeal-panel {
  .appeal-content {
    .appeal-info {
      margin-bottom: 20px;
    }

    .appeal-details,
    .appeal-evidence,
    .appeal-result {
      margin-bottom: 20px;

      h4 {
        margin-bottom: 10px;
        color: #606266;
      }

      p {
        color: #606266;
        line-height: 1.6;
      }
    }

    .evidence-image {
      width: 120px;
      height: 120px;
      margin-right: 10px;
      margin-bottom: 10px;
      border-radius: 4px;
      cursor: pointer;
    }

    .handle-time {
      font-size: 12px;
      color: #909399;
      margin-top: 10px;
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>