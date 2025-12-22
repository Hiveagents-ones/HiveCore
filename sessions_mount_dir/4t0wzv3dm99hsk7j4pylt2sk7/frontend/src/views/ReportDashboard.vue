<template>
  <div class="report-dashboard">
    <div class="dashboard-header">
      <h1>数据报表与分析</h1>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleDateChange"
        />
        <el-button type="primary" @click="refreshData">
          <i class="el-icon-refresh"></i> 刷新
        </el-button>
        <el-button type="success" @click="showExportDialog">
          <i class="el-icon-download"></i> 导出报表
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" class="summary-cards">
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="card-content">
            <h3>总会员数</h3>
            <p class="card-value">{{ summary.totalMembers }}</p>
            <span class="card-trend positive">
              <i class="el-icon-top"></i> +12.5%
            </span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="card-content">
            <h3>总收入</h3>
            <p class="card-value">¥{{ summary.totalRevenue }}</p>
            <span class="card-trend positive">
              <i class="el-icon-top"></i> +8.3%
            </span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="card-content">
            <h3>活跃课程</h3>
            <p class="card-value">{{ summary.activeCourses }}</p>
            <span class="card-trend negative">
              <i class="el-icon-bottom"></i> -2.1%
            </span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="card-content">
            <h3>平均客单价</h3>
            <p class="card-value">¥{{ summary.avgOrderValue }}</p>
            <span class="card-trend positive">
              <i class="el-icon-top"></i> +5.7%
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab" @tab-click="handleTabClick">
      <el-tab-pane label="会员趋势" name="members">
        <el-card>
          <div slot="header" class="chart-header">
            <span>新增会员趋势</span>
            <el-button type="text" @click="drillDown('member_trend')">
              查看详情
            </el-button>
          </div>
          <div ref="memberTrendChart" class="chart-container"></div>
        </el-card>
        <el-row :gutter="20" class="sub-charts">
          <el-col :span="12">
            <el-card>
              <div slot="header">会员类型分布</div>
              <div ref="memberTypeChart" class="chart-container"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <div slot="header">性别分布</div>
              <div ref="genderChart" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="课程分析" name="courses">
        <el-card>
          <div slot="header" class="chart-header">
            <span>课程受欢迎度</span>
            <el-button type="text" @click="drillDown('course_popularity')">
              查看详情
            </el-button>
          </div>
          <div ref="coursePopularityChart" class="chart-container"></div>
        </el-card>
        <el-row :gutter="20" class="sub-charts">
          <el-col :span="12">
            <el-card>
              <div slot="header">时间段分布</div>
              <div ref="timeSlotChart" class="chart-container"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <div slot="header">场地使用率</div>
              <div ref="locationChart" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="收入统计" name="revenue">
        <el-card>
          <div slot="header" class="chart-header">
            <span>收入趋势</span>
            <el-button type="text" @click="drillDown('revenue_stats')">
              查看详情
            </el-button>
          </div>
          <div ref="revenueChart" class="chart-container"></div>
        </el-card>
        <el-row :gutter="20" class="sub-charts">
          <el-col :span="12">
            <el-card>
              <div slot="header">支付类型分布</div>
              <div ref="paymentTypeChart" class="chart-container"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <div slot="header">Top会员消费</div>
              <el-table :data="topMembers" style="width: 100%">
                <el-table-column prop="name" label="会员姓名" />
                <el-table-column prop="total_spent" label="消费金额">
                  <template slot-scope="scope">
                    ¥{{ scope.row.total_spent }}
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>

    <!-- 导出中心 -->
    <ExportCenter ref="exportCenter" />

    <!-- 数据钻取弹窗 -->
    <DrillDownModal
      ref="drillDownModal"
      @refresh="refreshData"
    />
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getMemberTrend, getCoursePopularity, getRevenueStats } from '@/api/reports'
import ExportCenter from '@/components/reports/ExportCenter'
import DrillDownModal from '@/components/reports/DrillDownModal'

