<template>
  <div class="member-detail">
    <h1>会员详情</h1>
    
    <div v-if="loading" class="loading">
      加载中...
    </div>
    
    <div v-else-if="member" class="member-info">
      <div class="info-row">
        <span class="label">会员ID:</span>
        <span class="value">{{ member.id }}</span>
      </div>
      <div class="info-row">
        <span class="label">姓名:</span>
        <span class="value">{{ member.name }}</span>
      </div>
      <div class="info-row">
        <span class="label">电话:</span>
        <span class="value">{{ member.phone }}</span>
      </div>
      <div class="info-row">
        <span class="label">邮箱:</span>
        <span class="value">{{ member.email }}</span>
      </div>
      <div class="info-row">
        <span class="label">加入日期:</span>
        <span class="value">{{ member.join_date }}</span>
      </div>
      
      <div class="actions">
        <router-link :to="`/members/${member.id}/edit`" class="btn edit-btn">编辑</router-link>
        <router-link to="/members" class="btn back-btn">返回列表</router-link>
      </div>
    </div>
    
    <div v-else class="not-found">
      未找到会员信息
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { getMemberById } from '../api/members';
import { getMemberLogs } from '../api/audit';

export default {
  name: 'MemberDetail',
  setup() {
    const route = useRoute();
    const member = ref(null);
    const loading = ref(true);
    
    const fetchMember = async () => {
      try {
        const memberData = await getMemberById(route.params.id);
        member.value = memberData;
      } catch (error) {
        console.error('获取会员详情失败:', error);
      } finally {
        loading.value = false;
      }
    };
    
    onMounted(() => {
      fetchMember();
    });
    
    return {
      member,
      loading
    };
  }
};
</script>

<style scoped>
.member-detail {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  color: #333;
  margin-bottom: 20px;
}

.loading, .not-found {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.member-info {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.info-row {
  display: flex;
  margin-bottom: 15px;
}

.label {
  font-weight: bold;
  width: 100px;
  color: #555;
}

.value {
  flex: 1;
}

.actions {
  margin-top: 30px;
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
  font-weight: 500;
}

.edit-btn {
  background-color: #4CAF50;
  color: white;
  border: none;
}

.edit-btn:hover {
  background-color: #45a049;
}

.back-btn {
  background-color: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
  margin-left: 10px;
}

.back-btn:hover {
  background-color: #e0e0e0;
}
</style>