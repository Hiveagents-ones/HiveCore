<template>
  <div class="course-schedule">
    <h2>课程表</h2>
    <div class="course-grid">
      <CourseCard
        v-for="course in courses"
        :key="course.id"
        :course="course"
        @enroll="handleEnroll"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCourseStore } from '@/stores/course'
import CourseCard from '@/components/CourseCard.vue'

const courseStore = useCourseStore()
const courses = ref([])

onMounted(async () => {
  courses.value = await courseStore.fetchCourses()
})

const handleEnroll = async (courseId) => {
  try {
    await courseStore.enrollCourse(courseId)
    alert('报名成功！')
  } catch (error) {
    alert(error.message)
  }
}
</script>

<style scoped>
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}
</style>
