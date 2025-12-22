<template>
  <div class="member-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>会员管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增会员
          </el-button>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-container">
        <el-form :inline="true" :model="queryParams" class="demo-form-inline">
          <el-form-item label="搜索">
            <el-input
              v-model="queryParams.search"
              placeholder="姓名/手机号/会员卡号"
              clearable
              @keyup.enter="handleQuery"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryParams.status" placeholder="全部" clearable>
              <el-option label="活跃" value="active" />
              <el-option label="冻结" value="frozen" />
              <el-option label="过期" value="expired" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleQuery">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetQuery">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 会员列表 -->
      <el-table
        v-loading="loading"
        :data="memberList"
        style="width: 100%"
        border
        stripe
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="phone" label="手机号" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="card_number" label="会员卡号" width="180" />
        <el-table-column prop="level" label="会员等级" width="120">
          <template #default="scope">
            <el-tag :type="getLevelTagType(scope.row.level)">
              {{ scope.row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleView(scope.row)">
              查看
            </el-button>
            <el-button size="small" type="primary" @click="handleEdit(scope.row)">
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
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

    <!-- 会员表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="memberRules"
        label-width="100px"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="memberForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="memberForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="memberForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="会员卡号" prop="card_number">
          <el-input v-model="memberForm.card_number" placeholder="请输入会员卡号" />
        </el-form-item>
        <el-form-item label="会员等级" prop="level">
          <el-select v-model="memberForm.level" placeholder="请选择会员等级">
            <el-option label="普通会员" value="normal" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="memberForm.status" placeholder="请选择状态">
            <el-option label="活跃" value="active" />
            <el-option label="冻结" value="frozen" />
            <el-option label="过期" value="expired" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, Refresh } from '@element-plus/icons-vue';
import memberApi from '@/api/member';

// 查询参数
const queryParams = reactive({
  page: 1,
  size: 10,
  search: '',
  status: '',
});

// 会员列表数据
const memberList = ref([]);
const total = ref(0);
const loading = ref(false);

// 对话框相关
const dialogVisible = ref(false);
const dialogTitle = ref('');
const dialogType = ref(''); // 'add', 'edit', 'view'
const memberFormRef = ref(null);

// 表单数据
const memberForm = reactive({
  id: null,
  name: '',
  phone: '',
  email: '',
  card_number: '',
  level: '',
  status: '',
});

// 表单验证规则
const memberRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' },
  ],
  card_number: [{ required: true, message: '请输入会员卡号', trigger: 'blur' }],
  level: [{ required: true, message: '请选择会员等级', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
};

// 获取会员列表
const getMemberList = async () => {
  loading.value = true;
  try {
    const response = await memberApi.getMembers(queryParams);
    memberList.value = response.data.items || [];
    total.value = response.data.total || 0;
  } catch (error) {
    ElMessage.error('获取会员列表失败');
    console.error('Error fetching member list:', error);
  } finally {
    loading.value = false;
  }
};

// 搜索
const handleQuery = () => {
  queryParams.page = 1;
  getMemberList();
};

// 重置查询
const resetQuery = () => {
  queryParams.search = '';
  queryParams.status = '';
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

// 新增会员
const handleAdd = () => {
  dialogType.value = 'add';
  dialogTitle.value = '新增会员';
  resetForm();
  dialogVisible.value = true;
};

// 查看会员
const handleView = (row) => {
  dialogType.value = 'view';
  dialogTitle.value = '查看会员';
  Object.assign(memberForm, row);
  dialogVisible.value = true;
};

// 编辑会员
const handleEdit = (row) => {
  dialogType.value = 'edit';
  dialogTitle.value = '编辑会员';
  Object.assign(memberForm, row);
  dialogVisible.value = true;
};

// 删除会员
const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该会员吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await memberApi.deleteMember(row.id);
        ElMessage.success('删除成功');
        getMemberList();
      } catch (error) {
        ElMessage.error('删除失败');
        console.error('Error deleting member:', error);
      }
    })
    .catch(() => {
      // 用户取消删除
    });
};

// 提交表单
const submitForm = async () => {
  if (!memberFormRef.value) return;

  await memberFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (dialogType.value === 'add') {
          await memberApi.createMember(memberForm);
          ElMessage.success('新增成功');
        } else if (dialogType.value === 'edit') {
          await memberApi.updateMember(memberForm.id, memberForm);
          ElMessage.success('更新成功');
        }
        dialogVisible.value = false;
        getMemberList();
      } catch (error) {
        ElMessage.error(dialogType.value === 'add' ? '新增失败' : '更新失败');
        console.error('Error submitting form:', error);
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
  if (memberFormRef.value) {
    memberFormRef.value.resetFields();
  }
  Object.assign(memberForm, {
    id: null,
    name: '',
    phone: '',
    email: '',
    card_number: '',
    level: '',
    status: '',
  });
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
};

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    active: '活跃',
    frozen: '冻结',
    expired: '过期',
  };
  return statusMap[status] || status;
};

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    active: 'success',
    frozen: 'warning',
    expired: 'danger',
  };
  return typeMap[status] || 'info';
};

// 获取等级标签类型
const getLevelTagType = (level) => {
  const typeMap = {
    normal: '',
    silver: 'info',
    gold: 'warning',
    diamond: 'success',
  };
  return typeMap[level] || 'info';
};

// 组件挂载
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

.filter-container {
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
  gap: 10px;
}
</style>