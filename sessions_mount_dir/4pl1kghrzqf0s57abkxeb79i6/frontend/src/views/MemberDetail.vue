<template>
  <div class="member-detail">
    <el-page-header @back="goBack" :title="pageTitle">
      <template #content>
        <div class="flex items-center">
          <el-tag :type="getStatusType(member.status)" size="small">
            {{ getStatusText(member.status) }}
          </el-tag>
          <span class="ml-2">{{ member.name }}</span>
        </div>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="mt-4">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>基本信息</span>
              <el-button 
                type="primary" 
                :icon="isEditing ? 'Check' : 'Edit'" 
                @click="toggleEdit"
                :loading="loading"
              >
                {{ isEditing ? '保存' : '编辑' }}
              </el-button>
            </div>
          </template>

          <el-form 
            ref="memberFormRef" 
            :model="memberForm" 
            :rules="memberRules" 
            label-width="100px"
            :disabled="!isEditing"
          >
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="姓名" prop="name">
                  <el-input v-model="memberForm.name" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="性别" prop="gender">
                  <el-select v-model="memberForm.gender" placeholder="请选择性别">
                    <el-option label="男" value="male" />
                    <el-option label="女" value="female" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="年龄" prop="age">
                  <el-input-number v-model="memberForm.age" :min="1" :max="120" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="手机号" prop="phone">
                  <el-input v-model="memberForm.phone" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="会员卡类型" prop="membership_type">
                  <el-select v-model="memberForm.membership_type" placeholder="请选择会员卡类型">
                    <el-option label="月卡" value="monthly" />
                    <el-option label="季卡" value="quarterly" />
                    <el-option label="年卡" value="yearly" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="到期时间" prop="expiry_date">
                  <el-date-picker 
                    v-model="memberForm.expiry_date" 
                    type="date" 
                    placeholder="选择日期"
                    format="YYYY-MM-DD"
                    value-format="YYYY-MM-DD"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="健身目标" prop="fitness_goals">
              <el-input 
                v-model="memberForm.fitness_goals" 
                type="textarea" 
                :rows="3"
                placeholder="请输入健身目标"
              />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="mt-4">
          <template #header>
            <div class="card-header">
              <span>会员卡操作</span>
            </div>
          </template>

          <el-space wrap>
            <el-button type="success" @click="showRenewDialog" :disabled="isEditing">
              续费
            </el-button>
            <el-button type="warning" @click="showUpgradeDialog" :disabled="isEditing">
              升级
            </el-button>
            <el-button 
              :type="member.status === 'frozen' ? 'success' : 'danger'"
              @click="toggleStatus"
              :disabled="isEditing"
            >
              {{ member.status === 'frozen' ? '解冻' : '冻结' }}
            </el-button>
          </el-space>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>入场记录</span>
              <el-button type="text" @click="loadCheckInRecords">刷新</el-button>
            </div>
          </template>

          <el-timeline>
            <el-timeline-item 
              v-for="record in checkInRecords" 
              :key="record.id"
              :timestamp="record.check_in_time"
            >
              {{ record.check_in_time }} 入场
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- 续费对话框 -->
    <el-dialog v-model="renewDialogVisible" title="会员卡续费" width="400px">
      <el-form :model="renewForm" label-width="100px">
        <el-form-item label="续费时长">
          <el-select v-model="renewForm.duration">
            <el-option label="1个月" value="1" />
            <el-option label="3个月" value="3" />
            <el-option label="6个月" value="6" />
            <el-option label="12个月" value="12" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="renewForm.payment_method">
            <el-option label="现金" value="cash" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="微信" value="wechat" />
            <el-option label="银行卡" value="card" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRenew" :loading="loading">确认续费</el-button>
      </template>
    </el-dialog>

    <!-- 升级对话框 -->
    <el-dialog v-model="upgradeDialogVisible" title="会员卡升级" width="400px">
      <el-form :model="upgradeForm" label-width="100px">
        <el-form-item label="升级到">
          <el-select v-model="upgradeForm.new_type">
            <el-option label="季卡" value="quarterly" />
            <el-option label="年卡" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付方式">
          <el-select v-model="upgradeForm.payment_method">
            <el-option label="现金" value="cash" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="微信" value="wechat" />
            <el-option label="银行卡" value="card" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="upgradeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpgrade" :loading="loading">确认升级</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMemberStore } from '../stores/member'
