import { createI18n } from 'vue-i18n'

const messages = {
  'zh-CN': {
    pages: {
        checkin: '会员签到'
    },
    checkin: {
      title: '会员签到',
      searchMethod: '签到方式',
      byPhone: '手机号',
      byId: '会员ID',
      byIdCard: '身份证号',
      phonePlaceholder: '请输入11位手机号码',
      memberIdPlaceholder: '请输入会员ID',
      idCardPlaceholder: '请输入18位身份证号码',
      confirmButton: '确认签到',
      resetButton: '重置',
      success: '会员 {name} 签到成功！签到时间：{time}',
      errors: {
        memberNotFound: '查无此会员，请核对信息后重试',
        failed: '签到失败，请稍后再试',
        network: '网络错误，请检查网络连接',
      },
      rules: {
        methodRequired: '请选择一种签到方式',
        identifierRequired: '请输入会员信息',
        phoneFormat: '请输入正确的11位手机号码',
        idCardFormat: '请输入正确的18位身份证号码',
      },
    },
    member: {
      phone: '手机号码',
      id: '会员ID',
      idCard: '身份证号',
    },
  },
  'en-US': {
    pages: {
        checkin: 'Member Checkin'
    },
    checkin: {
      title: 'Member Check-in',
      searchMethod: 'Check-in Method',
      byPhone: 'Phone Number',
      byId: 'Member ID',
      byIdCard: 'ID Card Number',
      phonePlaceholder: 'Enter 11-digit phone number',
      memberIdPlaceholder: 'Enter Member ID',
      idCardPlaceholder: 'Enter 18-digit ID card number',
      confirmButton: 'Check In',
      resetButton: 'Reset',
      success: 'Member {name} checked in successfully at {time}',
      errors: {
        memberNotFound: 'Member not found. Please verify the information and try again.',
        failed: 'Check-in failed. Please try again later.',
        network: 'Network error. Please check your connection.',
      },
      rules: {
        methodRequired: 'Please select a check-in method.',
        identifierRequired: 'Please enter member information.',
        phoneFormat: 'Please enter a valid 11-digit phone number.',
        idCardFormat: 'Please enter a valid 18-digit ID card number.',
      },
    },
    member: {
        phone: 'Phone Number',
        id: 'Member ID',
        idCard: 'ID Card Number',
    },
  },
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'en-US',
  messages,
})

export default i18n
