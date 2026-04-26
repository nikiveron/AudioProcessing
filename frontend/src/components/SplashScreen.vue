<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Props {
  visible: boolean
}

defineProps<Props>()
const emit = defineEmits<{
  hide: []
}>()

const isVisible = ref(true)

onMounted(() => {
  // Start fade out animation after 2.5 seconds
  // (fade lasts 0.5s, so total is 3s)
  setTimeout(() => {
    isVisible.value = false
    // Emit event to parent after fade animation completes
    setTimeout(() => {
      emit('hide')
    }, 500)
  }, 2500)
})
</script>

<template>
  <transition name="splash-fade">
    <div v-if="visible && isVisible" class="splash-screen">
      <img src="/preview.jpg" alt="background" class="splash-background" />
      <div class="splash-overlay"></div>
      <div class="splash-content">
        <h1 class="splash-title">SONARA AI</h1>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.splash-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.splash-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.splash-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1;
}

.splash-content {
  position: relative;
  z-index: 2;
  text-align: center;
}

.splash-title {
  font-size: 64px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  letter-spacing: 4px;
  animation: pulse-title 2.5s ease-in-out;
}

@keyframes pulse-title {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Fade out transition */
.splash-fade-enter-active {
  transition: opacity 0.5s ease-out;
}

.splash-fade-leave-active {
  transition: opacity 0.5s ease-out;
}

.splash-fade-enter-from {
  opacity: 0;
}

.splash-fade-leave-to {
  opacity: 0;
}
</style>
