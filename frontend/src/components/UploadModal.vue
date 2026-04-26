<script setup lang="ts">
    import { ref } from 'vue'
    import { useProjectStore } from '../stores/projectStore'
    import { createTrack, startProcess } from '../api'
    import { connection, ensureSignalRStarted } from '../signalr'

    const projectStore = useProjectStore()
    const file = ref<File | null>(null)
    const instrument = ref('Guitar')
    const genre = ref('Classic')
    const loading = ref(false)
    const errorMessage = ref('')
    const fileError = ref('')
    const fileInput = ref<HTMLInputElement>()

    const SUPPORTED_TYPES = ['audio/mpeg', 'audio/wav', 'audio/x-wav']
    const SUPPORTED_EXTENSIONS = ['.mp3', '.wav']

    function selectFile() {
        fileInput.value?.click()
    }

    function onFileSelected(event: Event) {
        const target = event.target as HTMLInputElement
        const selectedFile = target.files?.[0] || null

        fileError.value = ''

        if (!selectedFile) {
            file.value = null
            return
        }

        const isSupportedType = SUPPORTED_TYPES.includes(selectedFile.type)

        const fileName = selectedFile.name.toLowerCase()
        const isSupportedExtension = SUPPORTED_EXTENSIONS.some(ext => fileName.endsWith(ext))

        if (!isSupportedType && !isSupportedExtension) {
            fileError.value = 'Тип файла не поддерживается! Выберите другой файл типа MP3 или WAV'
            file.value = null
            return
        }

        file.value = selectedFile
        errorMessage.value = ''
    }

    async function uploadAndProcess() {
        if (!file.value || !projectStore.activeProjectId) {
            errorMessage.value = 'Выберите файл и проект'
            return
        }

        loading.value = true
        errorMessage.value = ''

        try {
            // 1. Upload file
            const formData = new FormData()
            formData.append('file', file.value)

            const uploadResponse = await fetch('http://localhost:5000/api/files/upload', {
                method: 'POST',
                body: formData,
            })

            if (!uploadResponse.ok) {
                throw new Error(`Upload failed with status ${uploadResponse.status}`)
            }

            const uploadResult = await uploadResponse.json()
            console.log('File uploaded:', uploadResult)

            // 2. Create track in DB
            const track = await createTrack({
                filename: file.value.name,
                inputKey: uploadResult.inputKey,
                outputKey: uploadResult.outputKey,
            })

            console.log('Track saved in DB:', track)

            // 3. Subscribe to SignalR
            await ensureSignalRStarted()
            await connection.invoke('SubscribeToJob', track.outputKey)

            // 4. Add track to project
            const newTrack = {
                id: `track_${Date.now()}`,
                filename: file.value.name,
                instrument: instrument.value as 'Guitar' | 'Piano' | 'Vocal',
                genre: genre.value as 'Classic' | 'Jazz' | 'Rock',
                startTime: 0,
                inputKey: uploadResult.inputKey,
                outputKey: uploadResult.outputKey,
                isProcessed: false,
                isProcessing: true,
                trackId: track.trackId,
            }

            projectStore.addRawTrack(projectStore.activeProjectId, newTrack)
            projectStore.openProcessingModal(newTrack.id)

            // 5. Map enum to numbers
            const genreEnumMap: Record<string, number> = { Classic: 0, Jazz: 1, Rock: 2 }
            const instrumentEnumMap: Record<string, number> = { Guitar: 0, Piano: 1, Vocal: 2 }

            // 6. Start processing
            const processResult = await startProcess({
                trackId: track.trackId,
                genre: genreEnumMap[genre.value],
                instrument: instrumentEnumMap[instrument.value],
            })

            console.log('Process started:', processResult)
            projectStore.closeUploadModal()
        } catch (error) {
            console.error('Error:', error)
            errorMessage.value = error instanceof Error ? error.message : 'Unknown error'
            loading.value = false
        }
    }

    function closeModal() {
        projectStore.closeUploadModal()
    }

    function getTruncatedFileName(): string {
        if (!file.value) return 'Загрузить файл'
        const fileName = file.value.name
        const maxLength = 37
        return fileName.length > maxLength ? fileName.slice(0, maxLength) + '...' : fileName
    }
</script>

