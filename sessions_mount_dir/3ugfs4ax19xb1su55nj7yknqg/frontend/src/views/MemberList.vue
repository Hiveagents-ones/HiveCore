<template>
  <div class="member-list">
    <h1>会员列表</h1>
    <div class="actions">
      <router-link to="/members/new" class="btn btn-primary">
        新增会员
      </router-link>
    </div>
    
    <div v-if="loading" class="loading">加载中...</div>
    
    <table v-else class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>姓名</th>
          <th>电话</th>
          <th>邮箱</th>
          <th>会员类型</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in members" :key="member.id">
          <td>{{ member.id }}</td>
          <td>{{ member.name }}</td>
          <td>{{ member.phone }}</td>
          <td>{{ member.email }}</td>
          <td>{{ member.membership_type }}</td>
          <td>
            <router-link 
              :to="`/members/${member.id}`" 
              class="btn btn-sm btn-info"
            >
              查看
            </router-link>
            <router-link 
              :to="`/members/${member.id}/edit`" 
              class="btn btn-sm btn-warning"
            >
              编辑
            </router-link>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getMembers } from '../api/members';

export default {
  name: 'MemberList',
  setup() {
    const members = ref([]);
    const loading = ref(true);
    const error = ref(null);

    const fetchMembers = async () => {
      try {
        loading.value = true;
        const response = await getMembers();
        members.value = response.data;
      } catch (err) {
        error.value = err.message || '获取会员列表失败';
        console.error('Error fetching members:', err);
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      fetchMembers();
    });

    return {
      members,
      loading,
      error
    };
  }
};
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.actions {
  margin-bottom: 20px;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th, .table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.table th {
  background-color: #f8f9fa;
  font-weight: bold;
}

.btn {
  padding: 6px 12px;
  margin-right: 5px;
  border-radius: 4px;
  text-decoration: none;
  cursor: pointer;
}

.btn-primary {
  background-color: #007bff;
  color: white;
  border: 1px solid #007bff;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
  border: 1px solid #17a2b8;
}

.btn-warning {
  background-color: #ffc107;
  color: #212529;
  border: 1px solid #ffc107;
}

.loading {
  padding: 20px;
  text-align: center;
  color: #666;
}
</style>