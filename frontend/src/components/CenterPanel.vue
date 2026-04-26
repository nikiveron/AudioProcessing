<script setup lang="ts">
    import { ref } from 'vue'
    import { useProjectStore } from '../stores/projectStore'
    import TrackCard from './TrackCard.vue'
    import Icon from './Icon.vue'

    const projectStore = useProjectStore()
    const isEditingName = ref(false)
    const editingName = ref('')

    function startEditingName() {
        if (projectStore.activeProject) {
            editingName.value = projectStore.activeProject.name
            isEditingName.value = true
        }
    }

    function saveName() {
        if (projectStore.activeProjectId && editingName.value.trim()) {
            projectStore.renameProject(projectStore.activeProjectId, editingName.value)
            isEditingName.value = false
        }
    }

    function cancelEditingName() {
        isEditingName.value = false
    }

    function deleteTrack(trackId: string) {
        if (projectStore.activeProjectId) {
            projectStore.deleteRawTrack(projectStore.activeProjectId, trackId)
        }
    }

    function openUploadModal() {
        projectStore.openUploadModal()
    }
</script>

<template>
    <div class="center-panel">
        <div v-if="projectStore.activeProject" class="panel-content">
            <div class="panel-header">
                <div class="project-title">
                    <div v-if="!isEditingName" class="title-display">
                        <h2>{{ projectStore.activeProject.name }}</h2>
                        <button class="btn-edit" @click="startEditingName" title="Редактировать название">
                            <Icon name="edit" size="32" alt="Редактировать" />
                        </button>
                    </div>
                    <div v-else class="title-edit">
                        <input v-model="editingName"
                               type="text"
                               class="input-edit"
                               @keyup.enter="saveName"
                               @keyup.escape="cancelEditingName"
                               autofocus />
                        <button class="btn-save" @click="saveName">✓</button>
                        <button class="btn-cancel" @click="cancelEditingName">✕</button>
                    </div>
                </div>
                <div class="panel-divider"></div>
            </div>

            <div class="tracks-container">
                <div class="tracks-list">
                    <TrackCard v-for="track in projectStore.activeProjectRawTracks"
                               :key="track.id"
                               :track="track"
                               :project-id="projectStore.activeProjectId!"
                               :type="'raw'"
                               @delete="deleteTrack" />
                </div>

                <div v-if="projectStore.activeProjectRawTracks.length === 0" class="empty-state">
                    <Icon name="note" size="48" alt="Нота" class="empty-icon" />
                    <p>Нет треков в проекте</p>
                    <p class="empty-hint">Нажмите кнопку ниже, чтобы добавить треки</p>
                </div>
            </div>

            <div class="panel-footer">
                <button class="btn-add-file" @click="openUploadModal">
                    + Добавить файл
                </button>
            </div>
        </div>

        <div v-else class="no-project">
            <p>Выберите проект из левой панели</p>
        </div>
    </div>
</template>

<style scoped>
    .center-panel {
        width: 40%;
        flex: 1;
        background-color: rgba(165, 165, 170);
        border-radius: 30px;
        display: flex;
        flex-direction: column;
        padding: 20px;
        min-height: 0;
        min-width: 0;
    }

    .panel-content {
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 0;
    }

    .panel-header {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        width: 100%;
    }

    .panel-divider {
        width: 100%;
        height: 10px;
        background-color: white;
        border-radius: 10px;
        margin: 10px 0;
    }

    .project-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .title-display {
        display: flex;
        align-items: center;
        gap: 8px;
    }

        .title-display h2 {
            text-align: left;
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            color: white;
        }

    .btn-edit {
        background: none;
        border: none;
        font-size: 16px;
        cursor: pointer;
        padding: 4px 8px;
        opacity: 0.6;
        transition: opacity 0.2s;
    }

        .btn-edit:hover {
            opacity: 1;
        }

    .input-edit {
        padding: 0;
    }

    .title-edit {
        display: flex;
        gap: 8px;
        align-items: center;
        flex: 1;
    }

        .title-edit input {
            flex: 1;
            min-width: 0;
            padding: 10px 14px;
            border: 2px solid #81679e;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 500;
            background-color: #D9D9D9;
            color: #212121;
            transition: all 0.3s ease;
        }

            .title-edit input:focus {
                outline: none;
                border-color: #81679e;
                background-color: rgb(230, 230, 230);
            }

            .title-edit input::placeholder {
                color: rgba(0, 0, 0, 0.5);
            }

    .btn-save,
    .btn-cancel {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 18px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ADA0BC;
    }

    .btn-save {
        background-color: #81679e;
        color: white;
    }

        .btn-save:hover {
            background-color: #6f5587;
            transform: scale(1.05);
        }

    .btn-cancel {
        background-color: rgba(255, 255, 255, 0.2);
        color: white;
    }

        .btn-cancel:hover {
            background-color: rgba(255, 255, 255, 0.3);
            transform: scale(1.05);
        }

    .tracks-container {
        flex: 1;
        overflow-y: scroll;
        margin-bottom: 20px;
        min-height: 0;
        padding-right: 10px;
    }

        .tracks-container::-webkit-scrollbar {
            width: 10px;
        }

        .tracks-container::-webkit-scrollbar-track {
            background: rgb(217, 217, 217);
            border-radius: 10px;
        }

        .tracks-container::-webkit-scrollbar-thumb {
            background: #fff; 
            border-radius: 10px;
            border: 2px solid #888;
        }

            .tracks-container::-webkit-scrollbar-thumb:hover {
                background: #e6e6e6;
            }

    .tracks-list {
        display: flex;
        flex-direction: column;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: rgba(255, 255, 255);
        text-align: center;
    }

    .empty-icon {
        margin-bottom: 16px;
    }

    .empty-state p {
        margin: 0 0 8px 0;
        color: rgba(230, 230, 230);
        font-size: 14px;
    }

    .empty-hint {
        font-size: 12px;
        color: rgba(255, 255, 255);
        opacity: 0.8;
    }

    .panel-footer {
        margin-top: auto;
    }

    .btn-add-file {
        width: 100%;
        padding: 12px 16px;
        background-color: #81679e;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        cursor: pointer;
        transition: all 0.2s ease;
    }

        .btn-add-file:hover {
            background-color: #6f5587;
        }

    .no-project {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: rgb(245, 245, 245);
        font-size: 16px;
    }
</style>