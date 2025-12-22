<template>
  <div class="activity-detail-view">
    <div v-if="loading" class="loading">
      <p>加载中...</p>
    </div>
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchActivity" class="retry-btn">重试</button>
    </div>
    <div v-else-if="activity" class="activity-detail">
      <div class="activity-header">
        <h1>{{ activity.title }}</h1>
        <div class="activity-meta">
          <span class="category">{{ activity.category }}</span>
          <span class="difficulty">难度: {{ activity.difficulty }}</span>
        </div>
      </div>
      
      <div class="activity-content">
        <div class="activity-image" v-if="activity.image_url">
          <img :src="activity.image_url" :alt="activity.title" />
        </div>
        
        <div class="activity-info">
          <div class="info-section">
            <h3>活动详情</h3>
            <p>{{ activity.description }}</p>
          </div>
          
          <div class="info-section">
            <h3>时间地点</h3>
            <p><strong>开始时间:</strong> {{ formatDate(activity.start_time) }}</p>
            <p><strong>结束时间:</strong> {{ formatDate(activity.end_time) }}</p>
            <p><strong>地点:</strong> {{ activity.location }}</p>
          </div>
          
          <div class="info-section">
            <h3>主办方</h3>
            <p>{{ activity.merchant_name }}</p>
          </div>
          
          <div class="info-section">
            <h3>报名信息</h3>
            <p><strong>最大人数:</strong> {{ activity.max_participants }}人</p>
            <p><strong>已报名:</strong> {{ activity.current_participants }}人</p>
            <p><strong>截止时间:</strong> {{ formatDate(activity.registration_deadline) }}</p>
          </div>
        </div>
      </div>
      
      <div class="activity-actions">
        <button 
          v-if="!isRegistered && canRegister" 
          @click="handleRegister" 
          class="register-btn"
          :disabled="registering"
        >
          {{ registering ? '报名中...' : '立即报名' }}
        </button>
        <button 
          v-else-if="isRegistered" 
          @click="handleCancel" 
          class="cancel-btn"
          :disabled="cancelling"
        >
          {{ cancelling ? '取消中...' : '取消报名' }}
        </button>
        <p v-else-if="!canRegister" class="registration-closed">
          报名已结束或人数已满
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { activityAPI } from '@/services/api';

const route = useRoute();
const router = useRouter();

const activity = ref(null);
const loading = ref(true);
const error = ref(null);
const isRegistered = ref(false);
const registering = ref(false);
const cancelling = ref(false);

const canRegister = computed(() => {
  if (!activity.value) return false;
  const now = new Date();
  const deadline = new Date(activity.value.registration_deadline);
  return (
    now < deadline && 
    activity.value.current_participants < activity.value.max_participants
  );
});

const formatDate = (dateString) => {
  if (!dateString) return '未设置';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const fetchActivity = async () => {
  try {
    loading.value = true;
    error.value = null;
    const activityId = route.params.id;
    
    const [activityData, registrationStatus] = await Promise.all([
      activityAPI.getActivityById(activityId),
      activityAPI.checkRegistration(activityId)
    ]);
    
    activity.value = activityData;
    isRegistered.value = registrationStatus.is_registered;
  } catch (err) {
    error.value = err.response?.data?.detail || '获取活动详情失败';
    console.error('Failed to fetch activity:', err);
  } finally {
    loading.value = false;
  }
};

const handleRegister = async () => {
  try {
    registering.value = true;
    await activityAPI.registerActivity(activity.value.id);
    isRegistered.value = true;
    activity.value.current_participants += 1;
  } catch (err) {
    error.value = err.response?.data?.detail || '报名失败';
    console.error('Failed to register:', err);
  } finally {
    registering.value = false;
  }
};

const handleCancel = async () => {
  try {
    cancelling.value = true;
    await activityAPI.cancelRegistration(activity.value.id);
    isRegistered.value = false;
    activity.value.current_participants -= 1;
  } catch (err) {
    error.value = err.response?.data?.detail || '取消报名失败';
    console.error('Failed to cancel registration:', err);
  } finally {
    cancelling.value = false;
  }
};

onMounted(() => {
  fetchActivity();
});
</script>

<style scoped>
.activity-detail-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.loading, .error {
  text-align: center;
  padding: 40px;
}

.error {
  color: #e74c3c;
}

.retry-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-btn:hover {
  background-color: #2980b9;
}

.activity-header {
  margin-bottom: 30px;
}

.activity-header h1 {
  font-size: 2.5em;
  margin-bottom: 10px;
  color: #2c3e50;
}

.activity-meta {
  display: flex;
  gap: 20px;
  color: #7f8c8d;
}

.category {
  background-color: #3498db;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.9em;
}

.difficulty {
  font-weight: bold;
}

.activity-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin-bottom: 30px;
}

.activity-image img {
  width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.activity-info {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-section h3 {
  color: #2c3e50;
  margin-bottom: 10px;
  border-bottom: 2px solid #3498db;
  padding-bottom: 5px;
}

.info-section p {
  margin: 5px 0;
  line-height: 1.6;
}

.activity-actions {
  text-align: center;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.register-btn {
  background-color: #27ae60;
  color: white;
  padding: 12px 30px;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s;
}

.register-btn:hover:not(:disabled) {
  background-color: #229954;
}

.register-btn:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

.cancel-btn {
  background-color: #e74c3c;
  color: white;
  padding: 12px 30px;
  border: none;
  border-radius: 5px;
  font-size: 1.1em;
  cursor: pointer;
  transition: background-color 0.3s;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #c0392b;
}

.cancel-btn:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

.registration-closed {
  color: #7f8c8d;
  font-size: 1.1em;
}

@media (max-width: 768px) {
  .activity-content {
    grid-template-columns: 1fr;
  }
  
  .activity-header h1 {
    font-size: 2em;
  }
  
  .activity-meta {
    flex-direction: column;
    gap: 10px;
  }
}
</style>