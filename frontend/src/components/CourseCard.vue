<template>
  <div class="course-card">
    <h3>{{ course.title }}</h3>
    <p>{{ course.description }}</p>
    <p>Instructor: {{ course.instructor }}</p>
    <p>Schedule: {{ new Date(course.schedule).toLocaleString() }}</p>
    <p>Max Participants: {{ course.max_participants }}</p>
    <button @click="$emit('book-course', course.id)">Book Now</button>
  </div>
</template>

<script>
export default {
  name: "CourseCard",
  props: {
    course: {
      type: Object,
      required: true,
    },
  },
};
</script>

<style scoped>
.course-card {
  border: 1px solid #ccc;
  padding: 1rem;
  margin: 1rem 0;
  border-radius: 5px;
}
button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 5px;
  cursor: pointer;
}
button:hover {
  background-color: #369f76;
}
</style>