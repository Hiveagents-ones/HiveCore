<template>
  <div class="member-list-container">
    <!-- 页面标题和操作区 -->
    <div class="page-header">
      <h2>{{ $t('members.title') }}</h2>
      <div class="actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          {{ $t('common.create') }}
        </el-button>
        <el-button @click="handleImport">
          <el-icon><Upload /></el-icon>
          {{ $t('common.import') }}
        </el-button>
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          {{ $t('common.export') }}
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选区 -->
    <div class="search-filters">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('members.searchPlaceholder')"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select
            v-model="statusFilter"
            :placeholder="$t('members.statusFilter')"
            clearable
            @change="handleFilter"
          >
            <el-option
              v-for="item in statusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select
            v-model="levelFilter"
            :placeholder="$t('members.levelFilter')"
            clearable
            @change="handleFilter"
          >
            <el-option
              v-for="item in levelOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="handleSearch">
            {{ $t('common.search') }}
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stats-card">
            <div class="stats-content">
              <div class="stats-value">{{ memberCount }}</div>
              <div class="stats-label">{{ $t('members.totalMembers') }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stats-card">
            <div class="stats-content">
              <div class="stats-value">{{ activeMembers.length }}</div>
              <div class="stats-label">{{ $t('members.activeMembers') }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stats-card">
            <div class="stats-content">
              <div class="stats-value">{{ expiredMembers.length }}</div>
              <div class="stats-label">{{ $t('members.expiredMembers') }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stats-card">
            <div class="stats-content">
              <div class="stats-value">{{ newMembersThisMonth }}</div>
              <div class="stats-label">{{ $t('members.newMembersThisMonth') }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 会员列表表格 -->
    <el-table
      v-loading="loading"
      :data="members"
      stripe
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" :label="$t('members.name')" width="120" />
      <el-table-column prop="phone" :label="$t('members.phone')" width="150" />
      <el-table-column prop="email" :label="$t('members.email')" width="200" />
      <el-table-column prop="level" :label="$t('members.level')" width="100">
        <template #default="scope">
          <el-tag :type="getLevelTagType(scope.row.level)">
            {{ scope.row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="join_date" :label="$t('members.joinDate')" width="120">
        <template #default="scope">
          {{ formatDate(scope.row.join_date) }}
        </template>
      </el-table-column>
      <el-table-column prop="expiry_date" :label="$t('members.expiryDate')" width="120">
        <template #default="scope">
          {{ formatDate(scope.row.expiry_date) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" :label="$t('members.status')" width="100">
        <template #default="scope">
          <el-tag :type="getStatusTagType(scope.row)">
            {{ getStatusText(scope.row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.actions')" width="200">
        <template #default="scope">
          <el-button size="small" @click="handleView(scope.row)">
            {{ $t('common.view') }}
          </el-button>
          <el-button size="small" type="primary" @click="handleEdit(scope.row)">
            {{ $t('common.edit') }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">
            {{ $t('common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 会员表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <member-form
        v-if="dialogVisible"
        :member="currentMember"
        :is-edit="isEdit"
        @submit="handleFormSubmit"
        @cancel="handleDialogClose"
      />
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      :title="$t('members.importTitle')"
      width="500px"
    >
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls,.csv"
        drag
        @change="handleFileChange"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          {{ $t('members.importText') }}
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ $t('members.importTip') }}
          </div>
        </template>
      </el-upload>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="importDialogVisible = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleImportSubmit">
            {{ $t('common.confirm') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, Upload, Download, UploadFilled } from '@element-plus/icons-vue';
import { useMembersStore } from '@/stores/members';
import { memberApi } from '@/api/member';
import MemberForm from '@/components/MemberForm.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();
const membersStore = useMembersStore();

// 响应式数据
const searchQuery = ref('');
const statusFilter = ref('');
const levelFilter = ref('');
const selectedMembers = ref([]);
const dialogVisible = ref(false);
const importDialogVisible = ref(false);
const isEdit = ref(false);
const currentMember = ref(null);
const uploadRef = ref(null);
const importFile = ref(null);

// 状态选项
const statusOptions = [
  { value: 'active', label: t('members.statusActive') },
  { value: 'expired', label: t('members.statusExpired') },
];

// 等级选项
const levelOptions = [
  { value: 'Bronze', label: t('members.levelBronze') },
  { value: 'Silver', label: t('members.levelSilver') },
  { value: 'Gold', label: t('members.levelGold') },
  { value: 'Platinum', label: t('members.levelPlatinum') },
];

// 计算属性
const { members, loading, pagination } = membersStore;
const memberCount = computed(() => membersStore.memberCount);
const activeMembers = computed(() => membersStore.activeMembers);
const expiredMembers = computed(() => membersStore.expiredMembers);

// 计算本月新增会员数
const newMembersThisMonth = computed(() => {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();
  
  return members.value.filter(member => {
    const joinDate = new Date(member.join_date);
    return joinDate.getMonth() === currentMonth && joinDate.getFullYear() === currentYear;
  }).length;
});

// 对话框标题
const dialogTitle = computed(() => {
  return isEdit.value ? t('members.editMember') : t('members.createMember');
});

// 方法
const fetchMembers = async () => {
  const params = {};
  
  if (searchQuery.value) {
    params.search = searchQuery.value;
  }
  
  if (statusFilter.value) {
    params.status = statusFilter.value;
  }
  
  if (levelFilter.value) {
    params.level = levelFilter.value;
  }
  
  await membersStore.fetchMembers(params);
};

const handleSearch = () => {
  pagination.page = 1;
  fetchMembers();
};

const handleFilter = () => {
  pagination.page = 1;
  fetchMembers();
};

const handleSizeChange = (size) => {
  pagination.size = size;
  fetchMembers();
};

const handleCurrentChange = (page) => {
  pagination.page = page;
  fetchMembers();
};

const handleSelectionChange = (selection) => {
  selectedMembers.value = selection;
};

const handleView = (member) => {
  router.push(`/members/${member.id}`);
};

const handleCreate = () => {
  isEdit.value = false;
  currentMember.value = null;
  dialogVisible.value = true;
};

const handleEdit = (member) => {
  isEdit.value = true;
  currentMember.value = { ...member };
  dialogVisible.value = true;
};

const handleDelete = async (member) => {
  try {
    await ElMessageBox.confirm(
      t('members.deleteConfirm', { name: member.name }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    );
    
    await memberApi.deleteMember(member.id);
    ElMessage.success(t('members.deleteSuccess'));
    fetchMembers();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('members.deleteError'));
    }
  }
};

const handleDialogClose = () => {
  dialogVisible.value = false;
  currentMember.value = null;
};

const handleFormSubmit = async (formData) => {
  try {
    if (isEdit.value) {
      await memberApi.updateMember(currentMember.value.id, formData);
      ElMessage.success(t('members.updateSuccess'));
    } else {
      await memberApi.createMember(formData);
      ElMessage.success(t('members.createSuccess'));
    }
    
    dialogVisible.value = false;
    fetchMembers();
  } catch (error) {
    ElMessage.error(isEdit.value ? t('members.updateError') : t('members.createError'));
  }
};

const handleImport = () => {
  importDialogVisible.value = true;
};

const handleFileChange = (file) => {
  importFile.value = file.raw;
};

const handleImportSubmit = async () => {
  if (!importFile.value) {
    ElMessage.warning(t('members.selectFileWarning'));
    return;
  }
  
  try {
    const formData = new FormData();
    formData.append('file', importFile.value);
    
    await memberApi.importMembers(formData);
    ElMessage.success(t('members.importSuccess'));
    importDialogVisible.value = false;
    importFile.value = null;
    uploadRef.value.clearFiles();
    fetchMembers();
  } catch (error) {
    ElMessage.error(t('members.importError'));
  }
};

const handleExport = async () => {
  try {
    const response = await memberApi.exportMembers();
    const url = window.URL.createObjectURL(new Blob([response]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'members.xlsx');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    ElMessage.success(t('members.exportSuccess'));
  } catch (error) {
    ElMessage.error(t('members.exportError'));
  }
};

// 辅助函数
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const getLevelTagType = (level) => {
  const levelTypes = {
    Bronze: 'info',
    Silver: '',
    Gold: 'warning',
    Platinum: 'success',
  };
  return levelTypes[level] || '';
};

const getStatusTagType = (member) => {
  const today = new Date();
  const expiryDate = new Date(member.expiry_date);
  return expiryDate >= today ? 'success' : 'danger';
};

const getStatusText = (member) => {
  const today = new Date();
  const expiryDate = new Date(member.expiry_date);
  return expiryDate >= today ? t('members.statusActive') : t('members.statusExpired');
};

// 生命周期
onMounted(() => {
  fetchMembers();
});
</script>

<style scoped>
.member-list-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.actions {
  display: flex;
  gap: 10px;
}

.search-filters {
  margin-bottom: 20px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stats-cards {
  margin-bottom: 20px;
}

.stats-card {
  text-align: center;
}

.stats-content {
  padding: 10px;
}

.stats-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 5px;
}

.stats-label {
  font-size: 14px;
  color: #909399;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>