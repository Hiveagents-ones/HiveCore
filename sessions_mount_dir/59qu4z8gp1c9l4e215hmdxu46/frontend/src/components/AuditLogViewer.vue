<template>
  <div class="audit-log-viewer">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>会员审计日志</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索操作内容"
              style="width: 200px; margin-right: 10px"
              clearable
              @clear="handleSearchClear"
              @keyup.enter="fetchAuditLogs"
            />
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="handleDateChange"
            />
            <el-button type="primary" @click="fetchAuditLogs">查询</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="auditLogs"
        v-loading="loading"
        border
        style="width: 100%"
        height="calc(100vh - 280px)"
      >
        <el-table-column prop="timestamp" label="时间" width="180" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="120" />
        <el-table-column prop="action" label="操作类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getActionTagType(row.action)">
              {{ row.action }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="操作对象" />
        <el-table-column prop="details" label="操作详情" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalLogs"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getMemberAuditLogs } from '@/api/members';
import { ElMessage } from 'element-plus';

export default {
  name: 'AuditLogViewer',
  props: {
    memberId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const auditLogs = ref([]);
    const loading = ref(false);
    const searchQuery = ref('');
    const dateRange = ref([]);
    const currentPage = ref(1);
    const pageSize = ref(20);
    const totalLogs = ref(0);

    const fetchAuditLogs = async () => {
      try {
        loading.value = true;
        const params = {
          page: currentPage.value,
          size: pageSize.value,
          search: searchQuery.value,
        };

        if (dateRange.value && dateRange.value.length === 2) {
          params.start_date = dateRange.value[0].toISOString().split('T')[0];
          params.end_date = dateRange.value[1].toISOString().split('T')[0];
        }

        const response = await getMemberAuditLogs(props.memberId, params);
        auditLogs.value = response.data.items;
        totalLogs.value = response.data.total;
      } catch (error) {
        ElMessage.error('获取审计日志失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    const handlePageChange = (page) => {
      currentPage.value = page;
      fetchAuditLogs();
    };

    const handleSizeChange = (size) => {
      pageSize.value = size;
      currentPage.value = 1;
      fetchAuditLogs();
    };

    const handleDateChange = () => {
      currentPage.value = 1;
      fetchAuditLogs();
    };

    const handleSearchClear = () => {
      currentPage.value = 1;
      fetchAuditLogs();
    };

    const formatDateTime = (timestamp) => {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleString();
    };

    const getActionTagType = (action) => {
      switch (action) {
        case 'CREATE':
          return 'success';
        case 'UPDATE':
          return 'warning';
        case 'DELETE':
          return 'danger';
        default:
          return 'info';
      }
    };

    onMounted(() => {
      fetchAuditLogs();
    });

    return {
      auditLogs,
      loading,
      searchQuery,
      dateRange,
      currentPage,
      pageSize,
      totalLogs,
      fetchAuditLogs,
      handlePageChange,
      handleSizeChange,
      handleDateChange,
      handleSearchClear,
      formatDateTime,
      getActionTagType,
    };
  },
};
</script>

<style scoped>
.audit-log-viewer {
  height: 100%;
}

.box-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.pagination-container {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}
</style>