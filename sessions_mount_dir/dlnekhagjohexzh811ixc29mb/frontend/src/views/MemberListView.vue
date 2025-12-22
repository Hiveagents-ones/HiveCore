<template>
  <div class="member-list-view">
    <h1>会员列表</h1>
    
    <div class="action-bar">
      <el-select v-model="statusFilter" placeholder="会员状态" style="width: 120px; margin-left: 20px" clearable @change="fetchMembers">
        <el-option label="全部" value="" />
        <el-option label="活跃" value="active" />
        <el-option label="暂停" value="paused" />
        <el-option label="过期" value="expired" />
      </el-select>
      <el-button type="primary" @click="showAddDialog = true">添加会员</el-button>
      <el-input
        v-model="searchQuery"
        placeholder="搜索会员"
        style="width: 300px; margin-left: 20px"
        clearable
        @clear="handleSearchClear"
        @keyup.enter="fetchMembers"
      >
        <template #append>
          <el-button icon="el-icon-search" @click="fetchMembers" />
        </template>
      </el-input>
    </div>
    
    <el-table :data="members" style="width: 100%" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="phone" label="电话" />
      <el-table-column prop="membership_status" label="会员状态">
        <template #default="scope">
          <el-tag :type="getStatusTagType(scope.row.membership_status)">
            {{ scope.row.membership_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
      :current-page="currentPage"
      :page-sizes="[10, 20, 50, 100]"
      :page-size="pageSize"
      layout="total, sizes, prev, pager, next, jumper"
      :total="total"
    />
    
    <!-- 添加/编辑会员对话框 -->
    <el-dialog :title="dialogTitle" v-model="showDialog" width="50%">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="会员状态" prop="membership_status">
          <el-select v-model="form.membership_status" placeholder="请选择会员状态">
            <el-option label="活跃" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="过期" value="expired" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDialog = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMembers, createMember, updateMember, deleteMember } from '../api/members'

export default {
  name: 'MemberListView',
  setup() {
    const members = ref([])
    const loading = ref(false)
    const searchQuery = ref('')
    const statusFilter = ref('')
    const currentPage = ref(1)
    const pageSize = ref(10)
    const total = ref(0)
    
    const showDialog = ref(false)
    const showAddDialog = ref(false)
    const dialogTitle = ref('')
    const formRef = ref(null)
    const currentMemberId = ref(null)
    
    const form = ref({
      name: '',
      email: '',
      phone: '',
      membership_status: 'active'
    })
    
    const rules = {
      name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur', 'change'] }
      ],
      phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
      membership_status: [{ required: true, message: '请选择会员状态', trigger: 'change' }]
    }
    
    const fetchMembers = async () => {
      loading.value = true
      try {
        const params = {
          page: currentPage.value,
          size: pageSize.value,
          search: searchQuery.value,
          status: statusFilter.value
        }
        const response = await getMembers(params)
        members.value = response.data.items
        total.value = response.data.total
      } catch (error) {
        ElMessage.error('获取会员列表失败: ' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    const handleSizeChange = (val) => {
      pageSize.value = val
      fetchMembers()
    }
    
    const handleCurrentChange = (val) => {
      currentPage.value = val
      fetchMembers()
    }
    
    const handleSearchClear = () => {
      statusFilter.value = ''
      searchQuery.value = ''
      fetchMembers()
    }
    
    const resetForm = () => {
      form.value = {
        name: '',
        email: '',
        phone: '',
        membership_status: 'active'
      }
      currentMemberId.value = null
    }
    
    const handleAdd = () => {
      resetForm()
      dialogTitle.value = '添加会员'
      showDialog.value = true
    }
    
    const handleEdit = (row) => {
      form.value = { ...row }
      currentMemberId.value = row.id
      dialogTitle.value = '编辑会员'
      showDialog.value = true
    }
    
    const handleDelete = (row) => {
      ElMessageBox.confirm('确定要删除该会员吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await deleteMember(row.id)
          ElMessage.success('删除成功')
          fetchMembers()
        } catch (error) {
          ElMessage.error('删除失败: ' + error.message)
        }
      }).catch(() => {})
    }
    
    const submitForm = async () => {
      try {
        await formRef.value.validate()
        
        if (currentMemberId.value) {
          await updateMember(currentMemberId.value, form.value)
          ElMessage.success('更新成功')
        } else {
          await createMember(form.value)
          ElMessage.success('添加成功')
        }
        
        showDialog.value = false
        fetchMembers()
      } catch (error) {
        if (!error.message.includes('validate')) {
          ElMessage.error('操作失败: ' + error.message)
        }
      }
    }
    
    const getStatusTagType = (status) => {
      switch (status) {
        case 'active': return 'success'
        case 'paused': return 'warning'
        case 'expired': return 'danger'
        default: return ''
      }
    }
    
    onMounted(() => {
      fetchMembers()
    })
    
    return {
      members,
      loading,
      searchQuery,
      statusFilter,
      currentPage,
      pageSize,
      total,
      showDialog,
      showAddDialog,
      dialogTitle,
      form,
      formRef,
      rules,
      handleSizeChange,
      handleCurrentChange,
      handleSearchClear,
      handleAdd,
      handleEdit,
      handleDelete,
      submitForm,
      getStatusTagType
    }
  }
}
</script>

<style scoped>
.member-list-view {
  padding: 20px;
}

.action-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.el-pagination {
  margin-top: 20px;
  text-align: right;
}
</style>