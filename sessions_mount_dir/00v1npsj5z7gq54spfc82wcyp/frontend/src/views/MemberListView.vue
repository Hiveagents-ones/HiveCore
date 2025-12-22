<template>
  <div class="member-list-view">
    <h1>{{ t('member.management') }}</h1>
    
    <div class="action-bar">
      <el-select 
        v-model="locale" 
        @change="switchLanguage"
        style="width: 100px; margin-left: 20px"
      >
        <el-option
          v-for="lang in availableLocales"
          :key="lang"
          :label="lang.toUpperCase()"
          :value="lang"
        />
      </el-select>
      <el-button type="primary" @click="showCreateDialog = true">{{ t('member.addMember') }}</el-button>
      <el-input 
        v-model="searchQuery" 
        :placeholder="t('member.searchPlaceholder')" 
        style="width: 300px; margin-left: 20px" 
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button icon="el-icon-search" @click="handleSearch" />
        </template>
      </el-input>
    </div>
    
    <el-table 
      :data="members" 
      border 
      style="width: 100%; margin-top: 20px"
      v-loading="loading"
    >
      <el-table-column prop="id" :label="t('member.id')" width="80" />
      <el-table-column prop="name" :label="t('member.name')" />
      <el-table-column prop="phone" :label="t('member.phone')" />
      <el-table-column prop="membership_type" :label="t('member.membershipType')" />
      <el-table-column prop="join_date" :label="t('member.joinDate')" />
      <el-table-column :label="t('common.actions')" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">{{ t('common.edit') }}</el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(scope.row.id)"
          >{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 性能监控展示 -->
    <div class="performance-metrics" v-if="performanceMetrics.length > 0" v-loading="chartLoading">
    <div class="metric-chart">
      <h4>{{ t('performance.chartTitle') }}</h4>
      <div ref="chartContainer" style="height: 180px; width: 100%;"></div>
    </div>
    <div class="system-metrics" v-if="metrics.length > 0">
      <h3>{{ t('performance.systemMetrics') }}</h3>
      <div v-for="metric in metrics" :key="metric.name" class="metric-item">
        <span class="metric-label">{{ metric.name }}:</span>
        <span>{{ metric.value }}ms (avg: {{ metric.avg }}ms)</span>
      </div>
    </div>
      <h3>{{ t('performance.metrics') }}</h3>
      <div v-for="metric in performanceMetrics" :key="metric.name" class="metric-item">
        <span class="metric-label">{{ metric.name }}:</span>
        <span>{{ metric.duration }}ms</span>
      </div>
    </div>
    
    <!-- 新增/编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="dialogTitle" 
      width="30%"
      @closed="resetForm"
,
      performanceMetrics
    >
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item :label="t('member.name')" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="t('member.phone')" prop="phone">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item :label="t('member.membershipType')" prop="membership_type">
          <el-select v-model="form.membership_type" placeholder="请选择">
            <el-option 
              v-for="item in membershipTypes" 
              :key="item.value" 
              :label="item.label" 
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { usePerformance } from '@/composables/performance';
import * as echarts from 'echarts';
import { useMetrics } from '@/composables/metrics';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import memberApi from '@/api/member';

export default {
  setup() {
    const members = ref([]);
    const loading = ref(false);
    const searchQuery = ref('');
    const showDialog = ref(false);
    const showCreateDialog = ref(false);
    const form = ref({
      id: null,
      name: '',
      phone: '',
      membership_type: ''
    });
    const formRef = ref(null);
    
    const membershipTypes = [
      { value: 'standard', label: '标准会员' },
      { value: 'premium', label: '高级会员' },
      { value: 'vip', label: 'VIP会员' }
    ];
    
    const rules = {
      name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
      phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
      membership_type: [{ required: true, message: '请选择会员类型', trigger: 'change' }]
    };
    
    const { t } = useI18n();
    const dialogTitle = ref(t('member.addMember'));
const { performanceMetrics, startTracking, endTracking } = usePerformance();
const { metrics, recordMetric } = useMetrics();
const performanceChart = ref(null);
    const chartContainer = ref(null);
    let chartInstance = null;
const { locale } = useI18n();
    const chartLoading = ref(false);
const availableLocales = ['en', 'zh'];
const switchLanguage = (lang) => {
  locale.value = lang;
  localStorage.setItem('locale', lang);
};
    
    const fetchMembers = async () => {
      chartLoading.value = true;
    startTracking('fetch_members');
      try {
        loading.value = true;
        const response = await memberApi.getAllMembers();
        members.value = response.data;
      } catch (error) {
        ElMessage.error(t('member.fetchFailed'));
      } finally {
        loading.value = false;
chartLoading.value = false;
    endTracking('search_members');
    endTracking('fetch_members');
    performanceMetrics.value.forEach(metric => {
      if (chartInstance) {
        chartInstance.dispose();
      }
      
      if (chartContainer.value) {
        chartInstance = echarts.init(chartContainer.value);
        chartInstance.setOption({
          tooltip: {
            trigger: 'item'
          },
          legend: {
            top: '5%',
            left: 'center'
          },
          series: [
            {
              name: 'Performance Metrics',
              type: 'pie',
              radius: ['40%', '70%'],
              avoidLabelOverlap: false,
              itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
              },
              label: {
                show: false,
                position: 'center'
              },
              emphasis: {
                label: {
                  show: true,
                  fontSize: '18',
                  fontWeight: 'bold'
                }
              },
              labelLine: {
                show: false
              },
              data: performanceMetrics.value.map(metric => ({
                value: metric.duration,
                name: metric.name
              }))
            }
          ]
        });
      }
      console.log(`[Performance] ${metric.name}: ${metric.duration}ms`);
      recordMetric(metric.name, metric.duration);
    });
      }
    };
    
    const handleSearch = async () => {
    startTracking('search_members');
      try {
        loading.value = true;
        const response = await memberApi.searchMembers({ q: searchQuery.value });
        members.value = response.data;
      } catch (error) {
        ElMessage.error(t('member.searchFailed'));
      } finally {
        loading.value = false;
      }
    };
    
    const handleEdit = (row) => {
      form.value = { ...row };
      dialogTitle.value = '编辑会员';
      showDialog.value = true;
    };
    
    const handleDelete = (id) => {
      ElMessageBox.confirm(t('member.deleteConfirm'), t('common.notice'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }).then(async () => {
        try {
          await memberApi.deleteMember(id);
          ElMessage.success(t('member.deleteSuccess'));
          fetchMembers();
        } catch (error) {
          ElMessage.error(t('member.deleteFailed'));
        }
      }).catch(() => {});
    };
    
    const submitForm = async () => {
      try {
        await formRef.value.validate();
        
        if (form.value.id) {
          await memberApi.updateMember(form.value.id, form.value);
          ElMessage.success(t('member.updateSuccess'));
        } else {
          await memberApi.createMember(form.value);
          ElMessage.success(t('member.createSuccess'));
        }
        
        showDialog.value = false;
        fetchMembers();
      } catch (error) {
        if (!error.response) {
          // 表单验证错误
          return;
        }
        ElMessage.error(error.response.data.message || t('member.operationFailed'));
        recordMetric('form_submit_error', 1);
      }
    };
    
    const resetForm = () => {
      form.value = {
        id: null,
        name: '',
        phone: '',
        membership_type: ''
      };
      if (formRef.value) {
        formRef.value.resetFields();
      }
    };
    
    onMounted(() => {
    window.addEventListener('resize', () => {
      if (chartInstance) {
        chartInstance.resize();
      }
    });
      fetchMembers();
    });
    
    return {
      chartContainer,
      locale,
      availableLocales,
      switchLanguage,
      members,
      loading,
      searchQuery,
      showDialog,
      showCreateDialog,
      form,
      formRef,
      membershipTypes,
      rules,
      dialogTitle,
      handleSearch,
      handleEdit,
      handleDelete,
      submitForm,
      resetForm
    };
  }
};
</script>

<style scoped>
  .performance-metrics {
    margin-top: 20px;
    padding: 15px;
    background-color: #f5f7fa;
    border-radius: 4px;
  }
  
  .metric-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  
  .metric-label {
    font-weight: bold;
    min-width: 150px;
    display: inline-block;
  }
.member-list-view {
  padding: 20px;
}

.action-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

  .metric-chart {
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    position: relative;
    margin-top: 15px;
    height: 200px;
    background-color: white;
    border-radius: 4px;
    padding: 10px;
  }