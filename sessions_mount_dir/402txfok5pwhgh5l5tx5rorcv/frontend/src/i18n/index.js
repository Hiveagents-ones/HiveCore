import { createI18n } from 'vue-i18n'

const messages = {
  en: {
    member: {
      title: 'Member Management',
      name: 'Name',
      contact: 'Contact',
      level: 'Member Level',
      status: 'Status',
      statusActive: 'Active',
      statusFrozen: 'Frozen',
      statusExpired: 'Expired',
      entryRecords: 'Entry Records',
      create: 'Create Member',
      edit: 'Edit Member',
      delete: 'Delete Member',
      search: 'Search',
      reset: 'Reset',
      confirm: 'Confirm',
      cancel: 'Cancel',
      save: 'Save',
      actions: 'Actions'
    },
    common: {
      required: 'This field is required',
      success: 'Success',
      error: 'Error',
      loading: 'Loading...',
      noData: 'No Data',
      operationSuccess: 'Operation successful',
      operationFailed: 'Operation failed',
      confirmDelete: 'Are you sure you want to delete this item?'
    }
  },
  zh: {
    member: {
      title: '会员信息管理',
      name: '姓名',
      contact: '联系方式',
      level: '会员等级',
      status: '会员状态',
      statusActive: '活跃',
      statusFrozen: '冻结',
      statusExpired: '过期',
      entryRecords: '入场记录',
      create: '创建会员',
      edit: '编辑会员',
      delete: '删除会员',
      search: '搜索',
      reset: '重置',
      confirm: '确认',
      cancel: '取消',
      save: '保存',
      actions: '操作'
    },
    common: {
      required: '此字段为必填项',
      success: '成功',
      error: '错误',
      loading: '加载中...',
      noData: '暂无数据',
      operationSuccess: '操作成功',
      operationFailed: '操作失败',
      confirmDelete: '确定要删除此项吗？'
    }
  }
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh',
  fallbackLocale: 'en',
  messages
})

export default i18n