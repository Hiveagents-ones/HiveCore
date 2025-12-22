<template>
  <div class="role-management">
    <div class="page-header">
      <h1>角色管理</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <i class="el-icon-plus"></i> 新建角色
      </el-button>
    </div>

    <el-table :data="roles" v-loading="loading" border>
      <el-table-column prop="name" label="角色名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="权限数量">
        <template #default="{ row }">
          {{ row.permissions?.length || 0 }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="editRole(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteRole(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Role Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingRole ? '编辑角色' : '新建角色'"
      width="50%"
    >
      <el-form :model="roleForm" :rules="roleRules" ref="roleFormRef" label-width="100px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="roleForm.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="roleForm.description"
            type="textarea"
            placeholder="请输入角色描述"
          />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="roleForm.permission_ids">
            <div class="permission-group" v-for="group in groupedPermissions" :key="group.resource">
              <h4>{{ getResourceName(group.resource) }}</h4>
              <el-checkbox
                v-for="permission in group.permissions"
                :key="permission.id"
                :label="permission.id"
              >
                {{ getActionName(permission.action) }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRole" :loading="saving">
          {{ editingRole ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();

const loading = ref(false);
const saving = ref(false);
const showCreateDialog = ref(false);
const editingRole = ref(null);
const roleFormRef = ref(null);
const permissions = ref([]);

const roleForm = ref({
  name: '',
  description: '',
  permission_ids: [],
});

const roleRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
};

const roles = computed(() => authStore.roles);

const groupedPermissions = computed(() => {
  const groups = {};
  permissions.value.forEach(permission => {
    if (!groups[permission.resource]) {
      groups[permission.resource] = {
        resource: permission.resource,
        permissions: [],
      };
    }
    groups[permission.resource].permissions.push(permission);
  });
  return Object.values(groups);
});

const getResourceName = (resource) => {
  const names = {
    members: '会员管理',
    courses: '课程管理',
    payments: '支付管理',
    reports: '报表管理',
    auth: '权限管理',
  };
  return names[resource] || resource;
};

const getActionName = (action) => {
  const names = {
    read: '查看',
    create: '创建',
    update: '更新',
    delete: '删除',
    all_read: '查看全部',
    all_update: '更新全部',
    all_delete: '删除全部',
  };
  return names[action] || action;
};

const formatDate = (date) => {
  return new Date(date).toLocaleString('zh-CN');
};

const fetchRoles = async () => {
  loading.value = true;
  try {
    await authStore.fetchRoles();
    await fetchPermissions();
  } catch (error) {
    ElMessage.error('获取角色列表失败');
  } finally {
    loading.value = false;
  }
};

const fetchPermissions = async () => {
  try {
    permissions.value = await authStore.fetchPermissions();
  } catch (error) {
    ElMessage.error('获取权限列表失败');
  }
};

const editRole = (role) => {
  editingRole.value = role;
  roleForm.value = {
    name: role.name,
    description: role.description || '',
    permission_ids: role.permissions?.map(p => p.id) || [],
  };
  showCreateDialog.value = true;
};

const saveRole = async () => {
  if (!roleFormRef.value) return;
  
  try {
    await roleFormRef.value.validate();
  } catch {
    return;
  }

  saving.value = true;
  try {
    if (editingRole.value) {
      await authStore.updateRole(editingRole.value.id, roleForm.value);
      ElMessage.success('角色更新成功');
    } else {
      await authStore.createRole(roleForm.value);
      ElMessage.success('角色创建成功');
    }
    showCreateDialog.value = false;
    resetForm();
    fetchRoles();
  } catch (error) {
    ElMessage.error(error.message || '操作失败');
  } finally {
    saving.value = false;
  }
};

const deleteRole = async (roleId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个角色吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    
    await authStore.deleteRole(roleId);
    ElMessage.success('角色删除成功');
    fetchRoles();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
};

const resetForm = () => {
  editingRole.value = null;
  roleForm.value = {
    name: '',
    description: '',
    permission_ids: [],
  };
  if (roleFormRef.value) {
    roleFormRef.value.resetFields();
  }
};

onMounted(() => {
  fetchRoles();
});
</script>

<style scoped>
.role-management {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.permission-group {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.permission-group h4 {
  margin: 0 0 10px 0;
  color: #606266;
}

.permission-group .el-checkbox {
  margin-right: 15px;
  margin-bottom: 5px;
}
</style>