<template>
    <div class="modal-overlay" @click="closeModal">
        <div class="modal" @click.stop>
            <div class="modal-header">
                <div class="modal-title">
                    <Icon name="note" size="16" alt="Трек" />
                    <h2>Добавить файл</h2>
                </div>
                <button class="btn-close" @click="closeModal">✕</button>
            </div>

            <div class="modal-content">
                <div class="form-group">
                    <label>Имя файла</label>
                    <div class="file-input-wrapper">
                        <button class="file-input-btn" @click="selectFile">
                            {{ getTruncatedFileName() }}
                        </button>
                        <input ref="fileInput"
                               type="file"
                               accept="audio/mpeg,audio/wav,.mp3,.wav"
                               @change="onFileSelected"
                               style="display: none" />
                    </div>
                    <div v-if="fileError" class="file-error-message">
                        {{ fileError }}
                    </div>
                </div>

                <div class="form-group">
                    <label>Инструмент</label>
                    <select v-model="instrument" class="select-input">
                        <option value="Guitar">Guitar</option>
                        <option value="Piano">Piano</option>
                        <option value="Vocal">Vocal</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Жанр</label>
                    <select v-model="genre" class="select-input">
                        <option value="Classic">Classic</option>
                        <option value="Jazz">Jazz</option>
                        <option value="Rock">Rock</option>
                    </select>
                </div>

                <div v-if="errorMessage" class="error-message">
                    {{ errorMessage }}
                </div>
            </div>

            <div class="modal-footer">
                <button class="btn-process" @click="uploadAndProcess" :disabled="loading || !file">
                    {{ loading ? 'Загрузка...' : 'Обработать файл' }}
                </button>
                <button class="btn-cancel" @click="closeModal" :disabled="loading">Отмена</button>
            </div>
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
        z-index: 100;
    }

    .modal {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 32px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
    }

        .modal-header h2 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: #1e1e1e;
        }

    .btn-close {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        opacity: 0.6;
        transition: opacity 0.2s;
    }

        .btn-close:hover {
            opacity: 1;
        }

    .modal-content {
        margin-bottom: 24px;
    }

    .form-group {
        margin-bottom: 16px;
    }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #1e1e1e;
            font-size: 14px;
        }

    .file-input-wrapper {
        position: relative;
    }

    .file-error-message {
        color: #cc0000;
        font-size: 12px;
        margin-top: 8px;
        padding: 8px 12px;
        background-color: #ffe0e0;
        border: 1px solid #ff9999;
        border-radius: 6px;
        text-align: left;
    }

    .file-input-btn {
        width: 100%;
        padding: 10px;
        padding-right: 20px;
        background-color: #ada0bc;
        border: none;
        border-radius: 15px;
        font-size: 21px;
        color: white;
        cursor: pointer;
        text-align: left;
        transition: all 0.2s;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        display: block;
    }

        .file-input-btn:hover {
            background-color: #9b8eaa;
        }

        .file-input-btn:focus {
            box-shadow: 0 0 0 3px rgba(129,103,158,0.35);
        }

    .select-input {
        width: 100%;
        padding: 12px 60px 12px 16px;
        background-color: #ada0bc;
        border: none !important;
        outline: none;
        border-radius: 15px;
        font-size: 21px;
        color: white;
        cursor: pointer;
        transition: all 0.2s ease;
        appearance: none;
        -webkit-appearance: none;
        -moz-appearance: none;
        background-image: url("data:image/svg+xml;utf8, <svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'> <polyline points='6 9 12 15 18 9'/> </svg>");
        background-repeat: no-repeat;
        background-position: right 30px center;
    }

        .select-input:hover {
            background-color: #9b8eaa;
        }

        .select-input:focus {
            box-shadow: 0 0 0 3px rgba(129,103,158,0.35);
        }

        .select-input option {
            background: #ffffff;
            color: #1e1e1e;
            padding: 12px;
            border-radius: 10px;
            font-size: 16px;
        }

            .select-input option:hover {
                background: #81679e;
                color: white;
            }

            .select-input option:checked {
                background: #81679e;
                color: white;
            }

    select {
        border: none !important;
    }

        select:focus {
            outline: none;
        }

    .error-message {
        background-color: #ffe0e0;
        border: 1px solid #ff9999;
        border-radius: 6px;
        padding: 12px;
        font-size: 14px;
        color: #cc0000;
        margin-top: 16px;
    }

    .modal-footer {
        display: flex;
        gap: 12px;
    }

    .btn-process,
    .btn-cancel {
        flex: 1;
        padding: 12px 16px;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .btn-process {
        background-color: #81679e;
        color: white;
    }

        .btn-process:hover:not(:disabled) {
            background-color: #6f5587;
        }

        .btn-process:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

    .btn-cancel {
        background-color: #6a696c;
        color: white;
    }

        .btn-cancel:hover:not(:disabled) {
            background-color: #5a595c;
        }

        .btn-cancel:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
</style>