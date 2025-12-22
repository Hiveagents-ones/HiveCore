<template>
  <div class="member-list-view">
    <h1>会员列表</h1>
    <el-alert
      title="会员管理"
      type="info"
      description="您可以在此查看、添加、编辑和删除会员信息"
      show-icon
      style="margin-bottom: 20px"
    />
    
    <div class="action-bar">
      <el-button type="primary" @click="showCreateDialog = true">新增会员</el-button>
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索会员" 
        style="width: 300px; margin-left: 20px"
        @input="handleSearch"
      >
        <template #append>
          <el-button icon="el-icon-search" />
        </template>
      </el-input>
    </div>
    
    <el-table 
      :data="filteredMembers" 
      style="width: 100%" 
      border
      stripe
      highlight-current-row
      @row-click="handleRowClick"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="phone" label="电话" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="card_status" label="会员卡状态">
        <template #default="scope">
          <el-tag :type="getStatusTagType(scope.row.card_status)">

            {{ scope.row.card_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-dialog v-model="showCreateDialog" title="新增会员" width="30%">
      <el-form :model="newMember" label-width="100px">
        <el-form-item label="姓名" required>
          <el-input v-model="newMember.name" />
        </el-form-item>
        <el-form-item label="电话" required>
          <el-input v-model="newMember.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="newMember.email" />
        </el-form-item>
        <el-form-item label="会员卡状态">
          <el-select v-model="newMember.card_status" placeholder="请选择">
            <el-option label="有效" value="active" />
            <el-option label="过期" value="expired" />
            <el-option label="冻结" value="frozen" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createMember">确认</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="showEditDialog" title="编辑会员" width="30%">
      <el-form :model="currentMember" label-width="100px">
        <el-form-item label="姓名" required>
          <el-input v-model="currentMember.name" />
        </el-form-item>
        <el-form-item label="电话" required>
          <el-input v-model="currentMember.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="currentMember.email" />
        </el-form-item>
        <el-form-item label="会员卡状态">
          <el-select v-model="currentMember.card_status" placeholder="请选择">
            <el-option label="有效" value="active" />
            <el-option label="过期" value="expired" />
            <el-option label="冻结" value="frozen" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateMember">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMembers, createMember, updateMember, deleteMember } from '../api/members'

export default {
  setup() {
    const members = ref([])
    const searchQuery = ref('')
    const showCreateDialog = ref(false)
    const showEditDialog = ref(false)
    const currentMember = ref({})
    
    const newMember = ref({
      name: '',
      phone: '',
      email: '',
      card_status: 'active'
    })
    
    const filteredMembers = computed(() => {
      if (!searchQuery.value) return members.value
      return members.value.filter(member => 
        member.name.includes(searchQuery.value) || 
        member.phone.includes(searchQuery.value) ||
        member.email.includes(searchQuery.value)
      )
    })
    
    const fetchMembers = async () => {
      try {
        const response = await getMembers()
        members.value = response.data
      } catch (error) {
        ElMessage.error('获取会员列表失败')
      }
    }
    
    const handleEdit = (member) => {
      currentMember.value = { ...member }
      showEditDialog.value = true
    }
    
    const handleDelete = (id) => {
      ElMessageBox.confirm('确定要删除该会员吗?', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await deleteMember(id)
          ElMessage.success('删除成功')
          fetchMembers()
        } catch (error) {
          ElMessage.error('删除失败')
        }
      }).catch(() => {})
    }
    
    const createMemberHandler = async () => {
      try {
        await createMember(newMember.value)
        ElMessage.success('创建成功')
        showCreateDialog.value = false
        newMember.value = { name: '', phone: '', email: '', card_status: 'active' }
        fetchMembers()
      } catch (error) {
        ElMessage.error('创建失败')
      }
    }
    
    const updateMemberHandler = async () => {
      try {
        await updateMember(currentMember.value.id, currentMember.value)
        ElMessage.success('更新成功')
        showEditDialog.value = false
        fetchMembers()
      } catch (error) {
        ElMessage.error('更新失败')
      }
    }
    
    const handleSearch = () => {
      // 搜索逻辑已经在computed属性中处理
    }
    
    const handleRowClick = (row) => {
      // 可以在这里添加行点击事件处理
      console.log('点击行:', row)
    }

    const getStatusTagType = (status) => {
      switch (status) {
        case 'active': return 'success'
        case 'expired': return 'warning'
        case 'frozen': return 'danger'
        default: return 'info'
      }
    }
    
    onMounted(() => {
      fetchMembers()
    })
    
    return {
      members,
      searchQuery,
      filteredMembers,
      showCreateDialog,
      showEditDialog,
      newMember,
      currentMember,
      handleEdit,
      handleDelete,
      createMember: createMemberHandler,
      updateMember: updateMemberHandler,
      handleSearch,
      getStatusTagType
    }
  }
}
</script>

<style scoped>
.member-list-view {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.action-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}
</style>