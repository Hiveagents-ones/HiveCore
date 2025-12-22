<template>
  <div class="detail-data-table">
    <div class="table-header">
      <div class="title">
        <slot name="title">
          <h3>{{ title }}</h3>
        </slot>
      </div>
      <div class="actions">
        <el-button
          type="primary"
          size="small"
          @click="handleExport"
          :loading="exporting"
        >
          导出数据
        </el-button>
      </div>
    </div>

    <el-table
      :data="tableData"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      @sort-change="handleSortChange"
      :default-sort="defaultSort"
    >
      <el-table-column
        v-for="column in columns"
        :key="column.prop"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :sortable="column.sortable"
        :formatter="column.formatter"
        :align="column.align || 'left'"
      >
        <template #default="scope" v-if="column.slot">
          <slot :name="column.slot" :row="scope.row" :index="scope.$index"></slot>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="showPagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  title: {
    type: String,
    default: '数据明细'
  },
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  total: {
    type: Number,
    default: 0
  },
  currentPage: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 10
  },
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  },
  showPagination: {
    type: Boolean,
    default: true
  },
  defaultSort: {
    type: Object,
    default: () => ({ prop: '', order: '' })
  }
})

const emit = defineEmits(['update:currentPage', 'update:pageSize', 'sort-change', 'export'])

const tableData = computed(() => props.data)
const currentPage = ref(props.currentPage)
const pageSize = ref(props.pageSize)
const exporting = ref(false)

watch(() => props.currentPage, (newVal) => {
  currentPage.value = newVal
})

watch(() => props.pageSize, (newVal) => {
  pageSize.value = newVal
})

const handleSizeChange = (val) => {
  pageSize.value = val
  emit('update:pageSize', val)
  emit('update:currentPage', 1)
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  emit('update:currentPage', val)
}

const handleSortChange = ({ prop, order }) => {
  emit('sort-change', { prop, order })
}

const handleExport = async () => {
  try {
    exporting.value = true
    emit('export')
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  currentPage.value = props.currentPage
  pageSize.value = props.pageSize
})
</script>

<style scoped>
.detail-data-table {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-header .title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table .cell) {
  padding: 0 10px;
}
</style>