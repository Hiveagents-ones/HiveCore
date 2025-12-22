<template>
  <div class="member-list-container">
    <h1>会员列表</h1>
    <div class="action-bar">
      <router-link to="/members/new" class="btn btn-primary">
        新增会员
      </router-link>
    </div>
    
    <div v-if="loading" class="loading-indicator">加载中...</div>
    
    <div v-if="error" class="error-message">
      加载会员列表失败: {{ error.message }}
    </div>
    
    <table v-if="members.length > 0" class="member-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>姓名</th>
          <th>电话</th>
          <th>邮箱</th>
          <th>加入日期</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in members" :key="member.id">
          <td>{{ member.id }}</td>
          <td>{{ member.name }}</td>
          <td>{{ member.phone }}</td>
          <td>{{ member.email }}</td>
          <td>{{ formatDate(member.join_date) }}</td>
          <td>
            <router-link 
              :to="`/members/${member.id}/edit`" 
              class="btn btn-sm btn-edit"
            >
              编辑
            </router-link>
            <button 
              @click="deleteMember(member.id)" 
              class="btn btn-sm btn-delete"
            >
              删除
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    
    <div v-if="members.length === 0 && !loading" class="empty-message">
      暂无会员数据
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getMembers } from '../api/members';
import { deleteMember as apiDeleteMember } from '../api/members';
import { useMemberStore } from '../stores/member';

export default {
  name: 'MemberList',
  setup() {
    const members = ref([]);
    const loading = ref(true);
    const error = ref(null);

    const memberStore = useMemberStore();

    const fetchMembers = async () => {
      try {
        loading.value = true;
        
        // 优先从store中获取缓存数据
        if (memberStore.hasMembers) {
          members.value = memberStore.members;
        }
        
        // 仍然从API获取最新数据
        const data = await getMembers();
        members.value = data;
        memberStore.setMembers(data);
        error.value = null;
      } catch (err) {
        console.error('获取会员列表失败:', err);
        error.value = err;
      } finally {
        loading.value = false;
      }
    };

    const formatDate = (dateString) => {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString();
    };

    const deleteMember = async (id) => {
      if (confirm('确定要删除这个会员吗？')) {
        try {
          await apiDeleteMember(id);
          await fetchMembers();
        } catch (err) {
          console.error('删除会员失败:', err);
          error.value = err;
        }
      }
    };

    onMounted(() => {
      fetchMembers();
    });

    return {
      members,
      loading,
      error,
      formatDate,
      deleteMember
    };
  }
};
</script>

<style scoped>
.member-list-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 20px;
  color: #333;
}

.action-bar {
  margin-bottom: 20px;
}

.member-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

.member-table th, .member-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.member-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.member-table tr:hover {
  background-color: #f9f9f9;
}

.btn {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 4px;
  text-decoration: none;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background-color: #4CAF50;
  color: white;
  border: none;
}

.btn-primary:hover {
  background-color: #45a049;
}

.btn-sm {
  padding: 5px 10px;
  font-size: 13px;
}

.btn-edit {
  background-color: #2196F3;
  color: white;
  border: none;
}

.btn-edit:hover {
  background-color: #0b7dda;
}

.loading-indicator {
  padding: 20px;
  text-align: center;
  color: #666;
}

.error-message {
  padding: 20px;
  color: #f44336;
  background-color: #ffebee;
  border-radius: 4px;
  margin-bottom: 20px;
}

.empty-message {
  padding: 20px;
  text-align: center;
  color: #666;
  background-color: #f5f5f5;
  border-radius: 4px;
}
</style>