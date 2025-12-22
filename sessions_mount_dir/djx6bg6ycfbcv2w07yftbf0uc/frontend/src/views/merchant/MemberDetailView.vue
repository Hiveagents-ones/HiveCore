<template>
  <div class="member-detail-view">
    <div class="page-header">
      <el-button @click="$router.go(-1)" icon="el-icon-arrow-left">返回</el-button>
      <h2>会员详情</h2>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <!-- 会员基本信息 -->
      <el-col :span="8">
        <el-card class="member-info-card">
          <div slot="header" class="clearfix">
            <span>基本信息</span>
            <el-button 
              style="float: right; padding: 3px 0" 
              type="text" 
              @click="editMode = !editMode"
            >
              {{ editMode ? '取消' : '编辑' }}
            </el-button>
          </div>
          
          <div class="member-avatar">
            <el-avatar :size="80" :src="member.avatar || ''">
              {{ member.name ? member.name.charAt(0) : 'M' }}
            </el-avatar>
          </div>
          
          <el-form :model="member" label-width="80px" v-if="member">
            <el-form-item label="姓名">
              <el-input v-if="editMode" v-model="member.name" />
              <span v-else>{{ member.name }}</span>
            </el-form-item>
            
            <el-form-item label="手机号">
              <el-input v-if="editMode" v-model="member.phone" />
              <span v-else>{{ member.phone }}</span>
            </el-form-item>
            
            <el-form-item label="邮箱">
              <el-input v-if="editMode" v-model="member.email" />
              <span v-else>{{ member.email }}</span>
            </el-form-item>
            
            <el-form-item label="生日">
              <el-date-picker 
                v-if="editMode" 
                v-model="member.birthday" 
                type="date" 
                placeholder="选择日期"
              />
              <span v-else>{{ member.birthday }}</span>
            </el-form-item>
            
            <el-form-item label="性别">
              <el-select v-if="editMode" v-model="member.gender">
                <el-option label="男" value="male" />
                <el-option label="女" value="female" />
                <el-option label="其他" value="other" />
              </el-select>
              <span v-else>{{ genderText }}</span>
            </el-form-item>
            
            <el-form-item label="注册时间">
              <span>{{ member.created_at }}</span>
            </el-form-item>
            
            <el-form-item v-if="editMode">
              <el-button type="primary" @click="saveMember">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 会员标签 -->
        <el-card class="member-tags-card">
          <div slot="header" class="clearfix">
            <span>会员标签</span>
          </div>
          <TagManager 
            :tags="member.tags || []" 
            @update="updateTags"
          />
        </el-card>
        
        <!-- 会员备注 -->
        <el-card class="member-note-card">
          <div slot="header" class="clearfix">
            <span>会员备注</span>
          </div>
          <NoteManager 
            :note="member.note || ''" 
            @update="updateNote"
          />
        </el-card>
      </el-col>
      
      <!-- 会员活动记录 -->
      <el-col :span="16">
        <el-tabs v-model="activeTab">
          <!-- 预约记录 -->
          <el-tab-pane label="预约记录" name="appointments">
            <el-table :data="appointments" style="width: 100%">
              <el-table-column prop="date" label="预约日期" width="180" />
              <el-table-column prop="time" label="预约时间" width="180" />
              <el-table-column prop="service" label="服务项目" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="scope">
                  <el-tag :type="getStatusType(scope.row.status)">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="staff" label="服务人员" width="120" />
            </el-table>
            
            <div class="pagination-wrapper">
              <el-pagination
                @size-change="handleAppointmentSizeChange"
                @current-change="handleAppointmentCurrentChange"
                :current-page="appointmentPage.current"
                :page-sizes="[10, 20, 50, 100]"
                :page-size="appointmentPage.size"
                layout="total, sizes, prev, pager, next, jumper"
                :total="appointmentPage.total"
              />
            </div>
          </el-tab-pane>
          
          <!-- 消费记录 -->
          <el-tab-pane label="消费记录" name="consumption">
            <el-table :data="consumption" style="width: 100%">
              <el-table-column prop="date" label="消费日期" width="180" />
              <el-table-column prop="type" label="消费类型" width="120" />
              <el-table-column prop="amount" label="消费金额" width="120">
                <template #default="scope">
                  ¥{{ scope.row.amount }}
                </template>
              </el-table-column>
              <el-table-column prop="description" label="消费描述" />
              <el-table-column prop="payment_method" label="支付方式" width="120" />
            </el-table>
            
            <div class="pagination-wrapper">
              <el-pagination
                @size-change="handleConsumptionSizeChange"
                @current-change="handleConsumptionCurrentChange"
                :current-page="consumptionPage.current"
                :page-sizes="[10, 20, 50, 100]"
                :page-size="consumptionPage.size"
                layout="total, sizes, prev, pager, next, jumper"
                :total="consumptionPage.total"
              />
            </div>
          </el-tab-pane>
          
          <!-- 统计信息 -->
          <el-tab-pane label="统计信息" name="stats">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-card class="stats-card">
                  <div class="stats-title">总消费金额</div>
                  <div class="stats-value">¥{{ stats.total_amount || 0 }}</div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card class="stats-card">
                  <div class="stats-title">消费次数</div>
                  <div class="stats-value">{{ stats.total_count || 0 }}</div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card class="stats-card">
                  <div class="stats-title">平均消费</div>
                  <div class="stats-value">¥{{ stats.avg_amount || 0 }}</div>
                </el-card>
              </el-col>
            </el-row>
            
            <el-row :gutter="20" style="margin-top: 20px">
              <el-col :span="8">
                <el-card class="stats-card">
                  <div class="stats-title">最近消费</div>
                  <div class="stats-value">{{ stats.last_consumption || '无' }}</div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card class="stats-card">
                  <div class="stats-title">预约次数</div>
                  <div class="stats-value">{{ stats.appointment_count || 0 }}</div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card class="stats-card">
                  <div class="stats-title">完成率</div>
                  <div class="stats-value">{{ stats.completion_rate || 0 }}%</div>
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>
        </el-tabs>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { memberAPI } from '@/services/api';
