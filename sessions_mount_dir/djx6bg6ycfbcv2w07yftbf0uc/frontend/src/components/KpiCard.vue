<template>
  <div class="kpi-card">
    <div class="kpi-card__header">
      <div class="kpi-card__title">{{ title }}</div>
      <div class="kpi-card__icon" v-if="icon">
        <el-icon :size="24">
          <component :is="icon" />
        </el-icon>
      </div>
    </div>
    <div class="kpi-card__content">
      <div class="kpi-card__value">
        {{ formattedValue }}
      </div>
      <div class="kpi-card__trend" v-if="trend !== null">
        <span :class="['trend-indicator', trend > 0 ? 'trend-up' : 'trend-down']">
          <el-icon>
            <CaretTop v-if="trend > 0" />
            <CaretBottom v-else />
          </el-icon>
          {{ Math.abs(trend) }}%
        </span>
        <span class="trend-label">较上期</span>
      </div>
    </div>
    <div class="kpi-card__footer" v-if="footer">
      {{ footer }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CaretTop, CaretBottom } from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  icon: {
    type: String,
    default: ''
  },
  trend: {
    type: Number,
    default: null
  },
  footer: {
    type: String,
    default: ''
  },
  format: {
    type: String,
    default: 'number', // number, currency, percentage
    validator: (value) => ['number', 'currency', 'percentage'].includes(value)
  }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  
  switch (props.format) {
    case 'currency':
      return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY'
      }).format(props.value)
    case 'percentage':
      return `${props.value}%`
    default:
      return new Intl.NumberFormat('zh-CN').format(props.value)
  }
})
</script>

<style scoped>
.kpi-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.kpi-card:hover {
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.kpi-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.kpi-card__title {
  font-size: 14px;
  color: #909399;
  font-weight: 500;
}

.kpi-card__icon {
  color: #409eff;
}

.kpi-card__content {
  margin-bottom: 12px;
}

.kpi-card__value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.kpi-card__trend {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.trend-indicator {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 14px;
  font-weight: 500;
}

.trend-up {
  color: #67c23a;
}

.trend-down {
  color: #f56c6c;
}

.trend-label {
  font-size: 12px;
  color: #909399;
}

.kpi-card__footer {
  font-size: 12px;
  color: #c0c4cc;
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
}
</style>