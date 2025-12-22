<template>
  <div class="coach-detail">
    <div class="page-header">
      <el-button @click="handleBack" class="back-button">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1>教练详情</h1>
      <div class="actions">
        <el-button type="primary" @click="handleEdit">
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
      </div>
    </div>

    <el-card v-loading="loading" class="coach-info-card">
      <template #header>
        <div class="card-header">
          <span>基本信息</span>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="ID">{{ coach.id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ coach.name }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ coach.phone }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ coach.email }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ coach.gender }}</el-descriptions-item>
        <el-descriptions-item label="年龄">{{ coach.age }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="coach.status === 'active' ? 'success' : 'danger'">
            {{ coach.status === 'active' ? '在职' : '离职' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="入职日期">{{ coach.hire_date }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="coach-specialties-card">
      <template #header>
        <div class="card-header">
          <span>专长领域</span>
        </div>
      </template>
      
      <div class="specialties">
        <el-tag
          v-for="specialty in coach.specialties"
          :key="specialty"
          class="mr-2 mb-2"
          type="success"
        >
          {{ specialty }}
        </el-tag>
      </div>
    </el-card>

    <el-card class="coach-bio-card">
      <template #header>
        <div class="card-header">
          <span>个人简介</span>
        </div>
      </template>
      
      <div class="bio-content">
        {{ coach.bio || '暂无简介' }}
      </div>
    </el-card>

    <el-card class="coach-courses-card">
      <template #header>
        <div class="card-header">
          <span>授课课程</span>
        </div>
      </template>
      
      <el-table
        :data="coach.courses"
        style="width: 100%"
        stripe
        empty-text="暂无授课课程"
      >
        <el-table-column prop="id" label="课程ID" width="80" />
        <el-table-column prop="name" label="课程名称" min-width="150" />
        <el-table-column prop="type" label="课程类型" width="120" />
        <el-table-column prop="duration" label="时长" width="100" />
        <el-table-column prop="max_capacity" label="最大容量" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '进行中' : '已结束' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit } from '@element-plus/icons-vue'
import { getCoachDetail } from '@/api/coach'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const coach = ref({
  id: '',
  name: '',
  phone: '',
  email: '',
  gender: '',
  age: '',
  status: '',
  hire_date: '',
  specialties: [],
  bio: '',
  courses: []
})

const fetchCoachDetail = async () => {
  try {
    loading.value = true
    const coachId = route.params.id
    const response = await getCoachDetail(coachId)
    coach.value = response.data
  } catch (error) {
    ElMessage.error('获取教练详情失败')
    console.error('Error fetching coach detail:', error)
  } finally {
    loading.value = false
  }
}

const handleBack = () => {
  router.push('/coaches')
}

const handleEdit = () => {
  router.push(`/coaches/${coach.value.id}/edit`)
}

onMounted(() => {
  fetchCoachDetail()
})
</script>

<style scoped>
.coach-detail {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 20px;
  font-size: 24px;
  color: #303133;
}

.back-button {
  padding: 8px 15px;
}

.actions {
  margin-left: auto;
}

.coach-info-card,
.coach-specialties-card,
.coach-bio-card,
.coach-courses-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.specialties {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.bio-content {
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
}

.mr-2 {
  margin-right: 8px;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>