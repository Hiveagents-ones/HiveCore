<template>
  <div class="member-list-view">
    <h1>会员列表</h1>
    <div class="actions">
      <button @click="showAddDialog = true" class="add-button">添加会员</button>
    </div>
    
    <table class="member-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>姓名</th>
          <th>联系方式</th>
          <th>会员等级</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in members" :key="member.id">
          <td>{{ member.id }}</td>
          <td>{{ member.name }}</td>
          <td>{{ member.contact }}</td>
          <td>{{ member.level }}</td>
          <td>
            <button @click="editMember(member)" class="edit-button">编辑</button>
            <button @click="deleteMember(member.id)" class="delete-button">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 添加/编辑对话框 -->
    <div v-if="showAddDialog || showEditDialog" class="dialog-overlay">
      <div class="dialog">
        <h2>{{ isEditing ? '编辑会员' : '添加会员' }}</h2>
        <form @submit.prevent="isEditing ? updateMember() : addMember()">
          <div class="form-group">
            <label>姓名:</label>
            <input v-model="currentMember.name" required>
          </div>
          <div class="form-group">
            <label>联系方式:</label>
            <input v-model="currentMember.contact" required>
          </div>
          <div class="form-group">
            <label>会员等级:</label>
            <select v-model="currentMember.level" required>
              <option value="普通">普通</option>
              <option value="银卡">银卡</option>
              <option value="金卡">金卡</option>
              <option value="钻石">钻石</option>
            </select>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeDialog" class="cancel-button">取消</button>
            <button type="submit" class="confirm-button">确认</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const API_URL = '/api/v1/members';

export default {
  setup() {
    const members = ref([]);
    const showAddDialog = ref(false);
    const showEditDialog = ref(false);
    const isEditing = ref(false);
    const currentMember = ref({
      id: null,
      name: '',
      contact: '',
      level: '普通'
    });

    const fetchMembers = async () => {
      try {
        const response = await axios.get(API_URL);
        members.value = response.data;
      } catch (error) {
        console.error('获取会员列表失败:', error);
      }
    };

    const addMember = async () => {
      try {
        await axios.post(API_URL, currentMember.value);
        await fetchMembers();
        closeDialog();
      } catch (error) {
        console.error('添加会员失败:', error);
      }
    };

    const editMember = (member) => {
      currentMember.value = { ...member };
      isEditing.value = true;
      showEditDialog.value = true;
    };

    const updateMember = async () => {
      try {
        await axios.put(`${API_URL}/${currentMember.value.id}`, currentMember.value);
        await fetchMembers();
        closeDialog();
      } catch (error) {
        console.error('更新会员失败:', error);
      }
    };

    const deleteMember = async (id) => {
      if (confirm('确定要删除这个会员吗?')) {
        try {
          await axios.delete(`${API_URL}/${id}`);
          await fetchMembers();
        } catch (error) {
          console.error('删除会员失败:', error);
        }
      }
    };

    const closeDialog = () => {
      showAddDialog.value = false;
      showEditDialog.value = false;
      isEditing.value = false;
      currentMember.value = {
        id: null,
        name: '',
        contact: '',
        level: '普通'
      };
    };

    onMounted(() => {
      fetchMembers();
    });

    return {
      members,
      showAddDialog,
      showEditDialog,
      isEditing,
      currentMember,
      addMember,
      editMember,
      updateMember,
      deleteMember,
      closeDialog
    };
  }
};
</script>

<style scoped>
.member-list-view {
  padding: 20px;
}

.actions {
  margin-bottom: 20px;
}

.add-button {
  background-color: #4CAF50;
  color: white;
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.member-table {
  width: 100%;
  border-collapse: collapse;
}

.member-table th, .member-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.member-table th {
  background-color: #f2f2f2;
}

.edit-button {
  background-color: #2196F3;
  color: white;
  padding: 5px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 5px;
}

.delete-button {
  background-color: #f44336;
  color: white;
  padding: 5px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.dialog {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  width: 400px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.cancel-button {
  background-color: #f44336;
  color: white;
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
}

.confirm-button {
  background-color: #4CAF50;
  color: white;
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>