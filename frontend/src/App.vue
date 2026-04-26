<script setup lang="ts">
    import { onMounted, ref } from 'vue'
    import { useProjectStore } from './stores/projectStore'
    import { connection, ensureSignalRStarted } from './signalr'
    import LeftPanel from './components/LeftPanel.vue'
    import CenterPanel from './components/CenterPanel.vue'
    import RightPanel from './components/RightPanel.vue'
    import UploadModal from './components/UploadModal.vue'
    import ProcessingModal from './components/ProcessingModal.vue'
    import SplashScreen from './components/SplashScreen.vue'
    import Header from './components/Header.vue'
    import HelpModal from './components/HelpModal.vue'
    import './style.css'

    const projectStore = useProjectStore()
    const showSplash = ref(true)
    const showHelp = ref(false)

    function hideSplash() {
        showSplash.value = false
    }

    function openHelp() {
        showHelp.value = true
    }

    function closeHelp() {
        showHelp.value = false
    }

    function goToHome() {
        window.location.href = '/'
    }

    onMounted(async () => {
        await ensureSignalRStarted()

        connection.on('JobFinished', (msg) => {
            console.log('Job finished event:', msg)
            projectStore.moveTrackToProcessed(projectStore.activeProjectId!, msg)
            projectStore.closeProcessingModal()
        })

        connection.on('JobFailed', (msg) => {
            console.log('Job failed event:', msg)
            projectStore.setTrackError(projectStore.activeProjectId!, msg)
            projectStore.closeProcessingModal()
        })
    })
</script>

<template>
    <div class="app">
        <SplashScreen :visible="showSplash" @hide="hideSplash" />
        <Header @logo-click="goToHome" @help-click="openHelp" />
        <div v-if="!showSplash" class="layout">
            <LeftPanel />
            <CenterPanel />
            <RightPanel />
        </div>
        <UploadModal v-if="projectStore.uploadModalOpen" />
        <ProcessingModal v-if="projectStore.processingModalOpen" />
        <HelpModal :visible="showHelp" @close="closeHelp" />
    </div>
</template>

<style scoped>
    .app {
        width: 100%;
        height: 100vh;
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        color: #1e1e1e;
        display: flex;
        flex-direction: column;
    }

    .layout {
        display: flex;
        width: 100%;
        flex: 1;
        gap: 16px;
        padding: 16px;
        animation: fadeIn 0.5s ease-in;
        min-height: 0;
        min-width: 0;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }

        to {
            opacity: 1;
        }
    }
</style>