import {
  getMemberDetail,
  updateMember,
  renewMembership,
  upgradeMembership,
  toggleMemberStatus,
  getMemberCheckInRecords
} from '../api/member'

const route = useRoute()
const router = useRouter()
const memberStore = useMemberStore()

const member = ref({})
const isEditing = ref(false)
const loading = ref(false)
const memberFormRef = ref(null)
const checkInRecords = ref([])

// 续费对话框
const renewDialogVisible = ref(false)
const renewForm = reactive({
  duration: '1',
  payment_method: 'cash'
})

// 升级对话框
const upgradeDialogVisible = ref(false)
const upgradeForm = reactive({
  new_type: 'quarterly',
  payment_method: 'cash'
})

// 表单数据
const memberForm = reactive({
  name: '',
  gender: '',
  age: null,
  phone: '',
  membership_type: '',
  expiry_date: '',
  fitness_goals: ''
})

// 表单验证规则
const memberRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  gender: [
    { required: true, message: '请选择性别', trigger: 'change' }
  ],
  age: [
    { required: true, message: '请输入年龄', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  membership_type: [
    { required: true, message: '请选择会员卡类型', trigger: 'change' }
  ],
  expiry_date: [
    { required: true, message: '请选择到期时间', trigger: 'change' }
  ]
}

// 计算属性
const pageTitle = computed(() => {
  return route.params.id ? '会员详情' : '新建会员'
})

// 方法
const goBack = () => {
  router.push('/members')
}

const getStatusType = (status) => {
  const types = {
    active: 'success',
    frozen: 'warning',
    expired: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: '活跃',
    frozen: '冻结',
    expired: '过期'
  }
  return texts[status] || '未知'
}

const toggleEdit = async () => {
  if (isEditing.value) {
    // 保存
    try {
      await memberFormRef.value.validate()
      loading.value = true
      await updateMember(route.params.id, memberForm)
      await loadMemberDetail()
      isEditing.value = false
      ElMessage.success('保存成功')
    } catch (error) {
      console.error('保存失败:', error)
      ElMessage.error('保存失败')
    } finally {
      loading.value = false
    }
  } else {
    // 进入编辑模式
    isEditing.value = true
  }
}

const loadMemberDetail = async () => {
  try {
    loading.value = true
    const response = await getMemberDetail(route.params.id)
    member.value = response.data
    Object.assign(memberForm, member.value)
  } catch (error) {
    console.error('加载会员详情失败:', error)
    ElMessage.error('加载会员详情失败')
  } finally {
    loading.value = false
  }
}

const loadCheckInRecords = async () => {
  try {
    const response = await getMemberCheckInRecords(route.params.id, { limit: 10 })
    checkInRecords.value = response.data.items || []
  } catch (error) {
    console.error('加载入场记录失败:', error)
  }
}

const showRenewDialog = () => {
  renewDialogVisible.value = true
}

const handleRenew = async () => {
  try {
    loading.value = true
    await renewMembership(route.params.id, renewForm)
    await loadMemberDetail()
    renewDialogVisible.value = false
    ElMessage.success('续费成功')
  } catch (error) {
    console.error('续费失败:', error)
    ElMessage.error('续费失败')
  } finally {
    loading.value = false
  }
}

const showUpgradeDialog = () => {
  upgradeDialogVisible.value = true
}

const handleUpgrade = async () => {
  try {
    loading.value = true
    await upgradeMembership(route.params.id, upgradeForm)
    await loadMemberDetail()
    upgradeDialogVisible.value = false
    ElMessage.success('升级成功')
  } catch (error) {
    console.error('升级失败:', error)
    ElMessage.error('升级失败')
  } finally {
    loading.value = false
  }
}

const toggleStatus = async () => {
  const action = member.value.status === 'frozen' ? '解冻' : '冻结'
  try {
    await ElMessageBox.confirm(
      `确定要${action}该会员吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    loading.value = true
    await toggleMemberStatus(route.params.id, {
      status: member.value.status === 'frozen' ? 'active' : 'frozen'
    })
    await loadMemberDetail()
    ElMessage.success(`${action}成功`)
  } catch (error) {
    if (error !== 'cancel') {
      console.error(`${action}失败:`, error)
      ElMessage.error(`${action}失败`)
    }
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  if (route.params.id) {
    loadMemberDetail()
    loadCheckInRecords()
  }
})
</script>

<style scoped>
.member-detail {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.ml-2 {
  margin-left: 8px;
}

.mt-4 {
  margin-top: 16px;
}
</style>