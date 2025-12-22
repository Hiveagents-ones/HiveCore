<template>
  <div class="permission-matrix">
    <div class="page-header">
      <h1>权限矩阵配置</h1>
      <div class="header-actions">
        <el-button @click="refreshData">
          <i class="el-icon-refresh"></i> 刷新
        </el-button>
        <el-button type="primary" @click="showCreatePermissionDialog = true">
          <i class="el-icon-plus"></i> 新建权限
        </el-button>
      </div>
    </div>

    <!-- Permission Matrix Table -->
    <div class="matrix-container">
      <el-table :data="matrixData" border v-loading="loading">
        <el-table-column label="资源/角色" fixed="left" width="150">
          <template #default="{ row }">
            <strong>{{ getResourceName(row.resource) }}</strong>
          </template>
        </el-table-column>
        
        <el-table-column
          v-for="role in roles"
          :key="role.id"
          :label="role.name"
          width="120"
        >
          <template #default="{ row }">
            <div class="permission-cell">
              <el-tag
                v-for="permission in row.roles[role.id]"
                :key="permission.id"
                size="small"
                :type="getPermissionTagType(permission.action)"
                class="permission-tag"
                @click="editPermission(permission)"
              >
                {{ getActionName(permission.action) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create Permission Dialog -->
    <el-dialog
      v-model="showCreatePermissionDialog"
      title="新建权限"
      width="40%"
    >
      <el-form :model="permissionForm" :rules="permissionRules" ref="permissionFormRef" label-width="100px">
        <el-form-item label="权限名称" prop="name">
          <el-input v-model="permissionForm.name" placeholder="请输入权限名称" />
        </el-form-item>
        <el-form-item label="资源" prop="resource">
          <el-select v-model="permissionForm.resource" placeholder="请选择资源">
            <el-option
              v-for="resource in resources"
              :key="resource.value"
              :label="resource.label"
              :value="resource.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="操作" prop="action">
          <el-select v-model="permissionForm.action" placeholder="请选择操作">
            <el-option
              v-for="action in actions"
              :key="action.value"
              :label="action.label"
              :value="action.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="permissionForm.description"
            type="textarea"
            placeholder="请输入权限描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreatePermissionDialog = false">取消</el-button>
        <el-button type="primary" @click="createPermission" :loading="saving">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- Permission Details Dialog -->
    <el-dialog
      v-model="showPermissionDetailsDialog"
      title="权限详情"
      width="40%"
    >
      <el-descriptions v-if="selectedPermission" :column="1" border>
        <el-descriptions-item label="权限名称">{{ selectedPermission.name }}</el-descriptions-item>
        <el-descriptions-item label="资源">{{ getResourceName(selectedPermission.resource) }}</el-descriptions-item>
        <el-descriptions-item label="操作">{{ getActionName(selectedPermission.action) }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ selectedPermission.description || '无' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showPermissionDetailsDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { authAPI } from '../api/auth';

const loading = ref(false);
const saving = ref(false);
const showCreatePermissionDialog = ref(false);
const showPermissionDetailsDialog = ref(false);
const permissionFormRef = ref(null);

const roles = ref([]);
const permissions = ref([]);
const selectedPermission = ref(null);

const permissionForm = ref({
  name: '',
  resource: '',
  action: '',
  description: '',
});

const permissionRules = {
  name: [{ required: true, message: '请输入权限名称', trigger: 'blur' }],
  resource: [{ required: true, message: '请选择资源', trigger: 'change' }],
  action: [{ required: true, message: '请选择操作', trigger: 'change' }],
};

const resources = [
  { label: '会员管理', value: 'members' },
  { label: '课程管理', value: 'courses' },
  { label: '支付管理', value: 'payments' },
  { label: '报表管理', value: 'reports' },
  { label: '权限管理', value: 'auth' },
];

const actions = [
  { label: '查看', value: 'read' },
  { label: '查看全部', value: 'all_read' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '更新全部', value: 'all_update' },
  { label: '删除', value: 'delete' },
  { label: '删除全部', value: 'all_delete' },
];

const matrixData = computed(() => {
  const resourceMap = {};
  
  // Initialize resource groups
  resources.forEach(resource => {
    resourceMap[resource.value] = {
      resource: resource.value,
      roles: {},
    };
    
    // Initialize role columns
    roles.value.forEach(role => {
      resourceMap[resource.value].roles[role.id] = [];
    });
  });
  
  // Fill with permissions
  permissions.value.forEach(permission => {
    if (resourceMap[permission.resource]) {
      permission.roles?.forEach(role => {
        if (resourceMap[permission.resource].roles[role.id]) {
          resourceMap[permission.resource].roles[role.id].push(permission);
        }
      });
    }
  });
  
  return Object.values(resourceMap);
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

const getPermissionTagType = (action) => {
  if (action.includes('all')) return 'danger';
  if (action === 'delete') return 'warning';
  if (action === 'create') return 'success';
  return 'info';
};

const fetchData = async () => {
  loading.value = true;
  try {
    const [rolesData, permissionsData] = await Promise.all([
      authAPI.getRoles(),
      authAPI.getPermissions(),
    ]);
    
    roles.value = rolesData;
    permissions.value = permissionsData;
  } catch (error) {
    ElMessage.error('获取数据失败');
  } finally {
    loading.value = false;
  }
};

const refreshData = () => {
  fetchData();
};

const createPermission = async () => {
  if (!permissionFormRef.value) return;
  
  try {
    await permissionFormRef.value.validate();
  } catch {
    return;
  }

  saving.value = true;
  try {
    await authAPI.createPermission(permissionForm.value);
    ElMessage.success('权限创建成功');
    showCreatePermissionDialog.value = false;
    resetPermissionForm();
    fetchData();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败');
  } finally {
    saving.value = false;
  }
};

const editPermission = (permission) => {
  selectedPermission.value = permission;
  showPermissionDetailsDialog.value = true;
};

const resetPermissionForm = () => {
  permissionForm.value = {
    name: '',
    resource: '',
    action: '',
    description: '',
  };
  if (permissionFormRef.value) {
    permissionFormRef.value.resetFields();
  }
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.permission-matrix {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.matrix-container {
  overflow-x: auto;
}

.permission-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 60px;
  padding: 4px;
}

.permission-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.permission-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>