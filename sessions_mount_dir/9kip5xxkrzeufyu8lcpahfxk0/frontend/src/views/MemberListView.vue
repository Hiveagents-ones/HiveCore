<template>
  <div class="member-list">
    <h1>会员列表</h1>
    
    <div class="actions">
      <el-button type="primary" @click="showAddDialog = true">添加会员</el-button>
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索会员" 
        style="width: 300px; margin-left: 20px"
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><search /></el-icon>
        </template>
      </el-input>
    </div>
    
    <el-table :data="filteredMembers" border style="width: 100%; margin-top: 20px">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="phone" label="电话" width="150" />
      <el-table-column prop="email" label="邮箱" width="200" />
      <el-table-column prop="join_date" label="加入日期" width="150" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-dialog v-model="showAddDialog" title="添加会员" width="30%">
      <el-form :model="newMember" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="newMember.name" autocomplete="off" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="newMember.phone" autocomplete="off" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="newMember.email" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="handleAdd">确认</el-button>
        </span>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showEditDialog" title="编辑会员" width="30%">
      <el-form :model="currentMember" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="currentMember.name" autocomplete="off" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="currentMember.phone" autocomplete="off" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="currentMember.email" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" @click="handleUpdate">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { Search } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getMembers, addMember, updateMember, deleteMember } from '../api/members';

const members = ref([]);
const searchQuery = ref('');
const showAddDialog = ref(false);
const showEditDialog = ref(false);
const currentMember = ref({ id: null, name: '', phone: '', email: '' });
const newMember = ref({ name: '', phone: '', email: '' });

const filteredMembers = computed(() => {
  return members.value.filter(member => {
    return (
      member.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      member.phone.includes(searchQuery.value) ||
      member.email.toLowerCase().includes(searchQuery.value.toLowerCase())
    );
  });
});

const fetchMembers = async () => {
  try {
    const response = await getMembers();
    members.value = response.data;
  } catch (error) {
    ElMessage.error('获取会员列表失败');
  }
};

const handleSearch = () => {
  // 搜索逻辑已通过计算属性实现
};

const handleAdd = async () => {
  try {
    await addMember(newMember.value);
    ElMessage.success('添加会员成功');
    showAddDialog.value = false;
    newMember.value = { name: '', phone: '', email: '' };
    await fetchMembers();
  } catch (error) {
    ElMessage.error('添加会员失败');
  }
};

const handleEdit = (member) => {
  currentMember.value = { ...member };
  showEditDialog.value = true;
};

const handleUpdate = async () => {
  try {
    await updateMember(currentMember.value.id, currentMember.value);
    ElMessage.success('更新会员成功');
    showEditDialog.value = false;
    await fetchMembers();
  } catch (error) {
    ElMessage.error('更新会员失败');
  }
};

const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除该会员吗?', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await deleteMember(id);
      ElMessage.success('删除会员成功');
      await fetchMembers();
    } catch (error) {
      ElMessage.error('删除会员失败');
    }
  }).catch(() => {
    // 用户取消删除
  });
};

onMounted(() => {
  fetchMembers();
});
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.actions {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
</style>