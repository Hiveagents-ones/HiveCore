<template>
  <div class="member-detail-container" v-if="member.id">
    <div v-if="loading" class="loading-spinner">
      <q-spinner color="primary" size="3em" />
    </div>
    
    <div v-else>
      <div class="member-header">
        <h2>会员详情</h2>
        <q-btn 
          color="primary" 
          label="编辑" 
          @click="editMode = true" 
          v-if="!editMode"
        />
      </div>
      
      <q-card class="member-card">
        <q-card-section>
          <div class="row q-mb-md">
            <div class="col-12 col-md-6">
              <q-input 
                v-model="member.name" 
                label="姓名" 
                outlined 
                :readonly="!editMode"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-input 
                v-model="member.phone" 
                label="电话" 
                outlined 
                :readonly="!editMode"
              />
            </div>
          </div>
          
          <div class="row q-mb-md">
            <div class="col-12 col-md-6">
              <q-input 
                v-model="member.email" 
                label="邮箱" 
                outlined 
                :readonly="!editMode"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select 
                v-model="member.card_status" 
                :options="cardStatusOptions" 
                label="会员卡状态" 
                outlined 
                :readonly="!editMode"
              />
            </div>
          </div>
        </q-card-section>
        
        <q-card-actions align="right" v-if="editMode">
          <q-btn flat label="取消" @click="cancelEdit" />
          <q-btn color="primary" label="保存" @click="saveMember" />
        </q-card-actions>
      </q-card>
      
      <div class="payment-history q-mt-lg">
        <h3>消费记录</h3>
        <div class="text-caption text-grey q-mb-sm">最近30天消费记录</div>
        <q-table
          :rows="payments"
          :columns="paymentColumns"
          row-key="id"
          :loading="paymentLoading"
          flat
          bordered
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { useQuasar } from 'quasar'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const memberId = route.params.id
const loading = ref(true)
const editMode = ref(false)
const member = ref({
  id: '',
  name: '',
  phone: '',
  email: '',
  card_status: ''
})

const originalMember = ref({})
const cardStatusOptions = [
  { label: '活跃', value: 'active' },
  { label: '已过期', value: 'expired' },
  { label: '已暂停', value: 'suspended' },
  { label: '已取消', value: 'canceled' }
]

// Payment history
const payments = ref([])
const paymentLoading = ref(false)
const paymentColumns = [
  { name: 'course', label: '课程', field: 'course_name', align: 'left' },
  { name: 'id', label: 'ID', field: 'id', align: 'left' },
  { name: 'amount', label: '金额', field: 'amount', align: 'left' },
  { name: 'payment_date', label: '支付日期', field: 'payment_date', align: 'left' },
  { name: 'payment_method', label: '支付方式', field: 'payment_method', align: 'left' },
  { name: 'status', label: '状态', field: 'status', align: 'left' }
]

const fetchMember = async () => {
  // 获取会员详情
  try {
    loading.value = true
    const response = await api.get(`/members/${memberId}`)
    member.value = response.data
    originalMember.value = { ...response.data }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '获取会员信息失败'
    })
    router.push('/members')
  } finally {
    loading.value = false
  }
}

const fetchPayments = async () => {
  // 获取会员消费记录
  try {
    paymentLoading.value = true
    const response = await api.get(`/members/${memberId}/payments`)
    payments.value = response.data
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '获取消费记录失败'
    })
  } finally {
    paymentLoading.value = false
  }
}

const saveMember = async () => {
  try {
    await api.put(`/members/${memberId}`, member.value)
    $q.notify({
      type: 'positive',
      message: '会员信息已更新'
    })
    editMode.value = false
    originalMember.value = { ...member.value }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: '更新会员信息失败'
    })
  }
}

const cancelEdit = () => {
  member.value = { ...originalMember.value }
  editMode.value = false
}

onMounted(() => {
  fetchMember()
  fetchPayments()
})
</script>

<style scoped>
.member-detail-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.member-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.member-card {
  margin-bottom: 30px;
}

.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}
</style>