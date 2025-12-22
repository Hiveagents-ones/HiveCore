<template>
  <div class="booking-wizard">
    <h1>课程预约向导</h1>
    
    <div class="wizard-steps">
      <div 
        v-for="(step, index) in steps" 
        :key="index"
        :class="['step', { 'active': currentStep === index, 'completed': currentStep > index }]"
        @click="goToStep(index)"
      >
        {{ step.title }}
      </div>
    </div>
    
    <div class="step-content">
      <div v-if="currentStep === 0">
        <h2>选择课程</h2>
        <div class="course-list">
        <div v-if="concurrentError" class="concurrent-error">
          <p>⚠️ 该课程已满或已被其他人预约，请选择其他课程</p>
          <button @click="fetchCourses" class="refresh-btn">刷新课程列表</button>
        </div>
          <div 
            v-for="course in courses" 
            :key="course.id"
            class="course-item"
            :class="{ 'selected': selectedCourseId === course.id }"
            @click="selectCourse(course)"
          >
            <h3>{{ course.name }}</h3>
            <p>时间: {{ course.schedule }}</p>
            <p>教练ID: {{ course.coach_id }}</p>
            <p>最大人数: {{ course.max_members }}</p>
          </div>
        </div>
      </div>
      
      <div v-if="currentStep === 1">
        <h2>确认预约</h2>
        <div v-if="selectedCourse" class="confirmation-details">
          <h3>您选择的课程</h3>
          <p>名称: {{ selectedCourse.name }}</p>
          <p>时间: {{ selectedCourse.schedule }}</p>
          <p>教练ID: {{ selectedCourse.coach_id }}</p>
          
          <div class="form-group">
            <label for="memberName">您的姓名:</label>
            <input id="memberName" v-model="memberName" type="text" />
          </div>
          
          <div class="form-group">
            <label for="memberPhone">联系电话:</label>
            <input id="memberPhone" v-model="memberPhone" type="tel" />
          </div>
        </div>
      </div>
      
      <div v-if="currentStep === 2">
        <h2>预约完成</h2>
        <div v-if="bookingSuccess" class="success-message">
          <p>🎉 预约成功!</p>
          <p>课程: {{ selectedCourse.name }}</p>
          <p>时间: {{ selectedCourse.schedule }}</p>
          <p>我们会尽快与您确认!</p>
        </div>
        <div v-else>
          <p>正在处理您的预约...</p>
        </div>
      </div>
    </div>
    
    <div class="wizard-actions">
      <button 
        v-if="currentStep > 0 && currentStep < steps.length - 1" 
        @click="prevStep"
      >
        上一步
      </button>
      
      <button 
        v-if="currentStep < steps.length - 1" 
        @click="nextStep"
        :disabled="!canProceed"
      >
        {{ currentStep === steps.length - 2 ? '确认预约' : '下一步' }}
      </button>
      
      <button 
        v-if="currentStep === steps.length - 1" 
        @click="resetWizard"
      >
        返回首页
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { getCourses, createCourse, getCourseById } from '../api/courses';