import TagManager from '@/components/TagManager.vue';
import NoteManager from '@/components/NoteManager.vue';

export default {
  name: 'MemberDetailView',
  components: {
    TagManager,
    NoteManager
  },
  setup() {
    const route = useRoute();
    const memberId = route.params.id;
    
    const loading = ref(false);
    const editMode = ref(false);
    const activeTab = ref('appointments');
    
    const member = ref({});
    const appointments = ref([]);
    const consumption = ref([]);
    const stats = ref({});
    
    const appointmentPage = reactive({
      current: 1,
      size: 10,
      total: 0
    });
    
    const consumptionPage = reactive({
      current: 1,
      size: 10,
      total: 0
    });
    
    const genderText = computed(() => {
      const genderMap = {
        male: '男',
        female: '女',
        other: '其他'
      };
      return genderMap[member.value.gender] || '未知';
    });
    
    const getStatusType = (status) => {
      const statusMap = {
        '已完成': 'success',
        '已取消': 'danger',
        '进行中': 'warning',
        '待确认': 'info'
      };
      return statusMap[status] || 'info';
    };
    
    const fetchMemberDetail = async () => {
      try {
        loading.value = true;
        const data = await memberAPI.getMemberById(memberId);
        member.value = data;
      } catch (error) {
        ElMessage.error('获取会员详情失败');
        console.error(error);
      } finally {
        loading.value = false;
      }
    };
    
    const fetchAppointments = async () => {
      try {
        const params = {
          page: appointmentPage.current,
          size: appointmentPage.size
        };
        const data = await memberAPI.getMemberAppointments(memberId, params);
        appointments.value = data.items || [];
        appointmentPage.total = data.total || 0;
      } catch (error) {
        ElMessage.error('获取预约记录失败');
        console.error(error);
      }
    };
    
    const fetchConsumption = async () => {
      try {
        const params = {
          page: consumptionPage.current,
          size: consumptionPage.size
        };
        const data = await memberAPI.getMemberConsumption(memberId, params);
        consumption.value = data.items || [];
        consumptionPage.total = data.total || 0;
      } catch (error) {
        ElMessage.error('获取消费记录失败');
        console.error(error);
      }
    };
    
    const fetchStats = async () => {
      try {
        const data = await memberAPI.getMemberStats({ member_id: memberId });
        stats.value = data;
      } catch (error) {
        ElMessage.error('获取统计信息失败');
        console.error(error);
      }
    };
    
    const saveMember = async () => {
      try {
        await memberAPI.updateMember(memberId, member.value);
        ElMessage.success('保存成功');
        editMode.value = false;
        fetchMemberDetail();
      } catch (error) {
        ElMessage.error('保存失败');
        console.error(error);
      }
    };
    
    const updateTags = async (tags) => {
      try {
        await memberAPI.updateMemberTags(memberId, tags);
        member.value.tags = tags;
        ElMessage.success('标签更新成功');
      } catch (error) {
        ElMessage.error('标签更新失败');
        console.error(error);
      }
    };
    
    const updateNote = async (note) => {
      try {
        await memberAPI.updateMemberNote(memberId, note);
        member.value.note = note;
        ElMessage.success('备注更新成功');
      } catch (error) {
        ElMessage.error('备注更新失败');
        console.error(error);
      }
    };
    
    const handleAppointmentSizeChange = (val) => {
      appointmentPage.size = val;
      appointmentPage.current = 1;
      fetchAppointments();
    };
    
    const handleAppointmentCurrentChange = (val) => {
      appointmentPage.current = val;
      fetchAppointments();
    };
    
    const handleConsumptionSizeChange = (val) => {
      consumptionPage.size = val;
      consumptionPage.current = 1;
      fetchConsumption();
    };
    
    const handleConsumptionCurrentChange = (val) => {
      consumptionPage.current = val;
      fetchConsumption();
    };
    
    onMounted(() => {
      fetchMemberDetail();
      fetchAppointments();
      fetchConsumption();
      fetchStats();
    });
    
    return {
      loading,
      editMode,
      activeTab,
      member,
      appointments,
      consumption,
      stats,
      appointmentPage,
      consumptionPage,
      genderText,
      getStatusType,
      saveMember,
      updateTags,
      updateNote,
      handleAppointmentSizeChange,
      handleAppointmentCurrentChange,
      handleConsumptionSizeChange,
      handleConsumptionCurrentChange
    };
  }
};
</script>

<style scoped>
.member-detail-view {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin-left: 20px;
  color: #303133;
}

.member-info-card,
.member-tags-card,
.member-note-card {
  margin-bottom: 20px;
}

.member-avatar {
  text-align: center;
  margin-bottom: 20px;
}

.clearfix:before,
.clearfix:after {
  display: table;
  content: "";
}

.clearfix:after {
  clear: both;
}

.pagination-wrapper {
  margin-top: 20px;
  text-align: right;
}

.stats-card {
  text-align: center;
}

.stats-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.stats-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
</style>