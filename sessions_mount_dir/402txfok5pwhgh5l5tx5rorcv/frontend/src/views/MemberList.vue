<template>
  <div class="member-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>会员列表</span>
          <el-button type="primary" @click="handleAdd">新增会员</el-button>
        </div>
      </template>

      <!-- 搜索和筛选区域 -->
      <div class="filter-container">
        <el-form :inline="true" :model="queryParams" class="demo-form-inline">
          <el-form-item label="姓名">
            <el-input v-model="queryParams.name" placeholder="请输入姓名" clearable @keyup.enter="handleQuery" />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="queryParams.contact" placeholder="请输入联系方式" clearable @keyup.enter="handleQuery" />
          </el-form-item>
          <el-form-item label="会员等级">
            <el-select v-model="queryParams.level" placeholder="请选择" clearable>
              <el-option label="普通会员" value="normal" />
              <el-option label="银卡会员" value="silver" />
              <el-option label="金卡会员" value="gold" />
              <el-option label="钻石会员" value="diamond" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryParams.status" placeholder="请选择" clearable>
              <el-option label="活跃" value="active" />
              <el-option label="冻结" value="frozen" />
              <el-option label="过期" value="expired" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleQuery">查询</el-button>
            <el-button @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 表格区域 -->
      <el-table v-loading="loading" :data="memberList" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="contact" label="联系方式" width="150" />
        <el-table-column prop="level" label="会员等级" width="120">
          <template #default="scope">
            <el-tag :type="getLevelTagType(scope.row.level)">{{ getLevelText(scope.row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>

        <!-- 动态字段列 -->
        <el-table-column
          v-for="field in dynamicFields"
          :key="field.key"
          :prop="`metadata.${field.key}`"
          :label="field.label"
          width="120"
        >
          <template #default="scope">
            <span v-if="field.type === 'date'">{{ formatDate(scope.row.metadata[field.key]) }}</span>
            <span v-else>{{ scope.row.metadata[field.key] || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="handleView(scope.row)">查看</el-button>
            <el-button link type="primary" size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="handleViewRecords(scope.row)">入场记录</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页区域 -->
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="cancelDialog"
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
        <el-form-item label="联系方式" prop="contact">
          <el-input v-model="memberForm.contact" placeholder="请输入联系方式" />
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
          <el-button @click="cancelDialog">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getMembers, createMember, updateMember, deleteMember } from '@/api/members'

const router = useRouter()

// 防抖函数
const debounce = (fn, delay) => {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

// 节流函数
const throttle = (fn, delay) => {
  let last = 0
  return function (...args) {
    const now = Date.now()
    if (now - last > delay) {
      fn.apply(this, args)
      last = now
    }
  }
}

// 查询参数
const queryParams = reactive({
  page: 1,
  size: 10,
  name: '',
  contact: '',
  level: '',
  status: ''
})

// 表格数据
const loading = ref(false)
const memberList = ref([])
const total = ref(0)

// 动态字段配置
const dynamicFields = ref([
  { key: 'birthday', label: '生日', type: 'date' },
  { key: 'address', label: '地址', type: 'string' },
  { key: 'points', label: '积分', type: 'number' }
])

// 对话框相关
const dialogVisible = ref(false)
const dialogTitle = ref('')
const memberFormRef = ref()
const memberForm = reactive({
  id: null,
  name: '',
  contact: '',
  level: '',
  status: ''
})

// 表单验证规则
const memberRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  contact: [{ required: true, message: '请输入联系方式', trigger: 'blur' }],
  level: [{ required: true, message: '请选择会员等级', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

// 获取会员列表
const getList = async () => {
  loading.value = true
  try {
    const params = {
      skip: (queryParams.page - 1) * queryParams.size,
      limit: queryParams.size,
      name: queryParams.name || undefined,
      contact: queryParams.contact || undefined,
      level: queryParams.level || undefined,
      status: queryParams.status || undefined
    }
    const response = await getMembers(params)
    memberList.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取会员列表失败')
  } finally {
    loading.value = false
  }
}

// 查询（使用防抖）
const handleQuery = debounce(() => {
  queryParams.page = 1
  getList()
}, 300)

// 重置查询
const resetQuery = () => {
  queryParams.name = ''
  queryParams.contact = ''
  queryParams.level = ''
  queryParams.status = ''
  handleQuery()
}

// 分页（使用节流）
const handleSizeChange = throttle((val) => {
  queryParams.size = val
  getList()
}, 500)

const handleCurrentChange = throttle((val) => {
  queryParams.page = val
  getList()
}, 500)

// 新增会员
const handleAdd = () => {
  dialogTitle.value = '新增会员'
  dialogVisible.value = true
  resetForm()
}

// 查看会员
const handleView = (row) => {
  router.push(`/members/${row.id}`)
}

// 编辑会员
const handleEdit = (row) => {
  dialogTitle.value = '编辑会员'
  dialogVisible.value = true
  Object.assign(memberForm, row)
}

// 查看入场记录
const handleViewRecords = (row) => {
  router.push(`/members/${row.id}/records`)
}

// 删除会员
const handleDelete = (row) => {
  ElMessageBox.confirm('确认要删除该会员吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteMember(row.id)
      ElMessage.success('删除成功')
      getList()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 提交表单
const submitForm = async () => {
  await memberFormRef.value.validate()
  try {
    if (memberForm.id) {
      await updateMember(memberForm.id, memberForm)
      ElMessage.success('更新成功')
    } else {
      await createMember(memberForm)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    getList()
  } catch (error) {
    ElMessage.error(memberForm.id ? '更新失败' : '创建失败')
  }
}

// 取消对话框
const cancelDialog = () => {
  dialogVisible.value = false
  resetForm()
}

// 重置表单
const resetForm = () => {
  memberForm.id = null
  memberForm.name = ''
  memberForm.contact = ''
  memberForm.level = ''
  memberForm.status = ''
  if (memberFormRef.value) {
    memberFormRef.value.resetFields()
  }
}

// 辅助函数
const getLevelTagType = (level) => {
  const map = {
    normal: '',
    silver: 'info',
    gold: 'warning',
    diamond: 'success'
  }
  return map[level] || ''
}

const getLevelText = (level) => {
  const map = {
    normal: '普通会员',
    silver: '银卡会员',
    gold: '金卡会员',
    diamond: '钻石会员'
  }
  return map[level] || level
}

const getStatusTagType = (status) => {
  const map = {
    active: 'success',
    frozen: 'warning',
    expired: 'danger'
  }
  return map[status] || ''
}

const getStatusText = (status) => {
  const map = {
    active: '活跃',
    frozen: '冻结',
    expired: '过期'
  }
  return map[status] || status
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

// 初始化
onMounted(() => {
  getList()
  watchQueryChanges()
})
</script>

<style scoped>
.member-list {
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
</style>