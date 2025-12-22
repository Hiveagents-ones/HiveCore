<template>
  <div class="booking-status" :class="status">
    <span>{{ status }}</span>
  </div>
</template>

<script>
export default {
  name: "BookingStatus",
  props: {
    status: {
      type: String,
      required: true,
    },
  },
};
</script>

<style scoped>
.booking-status {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 5px;
  font-weight: bold;
}
.booking-status.pending {
  background-color: #ffbe76;
}
.booking-status.confirmed {
  background-color: #78e08f;
}
.booking-status.cancelled {
  background-color: #ff7675;
}
</style>