export default {
  name: 'ReportDashboard',
  components: {
    ExportCenter,
    DrillDownModal
  },
  data() {
    return {
      activeTab: 'members',
      dateRange: [new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), new Date()],
      summary: {
        totalMembers: 0,
        totalRevenue: 0,
        activeCourses: 0,
        avgOrderValue: 0
      },
      memberData: null,
      courseData: null,
      revenueData: null,
      topMembers: [],
      charts: {},
      autoRefreshTimer: null
    }
  },
  mounted() {
    this.initCharts()
    this.loadData()
    this.startAutoRefresh()
  },
  beforeDestroy() {
    this.destroyCharts()
    this.stopAutoRefresh()
  },
  methods: {
    async loadData() {
      try {
        const [startDate, endDate] = this.dateRange
        
        // 加载会员数据
        const memberRes = await getMemberTrend({
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString()
        })
        this.memberData = memberRes.data
        this.summary.totalMembers = memberRes.data.total_members
        
        // 加载课程数据
        const courseRes = await getCoursePopularity({
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString()
        })
        this.courseData = courseRes.data
        this.summary.activeCourses = courseData.course_enrollment.length
        
        // 加载收入数据
        const revenueRes = await getRevenueStats({
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString()
        })
        this.revenueData = revenueRes.data
        this.summary.totalRevenue = revenueRes.data.total_revenue.toLocaleString()
        this.summary.avgOrderValue = Math.round(revenueRes.data.total_revenue / revenueRes.data.payment_types.reduce((acc, p) => acc + p.count, 0))
        this.topMembers = revenueRes.data.top_members
        
        // 更新图表
        this.updateCharts()
      } catch (error) {
        this.$message.error('加载数据失败')
      }
    },
    
    initCharts() {
      // 初始化所有图表实例
      this.charts.memberTrend = echarts.init(this.$refs.memberTrendChart)
      this.charts.memberType = echarts.init(this.$refs.memberTypeChart)
      this.charts.gender = echarts.init(this.$refs.genderChart)
      this.charts.coursePopularity = echarts.init(this.$refs.coursePopularityChart)
      this.charts.timeSlot = echarts.init(this.$refs.timeSlotChart)
      this.charts.location = echarts.init(this.$refs.locationChart)
      this.charts.revenue = echarts.init(this.$refs.revenueChart)
      this.charts.paymentType = echarts.init(this.$refs.paymentTypeChart)
      
      // 监听窗口大小变化
      window.addEventListener('resize', this.handleResize)
    },
    
    updateCharts() {
      if (this.activeTab === 'members' && this.memberData) {
        this.updateMemberTrendChart()
        this.updateMemberTypeChart()
        this.updateGenderChart()
      } else if (this.activeTab === 'courses' && this.courseData) {
        this.updateCoursePopularityChart()
        this.updateTimeSlotChart()
        this.updateLocationChart()
      } else if (this.activeTab === 'revenue' && this.revenueData) {
        this.updateRevenueChart()
        this.updatePaymentTypeChart()
      }
    },
    
    updateMemberTrendChart() {
      const option = {
        title: {
          text: '每日新增会员'
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: this.memberData.daily_new.map(d => d.date)
        },
        yAxis: {
          type: 'value'
        },
        series: [{
          name: '新增会员',
          type: 'line',
          data: this.memberData.daily_new.map(d => d.count),
          smooth: true,
          areaStyle: {}
        }]
      }
      this.charts.memberTrend.setOption(option)
    },
    
    updateMemberTypeChart() {
      const option = {
        tooltip: {
          trigger: 'item'
        },
        series: [{
          name: '会员类型',
          type: 'pie',
          radius: ['40%', '70%'],
          data: this.memberData.member_types.map(t => ({
            name: t.type,
            value: t.count
          }))
        }]
      }
      this.charts.memberType.setOption(option)
    },
    
    updateGenderChart() {
      const option = {
        tooltip: {
          trigger: 'item'
        },
        series: [{
          name: '性别分布',
          type: 'pie',
          data: this.memberData.gender_distribution.map(g => ({
            name: g.gender,
            value: g.count
          }))
        }]
      }
      this.charts.gender.setOption(option)
    },
    
    updateCoursePopularityChart() {
      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          }
        },
        xAxis: {
          type: 'category',
          data: this.courseData.course_enrollment.slice(0, 10).map(c => c.course_name)
        },
        yAxis: {
          type: 'value'
        },
        series: [{
          name: '报名人数',
          type: 'bar',
          data: this.courseData.course_enrollment.slice(0, 10).map(c => c.enrollments)
        }]
      }
      this.charts.coursePopularity.setOption(option)
    },
    
    updateTimeSlotChart() {
      const option = {
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: this.courseData.time_slots.map(t => `${t.hour}:00`)
        },
        yAxis: {
          type: 'value'
        },
        series: [{
          name: '课程数量',
          type: 'line',
          data: this.courseData.time_slots.map(t => t.count),
          smooth: true
        }]
      }
      this.charts.timeSlot.setOption(option)
    },
    
    updateLocationChart() {
      const option = {
        tooltip: {
          trigger: 'item'
        },
        series: [{
          name: '场地使用',
          type: 'pie',
          radius: '50%',
          data: this.courseData.location_usage.map(l => ({
            name: l.location,
            value: l.usage
          }))
        }]
      }
      this.charts.location.setOption(option)
    },
    
    updateRevenueChart() {
      const option = {
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: this.revenueData.daily_revenue.map(d => d.date)
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: '¥{value}'
          }
        },
        series: [{
          name: '日收入',
          type: 'line',
          data: this.revenueData.daily_revenue.map(d => d.revenue),
          smooth: true,
          areaStyle: {}
        }]
      }
      this.charts.revenue.setOption(option)
    },
    
    updatePaymentTypeChart() {
      const option = {
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        series: [{
          name: '支付类型',
          type: 'pie',
          radius: ['40%', '70%'],
          data: this.revenueData.payment_types.map(p => ({
            name: p.type,
            value: p.amount
          }))
        }]
      }
      this.charts.paymentType.setOption(option)
    },
    
    handleDateChange() {
      this.loadData()
    },
    
    handleTabClick() {
      this.$nextTick(() => {
        this.updateCharts()
      })
    },
    
    refreshData() {
      this.loadData()
      this.$message.success('数据已刷新')
    },
    
    showExportDialog() {
      this.$refs.exportCenter.show()
    },
    
    drillDown(reportType) {
      this.$refs.drillDownModal.show({
        reportType,
        dateRange: this.dateRange
      })
    },
    
    startAutoRefresh() {
      this.autoRefreshTimer = setInterval(() => {
        this.loadData()
      }, 5 * 60 * 1000) // 5分钟自动刷新
    },
    
    stopAutoRefresh() {
      if (this.autoRefreshTimer) {
        clearInterval(this.autoRefreshTimer)
        this.autoRefreshTimer = null
      }
    },
    
    handleResize() {
      Object.values(this.charts).forEach(chart => {
        if (chart) {
          chart.resize()
        }
      })
    },
    
    destroyCharts() {
      window.removeEventListener('resize', this.handleResize)
      Object.values(this.charts).forEach(chart => {
        if (chart) {
          chart.dispose()
        }
      })
      this.charts = {}
    }
  }
}
</script>

<style scoped>
.report-dashboard {
  padding: 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.summary-cards {
  margin-bottom: 20px;
}

.summary-card {
  text-align: center;
}

.card-content {
  padding: 10px;
}

.card-content h3 {
  font-size: 14px;
  color: #909399;
  margin: 0 0 10px 0;
}

.card-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin: 0 0 10px 0;
}

.card-trend {
  font-size: 12px;
}

.card-trend.positive {
  color: #67c23a;
}

.card-trend.negative {
  color: #f56c6c;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.sub-charts {
  margin-top: 20px;
}

.sub-charts .chart-container {
  height: 300px;
}
</style>
