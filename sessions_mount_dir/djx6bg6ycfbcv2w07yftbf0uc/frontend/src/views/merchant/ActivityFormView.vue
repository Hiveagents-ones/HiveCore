<template>
  <div class="activity-form-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑活动' : '创建活动' }}</span>
          <el-button type="primary" @click="handleSaveDraft" :loading="savingDraft">
            保存草稿
          </el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="活动名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入活动名称"
            @blur="validateField('name')"
          />
        </el-form-item>

        <el-form-item label="活动时间" prop="activity_time">
          <el-date-picker
            v-model="formData.activity_time"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
            @change="validateField('activity_time')"
          />
        </el-form-item>

        <el-form-item label="活动地点" prop="location">
          <el-input
            v-model="formData.location"
            placeholder="请输入活动地点"
            @blur="validateField('location')"
          />
        </el-form-item>

        <el-form-item label="活动规则" prop="rules">
          <el-input
            v-model="formData.rules"
            type="textarea"
            :rows="4"
            placeholder="请输入活动规则"
            @blur="validateField('rules')"
          />
        </el-form-item>

        <el-form-item label="活动奖励" prop="rewards">
          <el-input
            v-model="formData.rewards"
            type="textarea"
            :rows="4"
            placeholder="请输入活动奖励"
            @blur="validateField('rewards')"
          />
        </el-form-item>

        <el-form-item label="最大参与人数" prop="max_participants">
          <el-input-number
            v-model="formData.max_participants"
            :min="1"
            :max="10000"
            @change="validateField('max_participants')"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
          <el-button @click="handleCancel">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 并发编辑提示 -->
    <el-dialog
      v-model="showConflictDialog"
      title="检测到冲突"
      width="30%"
    >
      <span>该活动正在被其他用户编辑，是否继续保存？</span>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showConflictDialog = false">取消</el-button>
          <el-button type="primary" @click="forceSave">强制保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { activityApi } from '../../services/api';

const route = useRoute();
const router = useRouter();
const formRef = ref(null);
const isEdit = ref(false);
const submitting = ref(false);
const savingDraft = ref(false);
const showConflictDialog = ref(false);
const lastSavedData = ref(null);
const draftTimer = ref(null);

const formData = reactive({
  name: '',
  activity_time: [],
  location: '',
  rules: '',
  rewards: '',
  max_participants: 50,
  is_draft: false,
});

const rules = {
  name: [
    { required: true, message: '请输入活动名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  activity_time: [
    { required: true, message: '请选择活动时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (value && value.length === 2) {
          const start = new Date(value[0]);
          const end = new Date(value[1]);
          if (start >= end) {
            callback(new Error('结束时间必须大于开始时间'));
          } else {
            callback();
          }
        } else {
          callback();
        }
      },
      trigger: 'change',
    },
  ],
  location: [
    { required: true, message: '请输入活动地点', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' },
  ],
  rules: [
    { required: true, message: '请输入活动规则', trigger: 'blur' },
    { min: 10, max: 1000, message: '长度在 10 到 1000 个字符', trigger: 'blur' },
  ],
  rewards: [
    { required: true, message: '请输入活动奖励', trigger: 'blur' },
    { min: 10, max: 500, message: '长度在 10 到 500 个字符', trigger: 'blur' },
  ],
  max_participants: [
    { required: true, message: '请输入最大参与人数', trigger: 'change' },
    { type: 'number', min: 1, max: 10000, message: '人数在 1 到 10000 之间', trigger: 'change' },
  ],
};

// 自动补全功能
const setupAutoComplete = () => {
  // 这里可以添加自动补全逻辑，例如从本地存储或API获取常用数据
  const savedLocations = JSON.parse(localStorage.getItem('savedLocations') || '[]');
  if (savedLocations.length > 0) {
    // 可以在这里设置自动补全组件
  }
};

// 草稿保存功能
const saveDraft = async () => {
  try {
    savingDraft.value = true;
    const draftData = { ...formData, is_draft: true };
    
    if (isEdit.value) {
      await activityApi.updateActivity(route.params.id, draftData);
    } else {
      await activityApi.createActivity(draftData);
    }
    
    lastSavedData.value = JSON.parse(JSON.stringify(formData));
    ElMessage.success('草稿保存成功');
  } catch (error) {
    ElMessage.error('草稿保存失败: ' + error.message);
  } finally {
    savingDraft.value = false;
  }
};

// 定时保存草稿
const startAutoSave = () => {
  draftTimer.value = setInterval(() => {
    if (JSON.stringify(formData) !== JSON.stringify(lastSavedData.value)) {
      saveDraft();
    }
  }, 30000); // 每30秒自动保存一次
};

const stopAutoSave = () => {
  if (draftTimer.value) {
    clearInterval(draftTimer.value);
    draftTimer.value = null;
  }
};

// 表单验证
const validateField = async (field) => {
  try {
    await formRef.value.validateField(field);
  } catch (error) {
    // 验证失败不做处理
  }
};

// 提交表单
const handleSubmit = async () => {
  try {
    await formRef.value.validate();
    submitting.value = true;
    
    const submitData = { ...formData, is_draft: false };
    
    if (isEdit.value) {
      await activityApi.updateActivity(route.params.id, submitData);
      ElMessage.success('活动更新成功');
    } else {
      await activityApi.createActivity(submitData);
      ElMessage.success('活动创建成功');
    }
    
    router.push('/merchant/activities');
  } catch (error) {
    if (error.message.includes('conflict')) {
      showConflictDialog.value = true;
    } else {
      ElMessage.error('提交失败: ' + error.message);
    }
  } finally {
    submitting.value = false;
  }
};

// 强制保存
const forceSave = async () => {
  try {
    showConflictDialog.value = false;
    const submitData = { ...formData, is_draft: false, force: true };
    
    if (isEdit.value) {
      await activityApi.updateActivity(route.params.id, submitData);
      ElMessage.success('活动更新成功');
    } else {
      await activityApi.createActivity(submitData);
      ElMessage.success('活动创建成功');
    }
    
    router.push('/merchant/activities');
  } catch (error) {
    ElMessage.error('强制保存失败: ' + error.message);
  }
};

// 取消操作
const handleCancel = async () => {
  try {
    await ElMessageBox.confirm('确定要取消吗？未保存的更改将丢失', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    router.push('/merchant/activities');
  } catch (error) {
    // 用户取消
  }
};

// 保存草稿按钮点击
const handleSaveDraft = () => {
  saveDraft();
};

// 监听表单数据变化
watch(
  () => formData,
  () => {
    // 可以在这里添加实时验证逻辑
  },
  { deep: true }
);

// 初始化
onMounted(async () => {
  setupAutoComplete();
  
  if (route.params.id) {
    isEdit.value = true;
    try {
      const activity = await activityApi.getActivityById(route.params.id);
      Object.assign(formData, {
        name: activity.name || '',
        activity_time: activity.activity_time || [],
        location: activity.location || '',
        rules: activity.rules || '',
        rewards: activity.rewards || '',
        max_participants: activity.max_participants || 50,
      });
      lastSavedData.value = JSON.parse(JSON.stringify(formData));
    } catch (error) {
      ElMessage.error('获取活动信息失败: ' + error.message);
      router.push('/merchant/activities');
    }
  }
  
  startAutoSave();
});

// 清理
onBeforeUnmount(() => {
  stopAutoSave();
});
</script>

<style scoped>
.activity-form-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>