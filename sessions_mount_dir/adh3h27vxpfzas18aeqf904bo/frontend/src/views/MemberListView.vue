<template>
  <div class="member-list-view">
    <h1>会员列表</h1>
    
    <div class="action-bar">
      <el-button type="primary" @click="showAddDialog = true">添加会员</el-button>
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索会员" 
        style="width: 300px; margin-left: 20px;"
        clearable
        @clear="handleSearchClear"
        @keyup.enter="fetchMembers"
      >
        <template #append>
          <el-button icon="el-icon-search" @click="fetchMembers" />
        </template>
      </el-input>
    </div>
    
    <el-table :data="members" style="width: 100%" border>
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
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(scope.row.id)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="totalMembers"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="fetchMembers"
      @current-change="fetchMembers"
    />
    
    <!-- 添加/编辑会员对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="dialogTitle" 
      width="40%"
      @closed="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="会员卡状态" prop="card_status">
          <el-select v-model="form.card_status" placeholder="请选择状态">
            <el-option 
              v-for="status in cardStatusOptions" 
              :key="status.value" 
              :label="status.label" 
              :value="status.value" 
            />
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
import { getMembers, createMember, updateMember, deleteMember } from '../api/member'

export default {
  name: 'MemberListView',
  
  setup() {
    const members = ref([])
    const searchQuery = ref('')
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalMembers = ref(0)
    
    const showDialog = ref(false)
    const dialogTitle = ref('')
    const isEditMode = ref(false)
    const currentMemberId = ref(null)
    const formRef = ref(null)
    
    const form = ref({
      name: '',
      phone: '',
      email: '',
      card_status: ''
    })
    
    const rules = {
      name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
      phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur', 'change'] }
      ],
      card_status: [{ required: true, message: '请选择会员卡状态', trigger: 'change' }]
    }
    
    const cardStatusOptions = [
      { value: 'active', label: '激活' },
      { value: 'expired', label: '过期' },
      { value: 'suspended', label: '暂停' },
      { value: 'cancelled', label: '取消' }
    ]
    
    const fetchMembers = async () => {
      try {
        const params = {
          page: currentPage.value,
          size: pageSize.value,
          search: searchQuery.value
        }
        
        const response = await getMembers(params)
        members.value = response.data
        totalMembers.value = response.total
      } catch (error) {
        ElMessage.error('获取会员列表失败: ' + error.message)
      }
    }
    
    const handleSearchClear = () => {
      searchQuery.value = ''
      fetchMembers()
    }
    
    const handleEdit = (member) => {
      dialogTitle.value = '编辑会员'
      isEditMode.value = true
      currentMemberId.value = member.id
      form.value = { ...member }
      showDialog.value = true
    }
    
    const handleDelete = (id) => {
      ElMessageBox.confirm('确定要删除这个会员吗?', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await deleteMember(id)
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
        
        if (isEditMode.value) {
          await updateMember(currentMemberId.value, form.value)
          ElMessage.success('更新成功')
        } else {
          await createMember(form.value)
          ElMessage.success('添加成功')
        }
        
        showDialog.value = false
        fetchMembers()
      } catch (error) {
        if (error.name !== 'ValidationError') {
          ElMessage.error((isEditMode.value ? '更新' : '添加') + '失败: ' + error.message)
        }
      }
    }
    
    const resetForm = () => {
      formRef.value?.resetFields()
      isEditMode.value = false
      currentMemberId.value = null
      form.value = {
        name: '',
        phone: '',
        email: '',
        card_status: ''
      }
    }
    
    const getStatusTagType = (status) => {
      switch (status) {
        case 'active': return 'success'
        case 'expired': return 'warning'
        case 'suspended': return 'info'
        case 'cancelled': return 'danger'
        default: return ''
      }
    }
    
    onMounted(() => {
      fetchMembers()
    })
    
    return {
      members,
      searchQuery,
      currentPage,
      pageSize,
      totalMembers,
      showDialog,
      dialogTitle,
      form,
      rules,
      formRef,
      cardStatusOptions,
      fetchMembers,
      handleSearchClear,
      handleEdit,
      handleDelete,
      submitForm,
      resetForm,
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
  justify-content: flex-end;
}
</style>