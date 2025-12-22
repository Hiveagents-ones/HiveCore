<template>
  <div>
    <h1>Member Card Management</h1>
    <div v-if="loading">Loading...</div>
    <div v-else>
      <div v-for="card in memberCards" :key="card.id">
        <p>Card ID: {{ card.id }}</p>
        <p>Type: {{ card.card_type }}</p>
        <p>Expiry: {{ card.expiry_date }}</p>
        <p>Status: {{ card.status }}</p>
        <button @click="activateCard(card.id)" v-if="card.status !== 'active'">Activate</button>
        <button @click="deactivateCard(card.id)" v-else>Deactivate</button>
        <button @click="renewCard(card.id)">Renew</button>
      </div>
    </div>
  </div>
</template>

<script>
import { fetchMemberCards, manageMemberCard } from '../api/member';

export default {
  data() {
    return {
      memberCards: [],
      loading: true,
    };
  },
  async created() {
    await this.loadMemberCards();
    this.loading = false;
  },
  methods: {
    async loadMemberCards() {
      this.memberCards = await fetchMemberCards(this.$route.params.memberId);
    },
    async activateCard(cardId) {
      await manageMemberCard('activate', { cardId });
      await this.loadMemberCards();
    },
    async deactivateCard(cardId) {
      await manageMemberCard('deactivate', { cardId });
      await this.loadMemberCards();
    },
    async renewCard(cardId) {
      const expiryDate = prompt('Enter new expiry date (YYYY-MM-DD):');
      if (expiryDate) {
        await manageMemberCard('renew', { cardId, expiryDate });
        await this.loadMemberCards();
      }
    },
  },
};
</script>