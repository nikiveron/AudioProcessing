<script setup lang="ts">
    import { ref } from 'vue'
    import { useProjectStore } from '../stores/projectStore'
    import Icon from './Icon.vue'

    const projectStore = useProjectStore()
    const newProjectName = ref('')
    const showNewProjectInput = ref(false)

    function addProject() {
        if (newProjectName.value.trim()) {
            projectStore.createProject(newProjectName.value)
            newProjectName.value = ''
            showNewProjectInput.value = false
        }
    }

    function selectProject(projectId: string) {
        projectStore.setActiveProject(projectId)
    }

    function deleteProjectConfirm(projectId: string) {
        if (confirm('Вы уверены, что хотите удалить этот проект?')) {
            projectStore.deleteProject(projectId)
        }
    }
</script>

<template>
    <div class="left-panel">
        <div class="panel-header">
            <h2>Все проекты</h2>
            <div class="panel-divider"></div>
        </div>

        <div class="projects-list">
            <div v-for="project in projectStore.projects"
                 :key="project.id"
                 :class="['project-item', { active: projectStore.activeProjectId === project.id }]"
                 @click="selectProject(project.id)">
                <div class="project-header">
                    <Icon name="folder" size="32" alt="Папка" />
                    <span class="project-name">{{ project.name }}</span>
                </div>
                <div class="tracks-list">
                    <div v-for="track in project.rawTracks" :key="track.id" class="track-item">
                        <Icon name="note" size="16" alt="Трек" />
                        <span class="track-name">{{ track.filename }}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="panel-footer">
            <div v-if="!showNewProjectInput" class="add-project">
                <button class="btn-primary" @click="showNewProjectInput = true">+ Добавить проект</button>
            </div>
            <div v-else class="new-project-input">
                <input v-model="newProjectName"
                       type="text"
                       placeholder="Название проекта"
                       @keyup.enter="addProject"
                       @keyup.escape="showNewProjectInput = false"
                       autofocus />
                <button @click="addProject" class="btn-confirm">✓</button>
                <button @click="showNewProjectInput = false" class="btn-cancel">✕</button>
            </div>
        </div>
    </div>
</template>

<style scoped>
    .left-panel {
        width: 20%;
        background-color: rgba(165, 165, 170);
        border-radius: 30px;
        display: flex;
        flex-direction: column;
        padding: 20px;
        min-height: 0;
        min-width: 0;
    }

    .panel-header {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        width: 100%;
    }

        .panel-header h2 {
            text-align: left;
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            color: white;
        }

    .panel-divider {
        width: 100%;
        height: 10px;
        background-color: white;
        border-radius: 10px;
        margin: 10px 0;
    }

    .icon-btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px;
    }

        .icon-btn:hover {
            opacity: 0.7;
        }

    .projects-list {
        flex: 1;
        overflow-y: auto;
        margin-bottom: 20px;
    }

    .project-item {
        background-color: rgba(105, 105, 110, 0.8);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        color: white;
    }

        .project-item.active {
            background-color: #81679e;
            color: white;
        }

    .project-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }

    .project-name {
        font-weight: 600;
        font-size: 21px;
        color: white;
    }

    .tracks-list {
        margin-left: 40px;
        font-size: 15px;
        color: rgba(255, 255, 255, 0.8);
    }

    .track-item {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 4px;
        padding: 4px 0;
        opacity: 0.9;
    }

    .track-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .panel-footer {
        margin-top: auto;
    }

    .add-project {
        display: flex;
    }

    .btn-primary {
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

        .btn-primary:hover {
            background-color: #6f5587;
        }

    .new-project-input {
        display: flex;
        gap: 8px;
        align-items: center;
    }

        .new-project-input input {
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

            .new-project-input input:focus {
                outline: none;
                border-color: #81679e;
                background-color: rgb(230, 230, 230);
            }

            .new-project-input input::placeholder {
                color: rgba(0, 0, 0, 0.5);
            }

    .btn-confirm,
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

    .btn-confirm {
        background-color: #81679e;
        color: white;
    }

        .btn-confirm:hover {
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
</style>
