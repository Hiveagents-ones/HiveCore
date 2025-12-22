<template>
  <div class="member-list">
    <h1>会员列表</h1>
    
    <div class="search-bar">
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索会员" 
        style="width: 300px; margin-right: 10px;"
        @keyup.enter="fetchMembers"
      >
        <template #append>
          <el-button icon="el-icon-search" @click="fetchMembers" />
        </template>
      </el-input>
      
      <el-button type="primary" @click="showAddDialog = true">
        添加会员
      </el-button>
    </div>
    
    <el-table 
  :data="members" 
  border 
  style="width: 100%; margin-top: 20px;"
  v-loading="loading"
  element-loading-text="加载中..."
  element-loading-background="rgba(0, 0, 0, 0.1)"
>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="phone" label="电话" width="150">
  <template #default="{row}">
    {{ row.phone ? `${row.phone.substring(0, 3)}****${row.phone.substring(7)}` : '' }}
  </template>
</el-table-column>
      <el-table-column prop="email" label="邮箱" width="200">
  <template #default="{row}">
    {{ row.email ? row.email.replace(/(.{2}).*@/, '$1****@') : '' }}
  </template>
</el-table-column>
      <el-table-column prop="join_date" label="加入日期" width="150" />
      
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(scope.row.id)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      v-model:currentPage="currentPage"
      v-model:page-size="pageSize"
      :total="totalMembers"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="fetchMembers"
      @size-change="fetchMembers"
      style="margin-top: 20px;"
    />
    
    <!-- 添加/编辑会员对话框 -->
    <el-dialog 
      v-model="showAddDialog" 
      :title="isEditing ? '编辑会员' : '添加会员'" 
      width="30%"
    >
      <el-form :model="memberForm" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="memberForm.name" />
        </el-form-item>
        <el-form-item label="电话" required>
          <el-input v-model="memberForm.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="memberForm.email" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitMemberForm">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, watch, onUnmounted } from 'vue';
import { debounce } from 'lodash-es';
import { ElMessage, ElMessageBox } from 'element-plus';
import memberApi from '../api/member';

export default {
  name: 'MemberList',
  
  setup() {
    const members = ref([]);
    const searchQuery = ref('');
  const debouncedSearch = debounce(() => fetchMembers(), 500);
  watch(searchQuery, (newVal) => {
    if (newVal.trim() === '') {
      fetchMembers();
    } else {
      debouncedSearch();
    }
  });
    const currentPage = ref(1);
    const pageSize = ref(10);
  watch([currentPage, pageSize], () => {
    fetchMembers();
  });
    const totalMembers = ref(0);
    const showAddDialog = ref(false);
    const isEditing = ref(false);
    const currentMemberId = ref(null);
    
    const loading = ref(false);
    const memberForm = ref({
      name: '',
      phone: '',
      email: ''
    });
    
    // 取消请求的token
    const cancelToken = ref(null);
    const fetchMembers = debounce(async () => {
  loading.value = true;
      try {
        const response = await axios.get('/api/v1/members', {
          params: {
            page: currentPage.value,
            size: pageSize.value,
            search: searchQuery.value
          }
        });
        
        members.value = response.data.items;
        totalMembers.value = response.data.total;
      } catch (error) {
        ElMessage.error('获取会员列表失败');
        console.error(error);
      } finally {
        loading.value = false;
      }
    };
    
    const handleEdit = (member) => {
      isEditing.value = true;
      currentMemberId.value = member.id;
      memberForm.value = {
        name: member.name,
        phone: member.phone,
        email: member.email
      };
      showAddDialog.value = true;
    };
    
    const handleDelete = (id) => {
      ElMessageBox.confirm('确定要删除该会员吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await memberApi.deleteMember(id);
          ElMessage.success('删除成功');
          fetchMembers();
        } catch (error) {
          ElMessage.error('删除失败');
          console.error(error);
        }
      }).catch(() => {});
    };
    
    const submitMemberForm = async () => {
      try {
        if (isEditing.value) {
          await memberApi.updateMember(currentMemberId.value, memberForm.value);
          ElMessage.success('更新成功');
        } else {
          await memberApi.createMember(memberForm.value);
          ElMessage.success('添加成功');
        }
        
        showAddDialog.value = false;
        fetchMembers();
        resetForm();
      } catch (error) {
        ElMessage.error(isEditing.value ? '更新失败' : '添加失败');
        console.error(error);
      }
    };
    
    const resetForm = () => {

    };

    // 组件卸载时取消所有pending请求
    onUnmounted(() => {
      if (cancelToken.value) {
        cancelToken.value.cancel('组件卸载取消请求');
      }
    });
      memberForm.value = {
        name: '',
        phone: '',
        email: ''
      };
      isEditing.value = false;
      currentMemberId.value = null;
    };
    
    onMounted(() => {
      fetchMembers();
    });
    
    return {
      loading,
      members,
      searchQuery,
      currentPage,
      pageSize,
      totalMembers,
      showAddDialog,
      isEditing,
      memberForm,
      fetchMembers,
      handleEdit,
      handleDelete,
      submitMemberForm
    };
  }
};
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.search-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const fetchMembers = debounce(async () => {
  if (loading.value) return;
  
  loading.value = true;
  try {
    const { data } = await memberApi.getMembers({
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value.trim()
    });

    // 使用Object.freeze防止Vue对大数据进行响应式处理
    members.value = Object.freeze(data.items);
    totalMembers.value = data.total;
  } catch (error) {
    if (!axios.isCancel(error)) {
      ElMessage.error('获取会员列表失败');
      console.error(error);
    }
  } finally {
    loading.value = false;
  }
}, 300);

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const fetchMembers = debounce(async () => {
  if (loading.value) return;

  loading.value = true;
  try {
    const { data } = await memberApi.getMembers({
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value.trim()
    });

    // 使用Object.freeze防止Vue对大数据进行响应式处理
    members.value = Object.freeze(data.items);
    totalMembers.value = data.total;
  } catch (error) {
    if (!axios.isCancel(error)) {
      ElMessage.error('获取会员列表失败');
      console.error(error);
    }
  } finally {
    loading.value = false;
  }
}, 300);