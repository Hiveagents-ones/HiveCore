<template>
  <div class="member-list">
    <h1>会员列表</h1>
    <div class="search-bar">
      <input v-model="searchQuery" type="text" placeholder="搜索会员..." />
      <button @click="fetchMembers">搜索</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>会员ID</th>
          <th>姓名</th>
          <th>联系方式</th>
          <th>会员类型</th>
          <th>有效期</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in members" :key="member.id">
          <td>{{ member.id }}</td>
          <td>{{ member.name }}</td>
          <td>{{ member.contact }}</td>
          <td>{{ member.member_type }}</td>
          <td>{{ member.valid_until }}</td>
          <td>
            <button @click="editMember(member.id)">编辑</button>
            <button @click="deleteMember(member.id)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getMembers, deleteMember as apiDeleteMember } from '@/api/members';

const router = useRouter();
const members = ref([]);
const searchQuery = ref('');

const fetchMembers = async () => {
  const response = await getMembers({ search: searchQuery.value });
  members.value = response.data;
};

const editMember = (id) => {
  router.push({ name: 'MemberEdit', params: { id } });
};

const deleteMember = async (id) => {
  if (confirm('确定要删除该会员吗？')) {
    await apiDeleteMember(id);
    fetchMembers();
  }
};

onMounted(() => {
  fetchMembers();
});
</script>

<style scoped>
.member-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.search-bar {
  margin-bottom: 20px;
}

.search-bar input {
  padding: 10px;
  width: 70%;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.search-bar button {
  padding: 10px 20px;
  background-color: #007bff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.search-bar button:hover {
  background-color: #0056b3;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.table th {
  background-color: #f2f2f2;
}

.table button {
  margin: 0 5px;
  padding: 5px 10px;
  background-color: #007bff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.table button:hover {
  background-color: #0056b3;
}
</style>