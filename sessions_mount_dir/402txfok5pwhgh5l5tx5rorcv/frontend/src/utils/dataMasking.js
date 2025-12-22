/**
 * 敏感数据脱敏工具函数
 * 用于在前端展示时对敏感信息进行脱敏处理
 * 支持手机号、邮箱、身份证号、姓名、银行卡号、地址等常见敏感数据的脱敏
 */

/**
 * 手机号脱敏
 * @param {string} phone - 手机号
 * @returns {string} 脱敏后的手机号
 */
export function maskPhone(phone) {
  if (!phone || typeof phone !== 'string') return '';
  
  // 保留前3位和后4位，中间用*代替
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}

/**
 * 邮箱脱敏
 * @param {string} email - 邮箱地址
 * @returns {string} 脱敏后的邮箱
 */
export function maskEmail(email) {
  if (!email || typeof email !== 'string') return '';
  
  const [username, domain] = email.split('@');
  if (!username || !domain) return email;
  
  // 用户名只显示前2位和最后1位，中间用*代替
  const maskedUsername = username.length > 3
    ? username.substring(0, 2) + '*'.repeat(username.length - 3) + username.substring(username.length - 1)
    : username;
  
  return `${maskedUsername}@${domain}`;
}

/**
 * 身份证号脱敏
 * @param {string} idCard - 身份证号
 * @returns {string} 脱敏后的身份证号
 */
export function maskIdCard(idCard) {
  if (!idCard || typeof idCard !== 'string') return '';
  
  // 保留前6位和后4位，中间用*代替
  return idCard.replace(/(\d{6})\d*(\d{4})/, '$1********$2');
}

/**
 * 姓名脱敏
 * @param {string} name - 姓名
 * @returns {string} 脱敏后的姓名
 */
export function maskName(name) {
  if (!name || typeof name !== 'string') return '';
  
  // 2个字显示第一个字，3个字及以上显示第一个和最后一个字
  if (name.length === 2) {
    return name[0] + '*';
  } else if (name.length > 2) {
    return name[0] + '*'.repeat(name.length - 2) + name[name.length - 1];
  }
  
  return name;
}

/**
 * 银行卡号脱敏
 * @param {string} cardNo - 银行卡号
 * @returns {string} 脱敏后的银行卡号
 */
export function maskBankCard(cardNo) {
  if (!cardNo || typeof cardNo !== 'string') return '';
  
  // 保留前4位和后4位，中间用*代替
  return cardNo.replace(/(\d{4})\d*(\d{4})/, '$1 **** **** $2');
}

/**
 * 地址脱敏
 * @param {string} address - 地址
 * @returns {string} 脱敏后的地址
 */
export function maskAddress(address) {
  if (!address || typeof address !== 'string') return '';
  
  // 保留前6个字符，后面的用*代替
  if (address.length > 6) {
    return address.substring(0, 6) + '*'.repeat(address.length - 6);
  }
  
  return address;
}

/**
 * 通用脱敏函数
 * @param {string} data - 需要脱敏的数据
 * @param {string} type - 数据类型 (phone, email, idCard, name, bankCard, address)
 * @returns {string} 脱敏后的数据
 * @example
 * maskData('13812345678', 'phone') // '138****5678'
 * maskData('test@example.com', 'email') // 'te***@example.com'
 */
export function maskData(data, type) {
  if (!data || typeof data !== 'string') return '';
  
  switch (type) {
    case 'phone':
      return maskPhone(data);
    case 'email':
      return maskEmail(data);
    case 'idCard':
      return maskIdCard(data);
    case 'name':
      return maskName(data);
    case 'bankCard':
      return maskBankCard(data);
    case 'address':
      return maskAddress(data);
    default:
      return data;
  }
}

/**
 * 批量脱敏对象中的敏感字段
 * @param {Object} obj - 需要脱敏的对象
 * @param {Object} fields - 字段映射 { fieldName: 'type' }
 * @returns {Object} 脱敏后的对象
 * @example
 * const user = { name: '张三', phone: '13812345678' };
 * maskObject(user, { name: 'name', phone: 'phone' });
 * // { name: '张*', phone: '138****5678' }
 */
export function maskObject(obj, fields) {
  if (!obj || typeof obj !== 'object') return obj;
  
  const maskedObj = { ...obj };
  
  Object.keys(fields).forEach(fieldName => {
    if (maskedObj[fieldName]) {
      maskedObj[fieldName] = maskData(maskedObj[fieldName], fields[fieldName]);
    }
  });
  
  return maskedObj;
}

/**
 * 批量脱敏数组中的对象
 * @param {Array} arr - 需要脱敏的数组
 * @param {Object} fields - 字段映射 { fieldName: 'type' }
 * @returns {Array} 脱敏后的数组
 * @example
 * const users = [
 *   { name: '张三', phone: '13812345678' },
 *   { name: '李四', phone: '13987654321' }
 * ];
 * maskArray(users, { name: 'name', phone: 'phone' });
 * // [
 * //   { name: '张*', phone: '138****5678' },
 * //   { name: '李*', phone: '139****4321' }
 * // ]
 */
export function maskArray(arr, fields) {
  if (!Array.isArray(arr)) return arr;
  
  return arr.map(item => maskObject(item, fields));
}

// 默认导出所有函数
export default {
  maskPhone,
  maskEmail,
  maskIdCard,
  maskName,
  maskBankCard,
  maskAddress,
  maskData,
  maskObject,
  maskArray,
  maskCustom,
  isValidPhone,
  isValidEmail,
  isValidIdCard
};

/**
 * 自定义脱敏函数
 * @param {string} data - 需要脱敏的数据
 * @param {number} start - 保留前几位
 * @param {number} end - 保留后几位
 * @param {string} mask - 脱敏字符，默认为 '*'
 * @returns {string} 脱敏后的数据
 */
export function maskCustom(data, start = 0, end = 0, mask = '*') {
  if (!data || typeof data !== 'string') return '';
  
  const len = data.length;
  if (len <= start + end) return data;
  
  const startStr = data.substring(0, start);
  const endStr = data.substring(len - end);
  const maskStr = mask.repeat(len - start - end);
  
  return startStr + maskStr + endStr;
}

/**
 * 检查是否为有效的手机号
 * @param {string} phone - 手机号
 * @returns {boolean} 是否有效
 */
export function isValidPhone(phone) {
  return /^1[3-9]\d{9}$/.test(phone);
}

/**
 * 检查是否为有效的邮箱
 * @param {string} email - 邮箱
 * @returns {boolean} 是否有效
 */
export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * 检查是否为有效的身份证号
 * @param {string} idCard - 身份证号
 * @returns {boolean} 是否有效
 */
export function isValidIdCard(idCard) {
  return /(^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}$)/.test(idCard);
}