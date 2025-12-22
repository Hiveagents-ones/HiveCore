<template>
  <div class="activity-card">
    <div class="card-header">
      <img :src="activity.image || '/default-activity.jpg'" :alt="activity.title" class="activity-image">
      <div class="activity-status" :class="statusClass">
        {{ statusText }}
      </div>
    </div>
    
    <div class="card-body">
      <h3 class="activity-title">{{ activity.title }}</h3>
      <p class="activity-description">{{ activity.description }}</p>
      
      <div class="activity-info">
        <div class="info-item">
          <i class="icon-calendar"></i>
          <span>{{ formatDate(activity.start_time) }} - {{ formatDate(activity.end_time) }}</span>
        </div>
        <div class="info-item">
          <i class="icon-location"></i>
          <span>{{ activity.location }}</span>
        </div>
        <div class="info-item">
          <i class="icon-users"></i>
          <span>{{ activity.participants_count }}/{{ activity.max_participants }} 人</span>
        </div>
      </div>
      
      <div class="card-footer">
        <div class="activity-price">
          <span v-if="activity.price === 0" class="free">免费</span>
          <span v-else class="price">¥{{ activity.price }}</span>
        </div>
        <button 
          class="btn-participate" 
          :class="{ 'disabled': !canParticipate }"
          @click="handleParticipate"
          :disabled="!canParticipate"
        >
          {{ buttonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useActivityStore } from '@/stores/activity'
import { useRouter } from 'vue-router'

export default {
  name: 'ActivityCard',
  props: {
    activity: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const activityStore = useActivityStore()
    const router = useRouter()
    
    const statusClass = computed(() => {
      if (props.activity.status === 'cancelled') return 'cancelled'
      if (props.activity.status === 'completed') return 'completed'
      if (new Date(props.activity.end_time) < new Date()) return 'ended'
      if (new Date(props.activity.start_time) > new Date()) return 'upcoming'
      return 'ongoing'
    })
    
    const statusText = computed(() => {
      const statusMap = {
        'cancelled': '已取消',
        'completed': '已完成',
        'ended': '已结束',
        'upcoming': '即将开始',
        'ongoing': '进行中'
      }
      return statusMap[statusClass.value] || '未知'
    })
    
    const canParticipate = computed(() => {
      return (
        props.activity.status !== 'cancelled' &&
        props.activity.status !== 'completed' &&
        new Date(props.activity.end_time) > new Date() &&
        props.activity.participants_count < props.activity.max_participants &&
        !props.activity.is_participated
      )
    })
    
    const buttonText = computed(() => {
      if (props.activity.is_participated) return '已报名'
      if (props.activity.participants_count >= props.activity.max_participants) return '已满员'
      if (new Date(props.activity.end_time) < new Date()) return '已结束'
      return '立即报名'
    })
    
    const formatDate = (dateString) => {
      const date = new Date(dateString)
      return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
    }
    
    const handleParticipate = async () => {
      if (!canParticipate.value) return
      
      try {
        await activityStore.participateActivity(props.activity.id)
        // 触发父组件更新
        router.go(0)
      } catch (error) {
        console.error('报名失败:', error)
      }
    }
    
    return {
      statusClass,
      statusText,
      canParticipate,
      buttonText,
      formatDate,
      handleParticipate
    }
  }
}
</script>

<style scoped>
.activity-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
  cursor: pointer;
}

.activity-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.card-header {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.activity-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-status {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.activity-status.ongoing {
  background: #52c41a;
}

.activity-status.upcoming {
  background: #1890ff;
}

.activity-status.ended {
  background: #8c8c8c;
}

.activity-status.cancelled {
  background: #ff4d4f;
}

.activity-status.completed {
  background: #722ed1;
}

.card-body {
  padding: 16px;
}

.activity-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #262626;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.activity-description {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0 0 16px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.activity-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
  color: #595959;
}

.info-item i {
  margin-right: 8px;
  font-size: 16px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.activity-price .free {
  font-size: 16px;
  font-weight: 600;
  color: #52c41a;
}

.activity-price .price {
  font-size: 18px;
  font-weight: 600;
  color: #ff4d4f;
}

.btn-participate {
  padding: 8px 20px;
  border: none;
  border-radius: 20px;
  background: #1890ff;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.3s;
}

.btn-participate:hover:not(.disabled) {
  background: #40a9ff;
}

.btn-participate.disabled {
  background: #f0f0f0;
  color: #bfbfbf;
  cursor: not-allowed;
}
</style>