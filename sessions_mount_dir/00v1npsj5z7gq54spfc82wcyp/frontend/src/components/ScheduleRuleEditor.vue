<template>
  <div class="schedule-rule-editor">
    <div class="header">
      <h3>教练排班规则设置</h3>
      <el-button type="text" @click="showHelp" class="help-btn">帮助</el-button>
      <el-button type="primary" @click="saveRules">保存规则</el-button>
      
    </div>

    <div class="content">
      <el-form ref="form" :model="formData" label-width="120px">
        <el-form-item label="选择教练">
          <el-select v-model="formData.coachId" placeholder="请选择教练" filterable>
            <el-option
              v-for="coach in coaches"
              :key="coach.id"
              :label="coach.name"
              :value="coach.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="工作日" prop="workDays" :rules="[{ required: true, message: '请至少选择一个工作日', trigger: 'change' }]">
          <el-checkbox-group v-model="formData.workDays">
            <el-checkbox v-for="day in weekDays" :key="day.value" :label="day.value">
              {{ day.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="工作时间" prop="workTimeRange" :rules="[{ required: true, message: '请设置工作时间范围', trigger: 'change' }]">
          <el-time-picker
            v-model="formData.workTimeRange"
            is-range
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="HH:mm"
          />
        </el-form-item>

        <el-form-item label="课程间隔" prop="courseInterval" :rules="[{ required: true, message: '请设置课程间隔时间', trigger: 'change' }]">
          <el-input-number v-model="formData.courseInterval" :min="30" :max="120" :step="15" />
          <span class="unit">分钟</span>
        </el-form-item>

        <el-form-item label="最大课程数" prop="maxCourses" :rules="[{ required: true, message: '请设置最大课程数', trigger: 'change' }]">
          <el-input-number v-model="formData.maxCourses" :min="1" :max="10" />
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCoaches, saveScheduleRules } from '../api/coaches'

export default {
  name: 'ScheduleRuleEditor',
  
  setup() {
    const form = ref(null)
    const coaches = ref([])
    
    const formData = ref({
      // 默认工作时间 09:00-18:00
      coachId: '',
      workDays: [],
      workTimeRange: ['09:00', '18:00'],
      courseInterval: 60,
      maxCourses: 5
    })
    
    const weekDays = [
  // 工作日选项配置
    // 工作日选项配置
      { label: '周一', value: 1 },
      { label: '周二', value: 2 },
      { label: '周三', value: 3 },
      { label: '周四', value: 4 },
      { label: '周五', value: 5 },
      { label: '周六', value: 6 },
      { label: '周日', value: 7 }
    ]
    
    const fetchCoaches = async () => {
      try {
        const response = await getCoaches()
        coaches.value = response.data
      } catch (error) {
        ElMessage.error('获取教练列表失败')
        console.error(error)
      }
    }
    
    const showHelp = () => {
  // 表单验证失败处理
      ElMessage.info({
        message: '排班规则说明：\n1. 选择教练后设置其工作时间和课程安排\n2. 工作时间范围为每天的工作时段\n3. 课程间隔为每节课之间的休息时间\n4. 最大课程数为该教练每天最多安排的课程数',
        duration: 8000,
        showClose: true
      })
    }

    const saveRules = async () => {
      try {
        await form.value.validate()
        // 表单验证通过后继续执行
      try {
        const rules = {
          coach_id: formData.value.coachId,
          work_days: formData.value.workDays,
          work_start_time: formData.value.workTimeRange[0],
          work_end_time: formData.value.workTimeRange[1],
          course_interval: formData.value.courseInterval,
          max_courses: formData.value.maxCourses
        }
        
        await saveScheduleRules(rules)
        // 重置表单数据
        formData.value = {
          coachId: '',
          workDays: [],
          workTimeRange: ['09:00', '18:00'],
          courseInterval: 60,
          maxCourses: 5
        }
        ElMessage.success('排班规则保存成功')
      } catch (error) {
        ElMessage.error(`保存排班规则失败: ${error.message}`)
        console.error(error)
      }
    }
    
    onMounted(() => {
      fetchCoaches()
    })
    
    return {
      showHelp,
      form,
      formData,
      coaches,
      weekDays,
      saveRules
    }
  }
}
</script>

<style scoped>
.schedule-rule-editor {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
  
  .header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    
    .help-btn {
      font-size: 14px;
      color: #409eff;
    }
  }
}

.content {
  padding: 0 20px;
}

.unit {
  margin-left: 10px;
  color: #909399;
}

.el-checkbox {
  margin-right: 15px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    <div class="header">
      <h3>教练排班规则设置</h3>
      <div class="header-actions">
        <el-button type="text" @click="showHelp" class="help-btn">帮助</el-button>
        <el-button type="primary" @click="saveRules">保存规则</el-button>
      </div>
    </div>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    <div class="header">
      <h3>教练排班规则设置</h3>
      <div class="header-actions">
        <el-button type="text" @click="showHelp" class="help-btn">帮助</el-button>
        <el-button type="primary" @click="saveRules">保存规则</el-button>
      </div>
    </div>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    <div class="header">
      <h3>教练排班规则设置</h3>
      <div class="header-actions">
        <el-button type="text" @click="showHelp" class="help-btn">帮助</el-button>
        <el-button type="primary" @click="saveRules">保存规则</el-button>
      </div>
    </div>