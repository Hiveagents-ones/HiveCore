<template>
  <div class="activity-list-view">
    <div class="header">
      <h1>活动列表</h1>
      <div class="search-bar">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索活动..."
          @keyup.enter="handleSearch"
        />
        <button @click="handleSearch">搜索</button>
      </div>
    </div>

    <div class="filters">
      <select v-model="statusFilter" @change="fetchActivities">
        <option value="">全部状态</option>
        <option value="upcoming">即将开始</option>
        <option value="ongoing">进行中</option>
        <option value="completed">已结束</option>
      </select>
      <select v-model="typeFilter" @change="fetchActivities">
        <option value="">全部类型</option>
        <option value="fitness">健身</option>
        <option value="yoga">瑜伽</option>
        <option value="running">跑步</option>
        <option value="swimming">游泳</option>
      </select>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="activities.length === 0" class="empty">暂无活动</div>
    <div v-else class="activity-grid">
      <div
        v-for="activity in activities"
        :key="activity.id"
        class="activity-card"
        @click="goToDetail(activity.id)"
      >
        <div class="activity-image">
          <img :src="activity.image_url || '/default-activity.jpg'" :alt="activity.title" />
        </div>
        <div class="activity-content">
          <h3>{{ activity.title }}</h3>
          <p class="description">{{ activity.description }}</p>
          <div class="activity-info">
            <span class="date">
              <i class="icon-calendar"></i>
              {{ formatDate(activity.start_time) }}
            </span>
            <span class="location">
              <i class="icon-location"></i>
              {{ activity.location }}
            </span>
          </div>
          <div class="activity-meta">
            <span class="type">{{ activity.type }}</span>
            <span class="capacity">
              {{ activity.current_participants }}/{{ activity.max_participants }}人
            </span>
          </div>
          <div class="activity-status">
            <span :class="['status-badge', activity.status]">
              {{ getStatusText(activity.status) }}
            </span>
          </div>
          <div class="activity-actions">
            <button
              v-if="activity.is_registered"
              class="btn-cancel"
              @click.stop="handleCancelRegistration(activity.id)"
            >
              取消报名
            </button>
            <button
              v-else
              class="btn-register"
              @click.stop="handleRegister(activity.id)"
              :disabled="activity.current_participants >= activity.max_participants"
            >
              {{ activity.current_participants >= activity.max_participants ? '已满员' : '立即报名' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button
        v-for="page in totalPages"
        :key="page"
        :class="['page-btn', { active: currentPage === page }]"
        @click="changePage(page)"
      >
        {{ page }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { activityAPI } from '@/services/api.js';

const router = useRouter();
const activities = ref([]);
const loading = ref(false);
const error = ref('');
const searchQuery = ref('');
const statusFilter = ref('');
const typeFilter = ref('');
const currentPage = ref(1);
const pageSize = ref(12);
const total = ref(0);

const totalPages = computed(() => Math.ceil(total.value / pageSize.value));

const fetchActivities = async () => {
  loading.value = true;
  error.value = '';
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (statusFilter.value) params.status = statusFilter.value;
    if (typeFilter.value) params.type = typeFilter.value;
    
    const response = await activityAPI.getActivities(params);
    activities.value = response.items || [];
    total.value = response.total || 0;
  } catch (err) {
    error.value = '获取活动列表失败，请重试';
    console.error('Failed to fetch activities:', err);
  } finally {
    loading.value = false;
  }
};

const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    fetchActivities();
    return;
  }
  
  loading.value = true;
  error.value = '';
  try {
    const response = await activityAPI.searchActivities(searchQuery.value);
    activities.value = response.items || [];
    total.value = response.total || 0;
  } catch (err) {
    error.value = '搜索失败，请重试';
    console.error('Failed to search activities:', err);
  } finally {
    loading.value = false;
  }
};

const handleRegister = async (activityId) => {
  try {
    await activityAPI.registerActivity(activityId);
    // Update the activity registration status
    const activity = activities.value.find(a => a.id === activityId);
    if (activity) {
      activity.is_registered = true;
      activity.current_participants += 1;
    }
  } catch (err) {
    error.value = '报名失败，请重试';
    console.error('Failed to register activity:', err);
  }
};

const handleCancelRegistration = async (activityId) => {
  try {
    await activityAPI.cancelRegistration(activityId);
    // Update the activity registration status
    const activity = activities.value.find(a => a.id === activityId);
    if (activity) {
      activity.is_registered = false;
      activity.current_participants -= 1;
    }
  } catch (err) {
    error.value = '取消报名失败，请重试';
    console.error('Failed to cancel registration:', err);
  }
};

const goToDetail = (activityId) => {
  router.push(`/activities/${activityId}`);
};

const changePage = (page) => {
  currentPage.value = page;
  fetchActivities();
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getStatusText = (status) => {
  const statusMap = {
    upcoming: '即将开始',
    ongoing: '进行中',
    completed: '已结束',
    cancelled: '已取消',
  };
  return statusMap[status] || status;
};

onMounted(() => {
  fetchActivities();
});
</script>

<style scoped>
.activity-list-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 28px;
  color: #333;
  margin: 0;
}

.search-bar {
  display: flex;
  gap: 10px;
}

.search-bar input {
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 300px;
  font-size: 14px;
}

.search-bar button {
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.search-bar button:hover {
  background-color: #0056b3;
}

.filters {
  display: flex;
  gap: 15px;
  margin-bottom: 30px;
}

.filters select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background-color: white;
  cursor: pointer;
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 40px;
  font-size: 16px;
  color: #666;
}

.error {
  color: #dc3545;
}

.activity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.activity-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.activity-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.activity-image {
  height: 200px;
  overflow: hidden;
}

.activity-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-content {
  padding: 20px;
}

.activity-content h3 {
  margin: 0 0 10px;
  font-size: 18px;
  color: #333;
}

.description {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 15px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.activity-info {
  display: flex;
  gap: 15px;
  margin-bottom: 10px;
}

.activity-info span {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  color: #666;
}

.activity-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.type {
  background-color: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #495057;
}

.capacity {
  font-size: 14px;
  color: #666;
}

.activity-status {
  margin-bottom: 15px;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.upcoming {
  background-color: #fff3cd;
  color: #856404;
}

.status-badge.ongoing {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.completed {
  background-color: #f8d7da;
  color: #721c24;
}

.activity-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-register,
.btn-cancel {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn-register {
  background-color: #28a745;
  color: white;
}

.btn-register:hover:not(:disabled) {
  background-color: #218838;
}

.btn-register:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.btn-cancel {
  background-color: #dc3545;
  color: white;
}

.btn-cancel:hover {
  background-color: #c82333;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 5px;
}

.page-btn {
  padding: 8px 12px;
  border: 1px solid #ddd;
  background-color: white;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
}

.page-btn:hover {
  background-color: #f8f9fa;
}

.page-btn.active {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }

  .search-bar input {
    width: 100%;
  }

  .filters {
    flex-direction: column;
  }

  .activity-grid {
    grid-template-columns: 1fr;
  }
}
</style>