import { createI18n } from 'vue-i18n'

const messages = {
  en: {
    member: {
      title: 'Member Management',
      list: 'Member List',
      create: 'Create Member',
      edit: 'Edit Member',
      delete: 'Delete Member',
      name: 'Name',
      contact: 'Contact',
      level: 'Member Level',
      startDate: 'Start Date',
      endDate: 'End Date',
      actions: 'Actions',
      search: 'Search',
      reset: 'Reset',
      submit: 'Submit',
      cancel: 'Cancel',
      confirmDelete: 'Are you sure to delete this member?',
      success: 'Success',
      error: 'Error',
      required: 'This field is required',
      invalidEmail: 'Please enter a valid email',
      invalidPhone: 'Please enter a valid phone number'
    },
    common: {
      loading: 'Loading...',
      noData: 'No Data',
      operationSuccess: 'Operation successful',
      operationFailed: 'Operation failed',
      confirm: 'Confirm',
      yes: 'Yes',
      no: 'No'
    }
  },
  zh: {
    member: {
      title: '会员信息管理',
      list: '会员列表',
      create: '创建会员',
      edit: '编辑会员',
      delete: '删除会员',
      name: '姓名',
      contact: '联系方式',
      level: '会员等级',
      startDate: '生效日期',
      endDate: '到期日期',
      actions: '操作',
      search: '搜索',
      reset: '重置',
      submit: '提交',
      cancel: '取消',
      confirmDelete: '确定要删除该会员吗？',
      success: '成功',
      error: '错误',
      required: '此字段为必填项',
      invalidEmail: '请输入有效的邮箱地址',
      invalidPhone: '请输入有效的电话号码'
    },
    common: {
      loading: '加载中...',
      noData: '暂无数据',
      operationSuccess: '操作成功',
      operationFailed: '操作失败',
      confirm: '确认',
      yes: '是',
      no: '否'
    }
  }
}

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh',
  fallbackLocale: 'en',
  messages
})

export default i18n

export const setLocale = (locale) => {
  i18n.global.locale.value = locale
  localStorage.setItem('locale', locale)
}

export const t = i18n.global.t