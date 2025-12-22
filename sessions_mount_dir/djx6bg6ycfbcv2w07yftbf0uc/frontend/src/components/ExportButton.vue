<template>
  <div class="export-button">
    <el-dropdown @command="handleExport" trigger="click">
      <el-button type="primary" :loading="exporting">
        <el-icon><Download /></el-icon>
        导出数据
        <el-icon class="el-icon--right"><ArrowDown /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="excel">
            <el-icon><Document /></el-icon>
            导出为 Excel
          </el-dropdown-item>
          <el-dropdown-item command="csv">
            <el-icon><Tickets /></el-icon>
            导出为 CSV
          </el-dropdown-item>
          <el-dropdown-item command="pdf">
            <el-icon><Files /></el-icon>
            导出为 PDF
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, ArrowDown, Document, Tickets, Files } from '@element-plus/icons-vue'
import { exportAnalytics } from '@/services/analytics'

const props = defineProps({
  dateRange: {
    type: Array,
    required: true
  },
  chartData: {
    type: Object,
    required: true
  }
})

const exporting = ref(false)

const handleExport = async (format) => {
  if (exporting.value) return
  
  exporting.value = true
  try {
    const response = await exportAnalytics({
      format,
      dateRange: props.dateRange,
      data: props.chartData
    })
    
    // 创建下载链接
    const blob = new Blob([response.data], {
      type: getContentType(format)
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `analytics_${new Date().toISOString().split('T')[0]}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

const getContentType = (format) => {
  const types = {
    excel: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    csv: 'text/csv',
    pdf: 'application/pdf'
  }
  return types[format] || 'application/octet-stream'
}
</script>

<style scoped>
.export-button {
  display: inline-block;
}

.el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>