<template>
  <div class="member-detail-container">
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <span>会员详情</span>
          <el-button type="primary" @click="toggleEdit">
            {{ isEditing ? '取消编辑' : '编辑信息' }}
          </el-button>
        </div>
      </template>

      <el-form
        ref="memberFormRef"
        :model="memberForm"
        :rules="rules"
        label-width="120px"
        :disabled="!isEditing"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="memberForm.name" placeholder="请输入姓名" />
        </el-form-item>

        <el-form-item label="联系方式" prop="phone">
          <el-input v-model="memberForm.phone" placeholder="请输入手机号" />
        </el-form-item>

        <el-form-item label="身份证号" prop="id_card">
          <el-input v-model="memberForm.id_card" placeholder="请输入身份证号" />
        </el-form-item>

        <el-form-item label="健康状况" prop="health_status">
          <el-select
            v-model="memberForm.health_status"
            placeholder="请选择健康状况"
            style="width: 100%"
          >
            <el-option label="良好" value="good" />
            <el-option label="一般" value="fair" />
            <el-option label="较差" value="poor" />
          </el-select>
        </el-form-item>

        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="memberForm.notes"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>

        <el-form-item v-if="isEditing">
          <el-button type="primary" @click="saveMember">保存</el-button>
          <el-button @click="toggleEdit">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="operation-card">
      <template #header>
        <span>操作</span>
      </template>
      <el-button type="danger" @click="handleDelete">删除会员</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import request from '../utils/request';

const route = useRoute();
const router = useRouter();
const memberFormRef = ref(null);
const isEditing = ref(false);
const loading = ref(false);

const memberForm = ref({
  name: '',
  phone: '',
  id_card: '',
  health_status: '',
  notes: ''
});

const rules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  id_card: [
    { required: true, message: '请输入身份证号', trigger: 'blur' },
    { pattern: /^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/, message: '请输入正确的身份证号', trigger: 'blur' }
  ],
  health_status: [
    { required: true, message: '请选择健康状况', trigger: 'change' }
  ]
};

const fetchMemberDetail = async () => {
  try {
    loading.value = true;
    const response = await request.get(`/api/members/${route.params.id}`);
    memberForm.value = response.data;
  } catch (error) {
    ElMessage.error('获取会员详情失败');
    console.error('Error fetching member detail:', error);
  } finally {
    loading.value = false;
  }
};

const toggleEdit = () => {
  isEditing.value = !isEditing.value;
  if (!isEditing.value) {
    fetchMemberDetail();
  }
};

const saveMember = async () => {
  if (!memberFormRef.value) return;
  
  try {
    await memberFormRef.value.validate();
    loading.value = true;
    
    await request.put(`/api/members/${route.params.id}`, memberForm.value);
    ElMessage.success('保存成功');
    isEditing.value = false;
  } catch (error) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail);
    } else {
      ElMessage.error('保存失败');
    }
    console.error('Error saving member:', error);
  } finally {
    loading.value = false;
  }
};

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除该会员吗？此操作不可恢复',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    loading.value = true;
    await request.delete(`/api/members/${route.params.id}`);
    ElMessage.success('删除成功');
    router.push('/members');
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
      console.error('Error deleting member:', error);
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchMemberDetail();
});
</script>

<style scoped>
.member-detail-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.detail-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.operation-card {
  margin-top: 20px;
}
</style>