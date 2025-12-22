<template>
  <div class="coach-leave-container">
    <h1>教练请假审批</h1>
    <div v-if="pendingLeaveRequests.length > 0" class="pending-alert">
      <el-alert
        title="有待审批的请假申请"
        type="warning"
        :closable="false"
        show-icon
      >
        当前有 {{ pendingLeaveRequests.length }} 条待审批请假申请
      </el-alert>
    </div>
    
    <div class="leave-actions">
      <el-button type="primary" @click="showAddDialog">申请请假</el-button>
    </div>
    
    <el-table :data="leaveRequests" style="width: 100%" border>
      <el-table-column prop="coachName" label="教练姓名" width="120" />
      <el-table-column prop="startDate" label="开始日期" width="120" />
      <el-table-column prop="endDate" label="结束日期" width="120" />
      <el-table-column prop="reason" label="请假原因" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="getStatusTagType(scope.row.status)">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button 
            size="small" 
            type="success" 
            @click="handleApprove(scope.row)"
            :disabled="!['pending', 'first_approved'].includes(scope.row.status)"
          >
            {{ scope.row.status === 'pending' ? '初审通过' : '最终批准' }}
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleReject(scope.row)"
            :disabled="scope.row.status !== 'pending'"
          >
            拒绝
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-dialog v-model="dialogVisible" title="请假申请" width="50%">
      <el-form :model="leaveForm" label-width="100px">
        <el-form-item label="开始日期" required>
          <el-date-picker 
            v-model="leaveForm.startDate" 
            type="date" 
            placeholder="选择开始日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="结束日期" required>
          <el-date-picker 
            v-model="leaveForm.endDate" 
            type="date" 
            placeholder="选择结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="请假原因" required>
          <el-input 
            v-model="leaveForm.reason" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入请假原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitLeaveRequest">提交</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLeaveRequests, approveLeaveRequest, rejectLeaveRequest, createLeaveRequest, getPendingLeaveRequests } from '../api/coach'

const leaveRequests = ref([])
const pendingLeaveRequests = ref([])
const dialogVisible = ref(false)
const leaveForm = ref({
  startDate: '',
  endDate: '',
  reason: ''
})

const fetchLeaveRequests = async () => {
  try {
    const [allResponse, pendingResponse] = await Promise.all([
      getLeaveRequests(),
      getPendingLeaveRequests()
    ])
    leaveRequests.value = allResponse.data
    pendingLeaveRequests.value = pendingResponse.data
  } catch (error) {
    ElMessage.error('获取请假列表失败: ' + error.message)
  }
}

const showAddDialog = () => {
  leaveForm.value = {
    startDate: '',
    endDate: '',
    reason: ''
  }
  dialogVisible.value = true
}

const submitLeaveRequest = async () => {
  try {
    if (!leaveForm.value.startDate || !leaveForm.value.endDate || !leaveForm.value.reason) {
      ElMessage.warning('请填写完整的请假信息')
      return
    }
    
    await createLeaveRequest(leaveForm.value)
    ElMessage.success('请假申请提交成功')
    dialogVisible.value = false
    fetchLeaveRequests()
  } catch (error) {
    ElMessage.error('提交请假申请失败: ' + error.message)
  }
}

const handleApprove = async (row) => {
  try {
    await ElMessageBox.confirm('确定要批准该请假申请吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await approveLeaveRequest(row.id)
    ElMessage.success('已批准请假申请')
    fetchLeaveRequests()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批准请假失败: ' + error.message)
    }
  }
}

const handleReject = async (row) => {
  try {
    await ElMessageBox.confirm('确定要拒绝该请假申请吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await rejectLeaveRequest(row.id)
    ElMessage.success('已拒绝请假申请')
    fetchLeaveRequests()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('拒绝请假失败: ' + error.message)
    }
  }
}

const getStatusTagType = (status) => {
  switch (status) {
    case 'approved': return 'success'
    case 'rejected': return 'danger'
    case 'pending': return 'warning'
    case 'first_approved': return 'primary'
    case 'final_approved': return 'success'
    default: return 'info'
  }
}

onMounted(() => {
  fetchLeaveRequests()
})
</script>

<style scoped>
.coach-leave-container {
  padding: 20px;
}

.leave-actions {
}

.pending-alert {
  margin-bottom: 20px;
}
  margin-bottom: 20px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const handleApprove = async (row) => {
  try {
    const action = row.status === 'pending' ? '初审通过' : '最终批准'
    await ElMessageBox.confirm(`确定要${action}该请假申请吗?`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await approveLeaveRequest(row.id, row.status)
    ElMessage.success(`已${action}请假申请`)
    fetchLeaveRequests()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`${action}请假失败: ` + error.message)
    }
  }
}