export default {
  name: 'BookingWizard',
  setup() {
    const steps = [
      { title: '选择课程' },
      { title: '确认信息' },
      { title: '完成' }
    ];
    
    const currentStep = ref(0);
    const courses = ref([]);
    const selectedCourseId = ref(null);
    const selectedCourse = ref(null);
    const memberName = ref('');
    const memberPhone = ref('');
    const bookingSuccess = ref(false);
const concurrentError = ref(false);
    
    const canProceed = computed(() => {
      if (currentStep.value === 0) return selectedCourseId.value !== null;
      if (currentStep.value === 1) return memberName.value && memberPhone.value;
      return true;
    });
    
    const fetchCourses = async () => {
      try {
        const data = await getCourses();
        courses.value = data.map(course => ({
          ...course,
          current_members: course.current_members || 0
        }));
      } catch (error) {
        console.error('Failed to fetch courses:', error);
      }
    };
    
    const selectCourse = async (course) => {
      try {
        // 重新获取最新课程数据，防止并发问题
        const freshCourse = await getCourseById(course.id);
        if (freshCourse.current_members >= freshCourse.max_members) {
          concurrentError.value = true;
          selectedCourseId.value = null;
          selectedCourse.value = null;
          return;
        }
        concurrentError.value = false;
        selectedCourseId.value = freshCourse.id;
        selectedCourse.value = freshCourse;
        // 更新本地课程列表中的当前人数
        const index = courses.value.findIndex(c => c.id === freshCourse.id);
        if (index !== -1) {
          courses.value[index].current_members = freshCourse.current_members;
        }
      } catch (error) {
        console.error('Error checking course availability:', error);
        concurrentError.value = true;
      }
    };
    
    const nextStep = async () => {
      if (currentStep.value === steps.length - 2) {
        // 提交预约
        try {
          await createCourse({
            name: selectedCourse.value.name,
            schedule: selectedCourse.value.schedule,
            coach_id: selectedCourse.value.coach_id,
            max_members: selectedCourse.value.max_members,
            member_name: memberName.value,
            member_phone: memberPhone.value
          });
          bookingSuccess.value = true;
          currentStep.value++;
        } catch (error) {
          console.error('Failed to book course:', error);
        }
      } else {
        currentStep.value++;
      }
    };
    
    const prevStep = () => {
      currentStep.value--;
    };
    
    const goToStep = (index) => {
      if (index < currentStep.value) {
        currentStep.value = index;
      }
    };
    
    const resetWizard = () => {
      currentStep.value = 0;
      selectedCourseId.value = null;
      selectedCourse.value = null;
      memberName.value = '';
      memberPhone.value = '';
      bookingSuccess.value = false;
    };
    
    onMounted(() => {
      fetchCourses();
    });
    
    return {
      steps,
      currentStep,
      courses,
      selectedCourseId,
      selectedCourse,
      memberName,
      memberPhone,
      bookingSuccess,
      canProceed,
      selectCourse,
      nextStep,
      prevStep,
      goToStep,
      resetWizard
    };
  }
};
</script>

<style scoped>
.booking-wizard {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.wizard-steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 30px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.step {
  flex: 1;
  text-align: center;
  padding: 10px;
  cursor: pointer;
  color: #999;
  position: relative;
}

.step.active {
  color: #42b983;
  font-weight: bold;
}

.step.completed {
  color: #42b983;
}

.step:not(:last-child):after {
  content: '';
  position: absolute;
  top: 50%;
  right: 0;
  width: 100%;
  height: 2px;
  background: #eee;
  z-index: -1;
}

.step.completed:not(:last-child):after {
  background: #42b983;
}

.course-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.course-item {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s;
}

.course-item:hover {
  border-color: #42b983;
}

.course-item.selected {
  border-color: #42b983;
  background-color: rgba(66, 185, 131, 0.1);
}

.confirmation-details {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 5px;
}

.form-group {
  margin: 15px 0;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.success-message {
  text-align: center;
  padding: 30px;
  background-color: #f8fff8;
  border: 1px solid #42b983;
  border-radius: 5px;
}

.concurrent-error {
  .refresh-btn {
    margin-top: 10px;
    padding: 5px 10px;
    background-color: #ff6b6b;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .refresh-btn:hover {
    background-color: #ff5252;
  }
  grid-column: 1 / -1;
  padding: 15px;
  margin-bottom: 20px;
  background-color: #fff8f8;
  border: 1px solid #ff6b6b;
  border-radius: 5px;
  color: #ff6b6b;
  text-align: center;
}
  text-align: center;
  padding: 30px;
  background-color: #f8fff8;
  border: 1px solid #42b983;
  border-radius: 5px;
}

.wizard-actions {
  margin-top: 30px;
  display: flex;
  justify-content: space-between;
}

button {
  padding: 10px 20px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style>