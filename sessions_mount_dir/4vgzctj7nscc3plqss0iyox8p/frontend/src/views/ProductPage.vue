<script setup>
import { ref } from 'vue';

const product = ref({
  title: '全新智能手表 Pro',
  image: 'https://via.placeholder.com/800x400',
  features: '支持心率监测、GPS定位、50米防水、7天续航',
  specs: '屏幕尺寸：1.75英寸 | 分辨率：320x320 | 重量：45g | 材质：航空级铝合金'
});
</script>

<template>
  <div class="product-page">
    <div class="product-image-container">
      <img 
        :src="product.image" 
        :alt="product.title" 
        class="product-image"
      >
    </div>

    <div class="product-details">
      <h1 class="product-title">{{ product.title }}</h1>

      <div class="description-section">
        <h2 class="section-title">核心功能</h2>
        <p class="feature-list">{{ product.features }}</p>
      </div>

      <div class="description-section">
        <h2 class="section-title">产品规格</h2>
        <p class="specs-list">{{ product.specs }}</p>
      </div>

      <router-link 
        to="/checkout" 
        class="buy-button"
        aria-label="立即购买"
      >
        立即购买
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.product-page {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 0 1.5rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.product-image-container {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.product-image {
  width: 100%;
  height: auto;
  display: block;
  transition: transform 0.3s ease;
}

.product-image:hover {
  transform: scale(1.02);
}

.product-title {
  color: #2c3e50;
  margin-bottom: 1.5rem;
  font-size: 2.2rem;
  line-height: 1.2;
}

.description-section {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.section-title {
  color: #3498db;
  margin-bottom: 0.8rem;
  font-size: 1.4rem;
  border-bottom: 2px solid #eaeaea;
  padding-bottom: 0.5rem;
}

.feature-list, .specs-list {
  color: #2c3e50;
  line-height: 1.6;
  font-size: 1.1rem;
}

.buy-button {
  display: inline-block;
  background: linear-gradient(135deg, #3498db, #1a75bc);
  color: white;
  text-decoration: none;
  padding: 1.2rem 2.5rem;
  border-radius: 50px;
  font-weight: 600;
  font-size: 1.1rem;
  text-align: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
  border: none;
  cursor: pointer;
  margin-top: 1rem;
}

.buy-button:hover {
  background: linear-gradient(135deg, #2c80b9, #1564a5);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
}

.buy-button:active {
  transform: translateY(0);
}

@media (max-width: 768px) {
  .product-page {
    padding: 0 1rem;
  }

  .product-title {
    font-size: 1.8rem;
  }

  .buy-button {
    width: 100%;
    padding: 1rem;
  }
}
</style>