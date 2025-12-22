<template>

  <div class="schedule-form">
    <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
      <el-form-item label="教练ID" prop="coach_id">
        <el-input v-model="form.coach_id" type="number" />
      </el-form-item>
      
      <el-form-item label="开始时间" prop="start_time">
        <el-date-picker
          v-model="form.start_time"
          type="datetime"
          placeholder="选择开始时间"
          value-format="YYYY-MM-DD HH:mm:ss"
        />
      </el-form-item>
      
      <el-form-item label="结束时间" prop="end_time">
        <el-date-picker
          v-model="form.end_time"
          type="datetime"
          placeholder="选择结束时间"
          value-format="YYYY-MM-DD HH:mm:ss"
        />
      </el-form-item>
      
      <el-form-item label="是否可用" prop="available">
        <el-switch v-model="form.available" />
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="submitForm">提交</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'
import { createSchedule, updateSchedule } from '../api/coaches'

const props = defineProps({

  initialData: {
    type: Object,
    default: () => ({
      coach_id: null,
      start_time: '',
      end_time: '',
      available: true
    })
  },
  isEdit: {
    type: Boolean,
    default: false
  },
  scheduleId: {
    type: Number,
    default: null
  }
})

const emits = defineEmits(['success'])

const form = ref({...props.initialData})
const formRef = ref(null)

const rules = {
  coach_id: [
    { required: true, message: '请选择教练', trigger: 'blur' }
  ],
  start_time: [
    { required: true, message: '请选择开始时间', trigger: 'change' }
  ],
  end_time: [
    { required: true, message: '请选择结束时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (new Date(value) <= new Date(form.value.start_time)) {
          callback(new Error('结束时间必须晚于开始时间'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

const submitForm = async () => {
  try {
    await formRef.value.validate()
    
    if (props.isEdit) {
      await updateSchedule(props.scheduleId, form.value)
      ElMessage.success('排班更新成功')
    } else {
      await createSchedule(form.value)
      ElMessage.success('排班创建成功')
    }
    
    emits('success')
    resetForm()
  } catch (error) {
    console.error('提交失败:', error)
    ElMessage.error('提交失败，请检查表单')
  }
}

const resetForm = () => {
  formRef.value.resetFields()
}
</script>

<style scoped>
.schedule-form {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}
</style>