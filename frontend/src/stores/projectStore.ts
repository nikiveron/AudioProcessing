import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import JSZip from 'jszip'
import { saveAs } from 'file-saver'

export interface Track {
    id: string
    filename: string
    instrument: 'Guitar' | 'Piano' | 'Vocal'
    genre: 'Classic' | 'Jazz' | 'Rock'
    duration: number
    startTime: number
    endTime: number
    inputKey: string
    outputKey?: string
    isProcessed: boolean
    isProcessing: boolean
    error?: string
    trackId: string
}

export interface Project {
    id: string
    name: string
    processedName: string
    rawTracks: Track[]
    processedTracks: Track[]
}

export const useProjectStore = defineStore('project', () => {
    const projects = ref<Project[]>([])
    const activeProjectId = ref<string | null>(null)
    const uploadModalOpen = ref(false)
    const processingModalOpen = ref(false)
    const processingTrackId = ref<string | null>(null)

    const activeProject = computed(() =>
        projects.value.find((p) => p.id === activeProjectId.value)
    )

    const activeProjectRawTracks = computed(() => activeProject.value?.rawTracks || [])
    const activeProjectProcessedTracks = computed(() => activeProject.value?.processedTracks || [])

    function createProject(name: string) {
        const newProject: Project = {
            id: `project_${Date.now()}`,
            name,
            processedName: `${name} (обработанный)`,
            rawTracks: [],
            processedTracks: [],
        }
        projects.value.push(newProject)
        activeProjectId.value = newProject.id
        return newProject
    }

    function deleteProject(projectId: string) {
        projects.value = projects.value.filter((p) => p.id !== projectId)
        if (activeProjectId.value === projectId) {
            activeProjectId.value = projects.value[0]?.id || null
        }
    }

    function setActiveProject(projectId: string) {
        activeProjectId.value = projectId
    }

    function renameProject(projectId: string, newName: string) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            project.name = newName
        }
    }

    function renameProcessedProject(projectId: string, newProcessedName: string) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            project.processedName = newProcessedName
        }
    }

    function addRawTrack(projectId: string, track: Track) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            project.rawTracks.push(track)
        }
    }

    function deleteRawTrack(projectId: string, trackId: string) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            project.rawTracks = project.rawTracks.filter((t) => t.id !== trackId)
            project.processedTracks = project.processedTracks.filter((t) => t.id !== trackId)
        }
    }

    function deleteProcessedTrack(projectId: string, trackId: string) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            project.processedTracks = project.processedTracks.filter((t) => t.id !== trackId)
            project.rawTracks = project.rawTracks.filter((t) => t.id !== trackId)
        }
    }

    function moveTrackToProcessed(projectId: string, message: any) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            const trackIndex = project.rawTracks.findIndex((t) => t.id === processingTrackId.value)
            if (trackIndex !== -1) {
                const track = project.rawTracks[trackIndex]
                track.isProcessed = true
                track.isProcessing = false
                project.processedTracks.push(track)
            }
        }
    }

    function setTrackError(projectId: string, message: any) {
        const project = projects.value.find((p) => p.id === projectId)
        if (project) {
            const track = project.rawTracks.find((t) => t.id === processingTrackId.value)
            if (track) {
                track.error = message.error
                track.isProcessing = false
            }
        }
    }

    function openUploadModal() {
        uploadModalOpen.value = true
    }

    function closeUploadModal() {
        uploadModalOpen.value = false
    }

    function openProcessingModal(trackId: string) {
        processingTrackId.value = trackId
        processingModalOpen.value = true
    }

    function closeProcessingModal() {
        processingModalOpen.value = false
        processingTrackId.value = null
    }

    async function downloadProject(projectId: string) {
        const project = projects.value.find(p => p.id === projectId)
        if (!project) return

        if (project.processedTracks.length === 0) {
            alert('В проекте нет обработанных треков')
            return
        }

        const zip = new JSZip()
        const folder = zip.folder(project.processedName || project.name)

        for (const track of project.processedTracks) {
            if (!track.outputKey) continue

            try {

                const response = await fetch(`http://localhost:5000/api/files/download?objectKey=${encodeURIComponent(track.outputKey)}`)
                const blob = await response.blob()
                folder?.file(track.filename, blob)
            } catch (err) {
                console.error('Ошибка загрузки файла:', track.filename, err)
            }
        }

        const content = await zip.generateAsync({ type: 'blob' })
        saveAs(content, `${project.processedName}.zip`)
    }

    return {
        projects,
        activeProjectId,
        uploadModalOpen,
        processingModalOpen,
        processingTrackId,
        activeProject,
        activeProjectRawTracks,
        activeProjectProcessedTracks,
        createProject,
        deleteProject,
        setActiveProject,
        renameProject,
        renameProcessedProject,
        addRawTrack,
        deleteRawTrack,
        deleteProcessedTrack,
        moveTrackToProcessed,
        setTrackError,
        openUploadModal,
        closeUploadModal,
        openProcessingModal,
        closeProcessingModal,
        downloadProject
    }
})
