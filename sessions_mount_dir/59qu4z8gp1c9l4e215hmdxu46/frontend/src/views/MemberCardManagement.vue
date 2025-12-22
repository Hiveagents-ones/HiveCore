<template>
  <div class="member-card-management">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>会员卡管理</span>
          <el-button type="primary" @click="fetchMemberCards" :loading="loading">刷新</el-button>
        </div>
      </template>

      <el-table :data="memberCards" style="width: 100%" v-loading="loading">
        <el-table-column prop="card_number" label="卡号" width="180">
          <template #default="scope">
            {{ scope.row.card_number.replace(/\d(?=\d{4})/g, '*') }} <el-tooltip content="完整卡号: {{scope.row.card_number}}" placement="top"><el-icon><Warning /></el-icon></el-tooltip>
            <el-popover
              placement="top"
              trigger="click"
              width="300"
            >
              <template #reference>
                <el-button size="small" type="text">查看完整卡号</el-button>
              </template>
              <div style="text-align: center; padding: 10px">
                <p>完整卡号 (请勿截图或拍照)</p>
                <p style="font-size: 18px; font-weight: bold; margin: 10px 0">{{ scope.row.card_number }}</p>
                <el-button type="primary" size="small" @click="copyToClipboard(scope.row.card_number)">复制卡号</el-button>
              </div>
            </el-popover>
          </template>
        </el-table-column>
        <el-table-column prop="member.name" label="会员姓名" width="180" />
        <el-table-column prop="member.phone" label="手机号" width="180">
          <template #default="scope">
            {{ scope.row.member.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expiry_date" label="过期日期" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDeactivate(scope.row)"
              v-if="scope.row.status === 'active'"
            >
              停用
            </el-button>
            <el-button
              size="small"
              type="success"
              @click="handleActivate(scope.row)"
              v-else
            >
              激活
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog v-model="dialogVisible" title="编辑会员卡" width="30%">
        <el-form :model="currentCard" label-width="100px">
          <el-form-item label="卡号">
            <el-input v-model="currentCard.card_number" disabled />
          </el-form-item>
          <el-form-item label="会员姓名">
            <el-input v-model="currentCard.member.name" disabled />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="currentCard.status" placeholder="请选择状态">
              <el-option label="激活" value="active" />
              <el-option label="停用" value="inactive" />
              <el-option label="过期" value="expired" />
            </el-select>
          </el-form-item>
          <el-form-item label="过期日期">
            <el-date-picker
              v-model="currentCard.expiry_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSave">保存</el-button>
          </span>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMemberCards, updateMemberCard } from '@/api'

const memberCards = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentCard = ref({
  id: null,
  card_number: '',
  member: {
    name: ''
  },
  status: '',
  expiry_date: ''
})

const fetchMemberCards = async () => {
  try {
    loading.value = true
    const response = await getMemberCards()
    memberCards.value = response.data
  } catch (error) {
    ElMessage.error('获取会员卡列表失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const getStatusTagType = (status) => {
  switch (status) {
    case 'active':
      return 'success'
    case 'inactive':
      return 'danger'
    case 'expired':
      return 'warning'
    default:
      return 'info'
  }
}

const handleEdit = (card) => {
  currentCard.value = JSON.parse(JSON.stringify(card))
  dialogVisible.value = true
}

const handleSave = async () => {
  if (currentCard.value.status === 'active' && new Date(currentCard.value.expiry_date) < new Date()) {
    try {
      await ElMessageBox.confirm('您正在激活一张已过期的会员卡，这可能导致系统异常。确定要继续吗?', '安全警告', {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        type: 'error'
      })
    } catch (error) {
      return
    }
  }
  if (!currentCard.value.expiry_date) {
    ElMessage.error('请设置过期日期')
    return
  }
  try {
    await ElMessageBox.confirm('确定要保存会员卡修改吗?\n\n卡号: ' + currentCard.value.card_number + '\n状态将修改为: ' + currentCard.value.status + '\n过期日期: ' + currentCard.value.expiry_date, '确认修改', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await updateMemberCard(currentCard.value.id, {
      status: currentCard.value.status,
      expiry_date: currentCard.value.expiry_date
    })
    ElMessage.success('会员卡更新成功')
    dialogVisible.value = false
    fetchMemberCards()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('更新会员卡失败: ' + error.message)
    }
  }
}

const handleActivate = async (card) => {
  if (card.expiry_date && new Date(card.expiry_date) < new Date()) {
    try {
      await ElMessageBox.confirm('该卡已过期，激活后需要更新过期日期。过期卡激活可能导致系统异常，请谨慎操作！', '安全警告', {
        confirmButtonText: '继续激活',
        cancelButtonText: '取消',
        type: 'error'
      })
    } catch (error) {
      return
    }
  }
  if (card.expiry_date && new Date(card.expiry_date) < new Date()) {
    await ElMessageBox.confirm('该卡已过期，激活后需要更新过期日期', '过期警告', {
      confirmButtonText: '继续激活',
      cancelButtonText: '取消',
      type: 'warning'
    })
  }

    await updateMemberCard(card.id, { status: 'active' })
    await ElMessageBox.alert('会员卡激活成功！请提醒会员及时检查卡片状态。', '激活成功', {
      confirmButtonText: '确定',
      type: 'success'
    })
    ElMessage.success('会员卡已激活')
    fetchMemberCards()
  } catch (error) {
    ElMessage.error('激活会员卡失败: ' + error.message)
  }
}

const handleDeactivate = async (card) => {
const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text)
    .then(() => {
      ElMessage.success('已复制到剪贴板')
    })
    .catch(() => {
      ElMessage.error('复制失败，请手动复制')
    })
}
  try {
    await ElMessageBox.confirm('确定要停用此会员卡吗?\n\n卡号: ' + card.card_number, '确认停用', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await updateMemberCard(card.id, { status: 'inactive' })
    ElMessage.success('会员卡已停用')
    fetchMemberCards()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('停用会员卡失败: ' + error.message)
    }
  }
}

onMounted(() => {
  fetchMemberCards()
})
</script>

<style scoped>
.member-card-management {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>