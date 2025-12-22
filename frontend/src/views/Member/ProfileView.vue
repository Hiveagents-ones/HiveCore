<template>
  <div class="profile-view">
    <h1>会员信息</h1>
    <ProfileForm :member="member" />
  </div>
</template>

<script>
import ProfileForm from '@/components/Member/ProfileForm.vue';
import { fetchMemberProfile } from '@/api/member';

export default {
  name: 'ProfileView',
  components: { ProfileForm },
  data() {
    return {
      member: {}
    };
  },
  async created() {
    this.member = await fetchMemberProfile();
  }
};
</script>

<style scoped>
.profile-view {
  padding: 20px;
}
</style>