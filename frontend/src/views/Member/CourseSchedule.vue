<template>
  <div>
    <h1>Course Schedule</h1>
    <div v-if="courses.length > 0" class="course-list">
      <CourseCard
        v-for="course in courses"
        :key="course.id"
        :course="course"
        @book-course="handleBooking"
      />
    </div>
    <p v-else>No courses available.</p>
  </div>
</template>

<script>
import { fetchCourses, fetchCourse, createBooking } from "@/api/courses";
import CourseCard from "@/components/CourseCard.vue";

export default {
  name: "CourseSchedule",
  components: {
    CourseCard,
  },
  data() {
    return {
      courses: [],
    };
  },
  async created() {
    this.courses = await fetchCourses();
  },
  methods: {
    async handleBooking(courseId) {
      try {
        const booking = await createBooking({
          course_id: courseId,
          user_id: 1, // Placeholder for logged-in user ID
          status: "pending",
          created_at: new Date().toISOString(),
        });
        alert(`Booking created with ID: ${booking.id}`);
      } catch (error) {
        console.error("Error creating booking:", error);
      }
    },
  },
};
</script>