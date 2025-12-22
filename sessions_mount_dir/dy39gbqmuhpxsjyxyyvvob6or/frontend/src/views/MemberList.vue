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
    
    <el-table :data="filteredMembers" style="width: 100%; margin-top: 20px" border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="phone" label="电话" />
      <el-table-column prop="join_date" label="加入日期" />
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
          <el-input v-model="newMember.name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="newMember.email" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="newMember.phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addMember">确认</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showEditDialog" title="编辑会员" width="30%">
      <el-form :model="currentMember" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="currentMember.name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="currentMember.email" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="currentMember.phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateMember">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getMembers,
  createMember,
  updateMember as apiUpdateMember,
  deleteMember
} from '@/api/members'

const members = ref([])
const searchQuery = ref('')
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const authStore = useAuthStore()
const newMember = ref({
  name: '',
  email: '',
  phone: ''
})
const currentMember = ref({
  id: null,
  name: '',
  email: '',
  phone: ''
})

const filteredMembers = computed(() => {
  return members.value.filter(member => {
    return (
      member.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      member.email.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      member.phone.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  })
})

const fetchMembers = async () => {
  try {
    if (!authStore.token) {
      await authStore.refreshToken()
    }
    const data = await getMembers()
    members.value = data
  } catch (error) {
    ElMessage.error('获取会员列表失败')
    console.error(error)
  }
}

const addMember = async () => {
  try {
    if (!authStore.token) {
      await authStore.refreshToken()
    }
    await createMember(newMember.value)
    ElMessage.success('会员添加成功')
    showAddDialog.value = false
    newMember.value = { name: '', email: '', phone: '' }
    fetchMembers()
  } catch (error) {
    ElMessage.error('添加会员失败')
    console.error(error)
  }
}

const handleEdit = (member) => {
  currentMember.value = { ...member }
  showEditDialog.value = true
}

const updateMember = async () => {
  try {
    if (!authStore.token) {
      await authStore.refreshToken()
    }
    await apiUpdateMember(currentMember.value.id, currentMember.value)
    ElMessage.success('会员信息更新成功')
    showEditDialog.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error('更新会员信息失败')
    console.error(error)
  }
}

const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除该会员吗?', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      if (!authStore.token) {
        await authStore.refreshToken()
      }
      await deleteMember(id)
      ElMessage.success('会员删除成功')
      fetchMembers()
    } catch (error) {
      ElMessage.error('删除会员失败')
      console.error(error)
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

const handleSearch = () => {
  // 搜索功能由computed属性filteredMembers自动处理
}

onMounted(() => {
  fetchMembers()
})
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.actions {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}
</style>