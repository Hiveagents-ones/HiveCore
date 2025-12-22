<template>
  <div class="member-detail">
    <h2>会员详情</h2>
    <div v-if="member" class="detail-container">
      <div class="detail-row">
        <span class="label">姓名:</span>
        <span class="value">{{ member.name }}</span>
      </div>
      <div class="detail-row">
        <span class="label">电话:</span>
        <span class="value">{{ maskPhone(member.phone) }}</span>
      </div>
      <div class="detail-row">
        <span class="label">邮箱:</span>
        <span class="value">{{ maskEmail(member.email) }}</span>
      </div>
      <div class="detail-row">
        <span class="label">加入日期:</span>
        <span class="value">{{ member.join_date }}</span>
      </div>
    </div>
    <div v-else>
      加载中...
    </div>
  </div>
</template>

<script>
export default {
  name: 'MemberDetail',
  props: {
    member: {
      type: Object,
      default: null
    }
  },
  methods: {
    maskPhone(phone) {
      if (!phone) return ''
      return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
    },
    maskEmail(email) {
      if (!email) return ''
      const [name, domain] = email.split('@')
      if (!name || !domain) return email
      const maskedName = name.length > 2 
        ? name.substring(0, 2) + '*'.repeat(name.length - 2)
        : name.charAt(0) + '*' 
      return `${maskedName}@${domain}`
    }
  }
}
</script>

<style scoped>
.member-detail {
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 4px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.detail-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
}

.label {
  font-weight: bold;
  min-width: 80px;
  color: #666;
}

.value {
  margin-left: 10px;
}
</style>