<template>
  <div class="course-management">
    <h2>课程管理</h2>
    <button @click="showCreateForm = true" class="btn btn-primary">创建新课程</button>
    
    <div v-if="showCreateForm" class="modal">
      <div class="modal-content">
        <h3>创建课程</h3>
        <form @submit.prevent="createCourse">
          <input v-model="newCourse.name" placeholder="课程名称" required>
          <input v-model="newCourse.coach" placeholder="教练" required>
          <input v-model="newCourse.time" type="datetime-local" required>
          <input v-model="newCourse.location" placeholder="地点" required>
          <input v-model="newCourse.capacity" type="number" placeholder="容量" required>
          <textarea v-model="newCourse.description" placeholder="描述"></textarea>
          <button type="submit">保存</button>
          <button type="button" @click="showCreateForm = false">取消</button>
        </form>
      </div>
    </div>
    
    <div class="course-list">
      <div v-for="course in courses" :key="course.id" class="course-item">
        <h3>{{ course.name }}</h3>
        <p>教练: {{ course.coach }}</p>
        <p>时间: {{ formatTime(course.time) }}</p>
        <p>地点: {{ course.location }}</p>
        <p>容量: {{ course.capacity }}</p>
        <button @click="editCourse(course)">编辑</button>
        <button @click="deleteCourse(course.id)">删除</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCourseStore } from '@/stores/course'

const courseStore = useCourseStore()
const courses = ref([])
const showCreateForm = ref(false)
const newCourse = ref({
  name: '',
  coach: '',
  time: '',
  location: '',
  capacity: 0,
  description: ''
})

onMounted(async () => {
  courses.value = await courseStore.fetchCourses()
})

const createCourse = async () => {
  await courseStore.createCourse(newCourse.value)
  showCreateForm.value = false
  courses.value = await courseStore.fetchCourses()
}

const editCourse = async (course) => {
  // Implement edit functionality
  console.log('Edit course:', course)
}

const deleteCourse = async (courseId) => {
  if (confirm('确定要删除这个课程吗？')) {
    await courseStore.deleteCourse(courseId)
    courses.value = await courseStore.fetchCourses()
  }
}

const formatTime = (time) => new Date(time).toLocaleString()
</script>

<style scoped>
.btn {
  padding: 10px 20px;
  margin: 10px 0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary {
  background-color: #007bff;
  color: white;
}
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}
.modal-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
}
.course-item {
  border: 1px solid #ddd;
  padding: 15px;
  margin: 10px 0;
  border-radius: 4px;
}
</style>
