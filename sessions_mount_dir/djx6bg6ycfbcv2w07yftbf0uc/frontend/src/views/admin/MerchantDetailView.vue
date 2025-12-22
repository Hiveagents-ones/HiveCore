<template>
  <div class="merchant-detail-view">
    <div class="page-header">
      <h1>商家详情</h1>
      <div class="actions">
        <el-button @click="$router.go(-1)">返回</el-button>
        <el-button v-if="merchant.status === 'pending'" type="success" @click="handleApprove">审核通过</el-button>
        <el-button v-if="merchant.status === 'pending'" type="danger" @click="handleReject">审核拒绝</el-button>
        <el-button v-if="merchant.status === 'active'" type="warning" @click="handleOffline">下线处理</el-button>
        <el-button v-if="merchant.status === 'offline'" type="success" @click="handleOnline">重新上线</el-button>
      </div>
    </div>

    <el-card v-loading="loading" class="merchant-info">
      <template #header>
        <div class="card-header">
          <span>基本信息</span>
          <el-button type="primary" @click="editMode = !editMode">
            {{ editMode ? '取消编辑' : '编辑信息' }}
          </el-button>
        </div>
      </template>

      <el-form :model="merchant" label-width="120px" :disabled="!editMode">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="商家名称">
              <el-input v-model="merchant.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="merchant.contact_person" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="merchant.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="merchant.email" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="商家地址">
          <el-input v-model="merchant.address" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item label="商家简介">
          <el-input v-model="merchant.description" type="textarea" :rows="3" />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="营业执照">
              <el-image
                v-if="merchant.license_url"
                :src="merchant.license_url"
                fit="contain"
                style="width: 200px; height: 200px"
                :preview-src-list="[merchant.license_url]"
              />
              <span v-else>暂无</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-tag :type="getStatusType(merchant.status)">{{ getStatusText(merchant.status) }}</el-tag>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="创建时间">
          <span>{{ formatDate(merchant.created_at) }}</span>
        </el-form-item>

        <el-form-item label="更新时间">
          <span>{{ formatDate(merchant.updated_at) }}</span>
        </el-form-item>

        <el-form-item v-if="editMode">
          <el-button type="primary" @click="handleSave">保存</el-button>
          <el-button @click="editMode = false">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="merchant-stats">
      <template #header>
        <span>经营数据</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ merchant.product_count || 0 }}</div>
            <div class="stat-label">商品数量</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ merchant.order_count || 0 }}</div>
            <div class="stat-label">订单数量</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">¥{{ merchant.total_sales || '0.00' }}</div>
            <div class="stat-label">总销售额</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ merchant.rating || '0.0' }}</div>
            <div class="stat-label">评分</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMerchant, updateMerchant, approveMerchant, rejectMerchant, offlineMerchant, onlineMerchant } from '@/api/merchant'

const route = useRoute()
const router = useRouter()
const merchantId = route.params.id

const loading = ref(false)
const editMode = ref(false)
const merchant = ref({
  id: '',
  name: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  description: '',
  license_url: '',
  status: '',
  created_at: '',
  updated_at: '',
  product_count: 0,
  order_count: 0,
  total_sales: '0.00',
  rating: '0.0'
})

const fetchMerchant = async () => {
  loading.value = true
  try {
    const response = await getMerchant(merchantId)
    merchant.value = response.data
  } catch (error) {
    ElMessage.error('获取商家信息失败')
    router.push('/admin/merchants')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  try {
    await updateMerchant(merchantId, merchant.value)
    ElMessage.success('保存成功')
    editMode.value = false
    fetchMerchant()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleApprove = async () => {
  try {
    await ElMessageBox.confirm('确认审核通过该商家？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await approveMerchant(merchantId)
    ElMessage.success('审核通过')
    fetchMerchant()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleReject = async () => {
  try {
    await ElMessageBox.confirm('确认拒绝该商家申请？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await rejectMerchant(merchantId)
    ElMessage.success('已拒绝')
    fetchMerchant()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleOffline = async () => {
  try {
    await ElMessageBox.confirm('确认下线该商家？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await offlineMerchant(merchantId)
    ElMessage.success('已下线')
    fetchMerchant()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleOnline = async () => {
  try {
    await ElMessageBox.confirm('确认重新上线该商家？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await onlineMerchant(merchantId)
    ElMessage.success('已上线')
    fetchMerchant()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    active: 'success',
    offline: 'danger',
    rejected: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待审核',
    active: '正常营业',
    offline: '已下线',
    rejected: '已拒绝'
  }
  return texts[status] || '未知'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchMerchant()
})
</script>

<style scoped>
.merchant-detail-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.actions {
  display: flex;
  gap: 10px;
}

.merchant-info {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.merchant-stats {
  margin-top: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}
</style>