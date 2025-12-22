import { createI18n } from 'vue-i18n'

const messages = {
  en: {
    nav: {
      home: 'Home',
      about: 'About',
      contact: 'Contact'
    },
    auth: {
      register: {
        title: 'Register',
        username: 'Username',
        password: 'Password',
        confirmPassword: 'Confirm Password',
        submit: 'Register',
        usernameRequired: 'Username is required',
        passwordRequired: 'Password is required',
        passwordMinLength: 'Password must be at least 6 characters',
        passwordMismatch: 'Passwords do not match',
        usernameExists: 'Username already exists',
        registerSuccess: 'Registration successful',
        registerFailed: 'Registration failed'
      },
      login: {
        title: 'Login',
        username: 'Username',
        password: 'Password',
        submit: 'Login',
        loginSuccess: 'Login successful',
        loginFailed: 'Login failed'
      }
    }
  },
  zh: {
    nav: {
      home: '首页',
      about: '关于',
      contact: '联系'
    },
    auth: {
      register: {
        title: '注册',
        username: '用户名',
        password: '密码',
        confirmPassword: '确认密码',
        submit: '注册',
        usernameRequired: '请输入用户名',
        passwordRequired: '请输入密码',
        passwordMinLength: '密码至少需要6个字符',
        passwordMismatch: '两次输入的密码不一致',
        usernameExists: '用户名已存在',
        registerSuccess: '注册成功',
        registerFailed: '注册失败'
      },
      login: {
        title: '登录',
        username: '用户名',
        password: '密码',
        submit: '登录',
        loginSuccess: '登录成功',
        loginFailed: '登录失败'
      }
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