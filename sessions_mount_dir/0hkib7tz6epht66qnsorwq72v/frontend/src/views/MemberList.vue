<template>
  <div class="member-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('member.title') }}</span>
          <el-button v-if="hasPermission('member:create')" type="primary" @click="handleAdd">{{ t('member.add') }}</el-button>
        </div>
      </template>

      <!-- 查询表单 -->
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item :label="t('member.name')">
          <el-input v-model="queryParams.name" :placeholder="t('member.namePlaceholder')" clearable />
        </el-form-item>
        <el-form-item :label="t('member.contact')">
          <el-input v-model="queryParams.contact" :placeholder="t('member.contactPlaceholder')" clearable />
        </el-form-item>
        <el-form-item :label="t('member.level')">
          <el-select v-model="queryParams.level" :placeholder="t('member.levelPlaceholder')" clearable>
            <el-option :label="t('member.levelNormal')" value="normal" />
            <el-option :label="t('member.levelSilver')" value="silver" />
            <el-option :label="t('member.levelGold')" value="gold" />
            <el-option :label="t('member.levelDiamond')" value="diamond" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">{{ t('common.search') }}</el-button>
          <el-button @click="resetQuery">{{ t('common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <!-- 操作按钮 -->
      <div class="table-operations">
        <el-button v-if="hasPermission('member:delete')" type="danger" :disabled="!selectedMembers.length" @click="handleBatchDelete">
          {{ t('member.batchDelete') }}
        </el-button>
        <el-button v-if="hasPermission('member:export')" type="success" @click="handleExport">{{ t('member.export') }}</el-button>
      </div>

      <!-- 数据表格 -->
      <el-table
        v-loading="loading"
        :data="memberList"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" :label="t('member.id')" width="80" />
        <el-table-column prop="name" :label="t('member.name')" />
        <el-table-column prop="contact" :label="t('member.contact')" />
        <el-table-column prop="level" :label="t('member.level')">
          <template #default="scope">
            <el-tag :type="getLevelType(scope.row.level)">{{ getLevelText(scope.row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="membership" :label="t('member.membership')">
          <template #default="scope">
            {{ scope.row.membership }} {{ t('member.days') }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('member.createdAt')" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="200" fixed="right">
          <template #default="scope">
            <el-button v-if="hasPermission('member:update')" type="primary" size="small" @click="handleEdit(scope.row)">{{ t('common.edit') }}</el-button>
            <el-button v-if="hasPermission('member:delete')" type="danger" size="small" @click="handleDelete(scope.row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="handleDialogClose"
    >
      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="memberRules"
        label-width="100px"
      >
        <el-form-item :label="t('member.name')" prop="name">
          <el-input v-model="memberForm.name" :placeholder="t('member.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('member.contact')" prop="contact">
          <el-input v-model="memberForm.contact" :placeholder="t('member.contactPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('member.level')" prop="level">
          <el-select v-model="memberForm.level" :placeholder="t('member.levelPlaceholder')">
            <el-option label="普通会员" value="normal" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('member.membership')" prop="membership">
          <el-input-number
            v-model="memberForm.membership"
            :min="0"
            :max="3650"
            controls-position="right"
          />
          <span style="margin-left: 10px">{{ t('member.days') }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleSubmit">{{ t('common.confirm') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import { memberApi } from '../api/member';
import { usePermission } from '../composables/usePermission';

// 查询参数
const queryParams = reactive({
  page: 1,
  size: 10,
  name: '',
  contact: '',
  level: '',
});

// 数据列表
const memberList = ref([]);
const total = ref(0);
const loading = ref(false);
const selectedMembers = ref([]);

// 对话框相关
const dialogVisible = ref(false);
const dialogTitle = ref('新增会员');
const memberFormRef = ref(null);
const isEdit = ref(false);
const currentMemberId = ref(null);

// 表单数据
const memberForm = reactive({
  name: '',
  contact: '',
  level: 'normal',
  membership: 365,
});

// 表单验证规则
const memberRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  contact: [{ required: true, message: '请输入联系方式', trigger: 'blur' }],
  level: [{ required: true, message: '请选择会员等级', trigger: 'change' }],
  membership: [{ required: true, message: '请输入剩余会籍', trigger: 'blur' }],
};

// 获取会员列表
const getMemberList = async () => {
  loading.value = true;
  try {
    const response = await memberApi.getMembers(queryParams);
    memberList.value = response.items || [];
    total.value = response.total || 0;
  } catch (error) {
    ElMessage.error(t('member.fetchError'));
  } finally {
    loading.value = false;
  }
};

// 查询
const handleQuery = () => {
  queryParams.page = 1;
  getMemberList();
};

// 重置查询
const resetQuery = () => {
  queryParams.name = '';
  queryParams.contact = '';
  queryParams.level = '';
  handleQuery();
};

// 分页大小改变
const handleSizeChange = (val) => {
  queryParams.size = val;
  getMemberList();
};

// 当前页改变
const handleCurrentChange = (val) => {
  queryParams.page = val;
  getMemberList();
};

// 表格选择改变
const handleSelectionChange = (selection) => {
  selectedMembers.value = selection;
};

// 新增会员
const handleAdd = () => {
  isEdit.value = false;
  dialogTitle.value = '新增会员';
  dialogVisible.value = true;
  resetForm();
};

// 编辑会员
const handleEdit = (row) => {
  isEdit.value = true;
  dialogTitle.value = '编辑会员';
  currentMemberId.value = row.id;
  dialogVisible.value = true;
  // 填充表单数据
  memberForm.name = row.name;
  memberForm.contact = row.contact;
  memberForm.level = row.level;
  memberForm.membership = row.membership;
};

// 删除会员
const handleDelete = (row) => {
  ElMessageBox.confirm(t('member.deleteConfirm'), t('common.prompt'), {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await memberApi.deleteMember(row.id);
        ElMessage.success(t('member.deleteSuccess'));
        getMemberList();
      } catch (error) {
        ElMessage.error(t('member.deleteError'));
      }
    })
    .catch(() => {});
};

// 批量删除
const handleBatchDelete = () => {
  if (!selectedMembers.value.length) {
    ElMessage.warning(t('member.selectToDelete'));
    return;
  }

  ElMessageBox.confirm(t('member.batchDeleteConfirm', { count: selectedMembers.value.length }), t('common.prompt'), {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        const deletePromises = selectedMembers.value.map((member) =>
          memberApi.deleteMember(member.id)
        );
        await Promise.all(deletePromises);
        ElMessage.success(t('member.batchDeleteSuccess'));
        getMemberList();
      } catch (error) {
        ElMessage.error(t('member.batchDeleteError'));
      }
    })
    .catch(() => {});
};

// 导出数据
const handleExport = () => {
  ElMessage.info(t('member.exportInDevelopment'));
};

// 提交表单
const handleSubmit = async () => {
  if (!memberFormRef.value) return;

  await memberFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          await memberApi.updateMember(currentMemberId.value, memberForm);
          ElMessage.success(t('member.updateSuccess'));
        } else {
          await memberApi.createMember(memberForm);
          ElMessage.success(t('member.createSuccess'));
        }
        dialogVisible.value = false;
        getMemberList();
      } catch (error) {
        ElMessage.error(isEdit.value ? t('member.updateError') : t('member.createError'));
      }
    }
  });
};

// 对话框关闭
const handleDialogClose = () => {
  resetForm();
};

// 重置表单
const resetForm = () => {
  memberForm.name = '';
  memberForm.contact = '';
  memberForm.level = 'normal';
  memberForm.membership = 365;
  if (memberFormRef.value) {
    memberFormRef.value.resetFields();
  }
};

// 获取会员等级类型
const getLevelType = (level) => {
  const typeMap = {
    normal: '',
    silver: 'info',
    gold: 'warning',
    diamond: 'success',
  };
  return typeMap[level] || '';
};

// 获取会员等级文本
const getLevelText = (level) => {
  const textMap = {
    normal: t('member.levelNormal'),
    silver: t('member.levelSilver'),
    gold: t('member.levelGold'),
    diamond: t('member.levelDiamond'),
  };
  return textMap[level] || level;
};

// 格式化日期
const formatDate = (date) => {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleString('zh-CN');
};

// 初始化
onMounted(() => {
  getMemberList();
});
</script>

<style scoped>
.member-list-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

.table-operations {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>