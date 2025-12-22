<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      label-position="right"
    >
      <el-form-item label="会员ID" prop="member_id">
        <el-input-number
          v-model="formData.member_id"
          :min="1"
          controls-position="right"
          placeholder="请输入会员ID"
          <template #append>
            <el-tooltip content="请输入有效的会员ID" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
        />
      </el-form-item>

      <el-form-item label="支付类型" prop="payment_type">
        <el-select
          v-model="formData.payment_type"
          placeholder="请选择支付类型"
          @change="handlePaymentTypeChange"
        >
          <el-option label="会员费" value="membership" />
          <el-option label="课程费" value="course" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="formData.payment_type === 'membership'" label="会员类型" prop="membership_type">
        <el-select v-model="formData.membership_type" placeholder="请选择会员类型">
          <el-option label="月度会员" value="monthly" />
          <el-option label="季度会员" value="quarterly" />
          <el-option label="年度会员" value="yearly" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="formData.payment_type === 'course'" label="课程ID" prop="course_id">
        <el-input-number
          v-model="formData.course_id"
          :min="1"
          controls-position="right"
          placeholder="请输入课程ID"
        />
      </el-form-item>

      <el-form-item label="金额" prop="amount">
        <el-input-number
          v-model="formData.amount"
          :min="0"
          :precision="2"
          controls-position="right"
          placeholder="请输入金额"
          :disabled="calculatedAmount > 0"
        />
        <div v-if="calculatedAmount > 0" class="calculated-amount">
          系统计算金额: {{ calculatedAmount.toFixed(2) }}
        </div>
      </el-form-item>

      <el-form-item label="支付日期" prop="payment_date">
        <el-date-picker
          v-model="formData.payment_date"
          type="date"
          placeholder="选择支付日期"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSubmit">提交</el-button>
        <el-button @click="handleClose">取消</el-button>
      </el-form-item>
    </el-form>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createPayment } from '@/api/payments'
import { getMembershipPrice, getCoursePrice } from '@/api/pricing'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  editData: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:visible', 'success'])

const formRef = ref(null)
const membershipPrices = ref({})
const coursePrices = ref({})
const formData = ref({
  member_id: null,
  payment_type: '',
  membership_type: '',
  course_id: null,
  amount: null,
  payment_date: new Date().toISOString().split('T')[0]
})

const rules = {
  member_id: [{ required: true, message: '请输入会员ID', trigger: 'blur' }],
  payment_type: [{ required: true, message: '请选择支付类型', trigger: 'change' }],
  membership_type: [
    {
      required: true,
      validator: (rule, value, callback) => {
        if (formData.value.payment_type === 'membership' && !value) {
          callback(new Error('请选择会员类型'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ],
  course_id: [
    {
      required: true,
      validator: (rule, value, callback) => {
        if (formData.value.payment_type === 'course' && !value) {
          callback(new Error('请输入课程ID'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  payment_date: [{ required: true, message: '请选择支付日期', trigger: 'change' }]
}

const dialogTitle = computed(() => {
  return props.editData.id ? '编辑收费记录' : '新增收费记录'
})

const calculatedAmount = computed(() => {
  if (formData.value.payment_type === 'membership' && formData.value.membership_type) {
    return membershipPrices.value[formData.value.membership_type] || 0
  } else if (formData.value.payment_type === 'course' && formData.value.course_id) {
    return coursePrices.value[formData.value.course_id] || 0
  }
  return 0
})
  return props.editData.id ? '编辑收费记录' : '新增收费记录'
})

watch(
  () => props.visible,
  (val) => {
    if (val && props.editData.id) {
      formData.value = { ...props.editData }
    } else {
      resetForm()
    }
  }
)

const handlePaymentTypeChange = (val) => {
  formData.value.amount = calculatedAmount.value
  if (val === 'membership') {
    formData.value.course_id = null
  } else if (val === 'course') {
    formData.value.membership_type = ''
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    
    const payload = {
      ...formData.value,
      payment_date: formData.value.payment_date
    }
    
    if (props.editData.id) {
      payload.id = props.editData.id
    }
    
    await createPayment(payload)
    ElMessage.success(props.editData.id ? '更新成功' : '创建成功')
    emit('success')
    handleClose()
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleClose = () => {
  emit('update:visible', false)
}

const resetForm = () => {
  formData.value = {
    member_id: null,
    payment_type: '',
    membership_type: '',
    course_id: null,
    amount: null,
    payment_date: new Date().toISOString().split('T')[0]
  }
  if (formRef.value) {
    formRef.value.resetFields()
  }
}
</script>

<style scoped>
.el-input-number {
  width: 100%;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

watch(
  calculatedAmount,
  (newVal) => {
    if (newVal > 0) {
      formData.value.amount = newVal
    }
  }
)