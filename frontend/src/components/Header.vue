<script setup lang="ts">
import Icon from './Icon.vue'

interface Props {
  onLogoClick?: () => void
  onHelpClick?: () => void
}

defineProps<Props>()
</script>

<template>
  <header class="header">
    <div class="header-left">
      <Icon name="music" size="32" alt="Логотип" @click="onLogoClick"/>
      <h1 class="logo" @click="onLogoClick">SONARA AI</h1>
    </div>
    <div class="header-right">
      <button class="btn-help" @click="onHelpClick" title="Справка">?</button>
    </div>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background-color: #ffffff;
  border-bottom: 1px solid #d9d9d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #81679e;
  cursor: pointer;
  user-select: none;
  transition: opacity 0.2s;
}

.logo:hover {
  opacity: 0.8;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-help {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid #81679e;
  background-color: #ffffff;
  color: #81679e;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-help:hover {
  background-color: #81679e;
  color: #ffffff;
}

.btn-help:active {
  transform: scale(0.95);
}
</style>
