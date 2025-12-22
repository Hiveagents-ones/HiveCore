<template>
  <div>
    <h1>My Bookings</h1>
    <div v-if="bookings.length > 0" class="booking-list">
      <div v-for="booking in bookings" :key="booking.id" class="booking-item">
        <h3>Course ID: {{ booking.course_id }}</h3>
        <p>Status: {{ booking.status }}</p>
        <p>Booked on: {{ booking.created_at }}</p>
      </div>
    </div>
    <p v-else>No bookings found.</p>
  </div>
</template>

<script>
import { fetchBookings } from "@/api/bookings";

export default {
  name: "MyBookings",
  data() {
    return {
      bookings: [],
    };
  },
  async created() {
    this.bookings = await fetchBookings();
  },
};
</script>