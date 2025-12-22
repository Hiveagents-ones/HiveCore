<template>
  <div class="date-range-picker">
    <el-date-picker
      v-model="dateRange"
      type="daterange"
      range-separator="至"
      start-placeholder="开始日期"
      end-placeholder="结束日期"
      :shortcuts="shortcuts"
      :disabled-date="disabledDate"
      @change="handleDateChange"
      size="default"
      format="YYYY-MM-DD"
      value-format="YYYY-MM-DD"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElDatePicker } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  maxDays: {
    type: Number,
    default: 365
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const dateRange = ref(props.modelValue)

// 快捷选项
const shortcuts = [
  {
    text: '今天',
    value: () => {
      const end = new Date()
      const start = new Date()
      return [start, end]
    }
  },
  {
    text: '昨天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24)
      end.setTime(end.getTime() - 3600 * 1000 * 24)
      return [start, end]
    }
  },
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  },
  {
    text: '本月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(1)
      return [start, end]
    }
  },
  {
    text: '上月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setMonth(start.getMonth() - 1)
      start.setDate(1)
      end.setDate(0)
      return [start, end]
    }
  },
  {
    text: '最近3个月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setMonth(start.getMonth() - 3)
      return [start, end]
    }
  },
  {
    text: '最近6个月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setMonth(start.getMonth() - 6)
      return [start, end]
    }
  },
  {
    text: '今年',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setMonth(0)
      start.setDate(1)
      return [start, end]
    }
  },
  {
    text: '去年',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setFullYear(start.getFullYear() - 1)
      start.setMonth(0)
      start.setDate(1)
      end.setFullYear(end.getFullYear() - 1)
      end.setMonth(11)
      end.setDate(31)
      return [start, end]
    }
  }
]

// 禁用未来日期
const disabledDate = (time) => {
  return time.getTime() > Date.now()
}

// 处理日期变化
const handleDateChange = (val) => {
  emit('update:modelValue', val)
  emit('change', val)
}

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  dateRange.value = newVal
})
</script>

<style scoped>
.date-range-picker {
  display: inline-block;
}

:deep(.el-date-editor) {
  width: 280px;
}

:deep(.el-date-editor .el-range-input) {
  font-size: 14px;
}

:deep(.el-date-editor .el-range-separator) {
  padding: 0 5px;
}
</style>