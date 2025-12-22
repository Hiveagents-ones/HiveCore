/**
 * 加密工具函数，用于在客户端加密身份证号
 * 使用 AES-256-GCM 算法进行加密
 */

import CryptoJS from 'crypto-js';

// 加密密钥（实际项目中应从环境变量获取）
const ENCRYPTION_KEY = 'your-secret-encryption-key-32-chars';

/**
 * 加密身份证号
 * @param {string} idCard - 待加密的身份证号
 * @returns {string} 加密后的字符串
 */
export function encryptIdCard(idCard) {
  if (!idCard) {
    throw new Error('身份证号不能为空');
  }

  try {
    // 生成随机初始化向量
    const iv = CryptoJS.lib.WordArray.random(16);
    
    // 加密
    const encrypted = CryptoJS.AES.encrypt(idCard, CryptoJS.enc.Utf8.parse(ENCRYPTION_KEY), {
      iv: iv,
      mode: CryptoJS.mode.GCM,
      padding: CryptoJS.pad.NoPadding
    });

    // 将 IV 和加密数据组合
    const combined = iv.concat(encrypted.ciphertext);
    
    // 转换为 Base64 字符串
    return CryptoJS.enc.Base64.stringify(combined);
  } catch (error) {
    console.error('加密失败:', error);
    throw new Error('身份证号加密失败');
  }
}

/**
 * 解密身份证号（仅用于测试，生产环境不应在前端解密）
 * @param {string} encryptedData - 加密的字符串
 * @returns {string} 解密后的身份证号
 */
export function decryptIdCard(encryptedData) {
  if (!encryptedData) {
    throw new Error('加密数据不能为空');
  }

  try {
    // 解析 Base64
    const combined = CryptoJS.enc.Base64.parse(encryptedData);
    
    // 提取 IV 和加密数据
    const iv = CryptoJS.lib.WordArray.create(combined.words.slice(0, 4));
    const ciphertext = CryptoJS.lib.WordArray.create(combined.words.slice(4));
    
    // 解密
    const decrypted = CryptoJS.AES.decrypt(
      { ciphertext: ciphertext },
      CryptoJS.enc.Utf8.parse(ENCRYPTION_KEY),
      {
        iv: iv,
        mode: CryptoJS.mode.GCM,
        padding: CryptoJS.pad.NoPadding
      }
    );

    return decrypted.toString(CryptoJS.enc.Utf8);
  } catch (error) {
    console.error('解密失败:', error);
    throw new Error('身份证号解密失败');
  }
}

/**
 * 验证身份证号格式
 * @param {string} idCard - 待验证的身份证号
 * @returns {boolean} 是否有效
 */
export function validateIdCard(idCard) {
  if (!idCard) return false;
  
  // 18位身份证正则
  const regex = /^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/;
  return regex.test(idCard);
}

/**
 * 脱敏显示身份证号
 * @param {string} idCard - 身份证号
 * @returns {string} 脱敏后的身份证号
 */
export function maskIdCard(idCard) {
  if (!idCard) return '';
  
  if (idCard.length === 18) {
    return idCard.substring(0, 6) + '********' + idCard.substring(14);
  }
  
  return idCard;
}

// 默认导出所有函数
export default {
  encryptIdCard,
  decryptIdCard,
  validateIdCard,
  maskIdCard
};
