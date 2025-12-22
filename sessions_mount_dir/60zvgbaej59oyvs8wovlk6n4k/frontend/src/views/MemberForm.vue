<template>
  <div class="member-form-container">
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑会员' : '创建会员' }}</span>
        </div>
      </template>
      
      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="rules"
        label-width="120px"
        label-position="right"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="姓名" prop="name">
          <el-input
            v-model="memberForm.name"
            placeholder="请输入会员姓名"
            clearable
          />
        </el-form-item>
        
        <el-form-item label="手机号码" prop="phone">
          <el-input
            v-model="memberForm.phone"
            placeholder="请输入手机号码"
            clearable
          />
        </el-form-item>
        
        <el-form-item label="会员卡号" prop="card_number">
          <el-input
            v-model="memberForm.card_number"
            placeholder="请输入会员卡号"
            clearable
          />
        </el-form-item>
        
        <el-form-item label="会员等级" prop="membership_level">
          <el-select
            v-model="memberForm.membership_level"
            placeholder="请选择会员等级"
            clearable
          >
            <el-option
              v-for="level in membershipLevels"
              :key="level.value"
              :label="level.label"
              :value="level.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="剩余会籍时长" prop="remaining_duration">
          <el-input-number
            v-model="memberForm.remaining_duration"
            :min="0"
            :max="3650"
            :step="1"
            controls-position="right"
          />
          <span class="unit">天</span>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
          >
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { api } from '../api';

const route = useRoute();
const router = useRouter();
const memberFormRef = ref(null);
const loading = ref(false);

// 判断是否为编辑模式
const isEdit = computed(() => !!route.params.id);

// 会员等级选项
const membershipLevels = [
  { value: 'bronze', label: '青铜会员' },
  { value: 'silver', label: '白银会员' },
  { value: 'gold', label: '黄金会员' },
  { value: 'platinum', label: '铂金会员' },
  { value: 'diamond', label: '钻石会员' }
];

// 表单数据
const memberForm = reactive({
  name: '',
  phone: '',
  card_number: '',
  membership_level: '',
  remaining_duration: 0
});

// 表单校验规则
const rules = {
  name: [
    { required: true, message: '请输入会员姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
  ],
  card_number: [
    { required: true, message: '请输入会员卡号', trigger: 'blur' },
    { min: 8, max: 20, message: '长度在 8 到 20 个字符', trigger: 'blur' }
  ],
  membership_level: [
    { required: true, message: '请选择会员等级', trigger: 'change' }
  ],
  remaining_duration: [
    { required: true, message: '请输入剩余会籍时长', trigger: 'blur' },
    { type: 'number', min: 0, message: '会籍时长不能小于0', trigger: 'blur' }
  ]
};

// 获取会员详情
const fetchMemberDetail = async (id) => {
  try {
    loading.value = true;
    const response = await api.get(`/members/${id}`);
    const memberData = response.data;
    
    // 填充表单数据
    Object.keys(memberForm).forEach(key => {
      if (memberData[key] !== undefined) {
        memberForm[key] = memberData[key];
      }
    });
  } catch (error) {
    console.error('获取会员详情失败:', error);
    ElMessage.error('获取会员详情失败');
    router.push('/members');
  } finally {
    loading.value = false;
  }
};

// 提交表单
const handleSubmit = async () => {
  if (!memberFormRef.value) return;
  
  try {
    await memberFormRef.value.validate();
    loading.value = true;
    
    if (isEdit.value) {
      // 更新会员
      await api.put(`/members/${route.params.id}`, memberForm);
      ElMessage.success('会员信息更新成功');
    } else {
      // 创建会员
      await api.post('/members', memberForm);
      ElMessage.success('会员创建成功');
    }
    
    // 返回会员列表页
    router.push('/members');
  } catch (error) {
    console.error('提交失败:', error);
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail);
    } else {
      ElMessage.error(isEdit.value ? '更新会员失败' : '创建会员失败');
    }
  } finally {
    loading.value = false;
  }
};

// 取消操作
const handleCancel = () => {
  ElMessageBox.confirm('确定要取消吗？未保存的数据将丢失', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      router.push('/members');
    })
    .catch(() => {
      // 用户取消操作
    });
};

// 组件挂载时，如果是编辑模式则获取会员详情
onMounted(() => {
  if (isEdit.value) {
    fetchMemberDetail(route.params.id);
  }
});
</script>

<style scoped>
.member-form-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.form-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.unit {
  margin-left: 10px;
  color: #909399;
}

.el-form-item {
  margin-bottom: 24px;
}

.el-button {
  margin-right: 10px;
}
</style>