<script setup lang="ts">
    import { useProjectStore } from '../stores/projectStore'

    const projectStore = useProjectStore()
</script>

<template>
    <div class="modal-overlay">
        <div class="modal">
            <div class="spinner-container">
                <div class="spinner"></div>
            </div>
            <h2>🎵 Добавление файла</h2>
            <p class="processing-text">Идет процесс обработки...</p>
            <p class="processing-hint">Дождитесь завершения</p>
        </div>
    </div>
</template>

<style scoped>
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 101;
    }

    .modal {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 48px 32px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        text-align: center;
    }

    .spinner-container {
        margin-bottom: 32px;
        display: flex;
        justify-content: center;
    }

    .spinner {
        width: 50px;
        height: 50px;
        border: 4px solid #d9d9d9;
        border-top-color: #81679e;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .modal h2 {
        margin: 0 0 16px 0;
        font-size: 18px;
        font-weight: 600;
        color: #1e1e1e;
    }

    .processing-text {
        margin: 0 0 8px 0;
        font-size: 16px;
        color: #1e1e1e;
        font-weight: 500;
    }

    .processing-hint {
        margin: 0;
        font-size: 14px;
        color: #807e82;
    }
</style>