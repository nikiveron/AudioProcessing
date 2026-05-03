<script setup lang="ts">
    import type { Track } from '../stores/projectStore'
    import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
    import Icon from './Icon.vue'

    interface Props {
        track: Track
        projectId: string
        type: string
        onDelete?: (trackId: string) => void
        onProcess?: (trackId: string) => void
    }

    const props = defineProps<Props>()
    const emit = defineEmits<{
        delete: [trackId: string]
        process: [trackId: string]
    }>()

    const audioRef = ref<HTMLAudioElement | null>(null)
    const isPlaying = ref(false)
    const isMuted = ref(false)
    const volume = ref(1)
    const currentTime = ref(0)
    const duration = ref(0)
    let objectUrl: string | null = null

    function audioUrl() {
        const t = props.track as Track & { inputKey?: string; outputKey?: string }
        if (props.type === 'processed') return `http://localhost:5000/api/files/download?objectKey=${encodeURIComponent(t.outputKey)}`
        if (props.type === 'raw') return `http://localhost:5000/api/files/download?objectKey=${encodeURIComponent(t.inputKey)}`
        return ''
    }

    async function fetchAndSetSource(a: HTMLAudioElement, url: string) {
        try {
            // try to fetch the file as blob first (helps detect HTTP errors / content-type)
            const res = await fetch(url)
            if (!res.ok) {
                console.error('Ошибка получения аудиофайла', res.status, res.statusText)
                // fallback: set URL directly (may still fail)
                a.src = url
                try { a.load() } catch { }
                return
            }

            const ct = res.headers.get('content-type') || ''
            if (!ct.startsWith('audio/')) {
                console.warn('Тип контента аудио не соответствует audio/*:', ct)
                // still try to use as blob
            }

            const blob = await res.blob()
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl)
                objectUrl = null
            }
            objectUrl = URL.createObjectURL(blob)
            a.src = objectUrl
            try { a.load() } catch { }
        } catch (err) {
            console.error('Не удалось получить аудиоресурс, используем прямой URL', err)
            a.src = url
            try { a.load() } catch { }
        }
    }

    async function togglePlay() {
        const a = audioRef.value
        if (!a) return

        if (!a.src) {
            const src = audioUrl()
            if (!src) {
                console.warn('Нет аудиоресурса для трека', props.track.id)
                return
            }
            await fetchAndSetSource(a, src)
        }

        if (isPlaying.value) {
            a.pause()
        } else {
            try {
                await a.play()
            } catch (err) {
                console.error('Ошибка воспроизведения:', err)
                console.error('Если появляется NotSupportedError, проверьте вкладку сети: возвращает ли сервер 200 и Content-Type audio/*? Если вы видите HTML или 404, настройте backend. Также проверьте заголовки CORS.')
            }
        }
    }

    function toggleMute() {
        const a = audioRef.value
        if (!a) return
        isMuted.value = !isMuted.value
        a.muted = isMuted.value
    }

    function onTimeUpdate() {
        const a = audioRef.value
        if (!a) return
        currentTime.value = a.currentTime
    }

    function onLoadedMetadata() {
        const a = audioRef.value
        if (!a) return
        duration.value = a.duration || 0
    }

    function onEnded() {
        isPlaying.value = false
    }

    async function seekTo(val: number) {
        const a = audioRef.value
        if (!a) return
        if (!a.src) {
            const src = audioUrl()
            if (src) await fetchAndSetSource(a, src)
        }
        a.currentTime = val
        currentTime.value = val
    }

    function changeVolume(val: number) {
        const a = audioRef.value
        if (!a) return
        volume.value = val
        a.volume = val
    }

    function downloadTrack() {
        const url = audioUrl()
        if (!url) return
        // use fetch to get blob then download to ensure we download actual file
        fetch(url)
            .then((res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                return res.blob()
            })
            .then((blob) => {
                const link = document.createElement('a')
                const blobUrl = URL.createObjectURL(blob)
                link.href = blobUrl
                const name = props.track.filename || 'track.wav'
                link.download = name
                document.body.appendChild(link)
                link.click()
                link.remove()
                setTimeout(() => URL.revokeObjectURL(blobUrl), 2000)
            })
            .catch((err) => {
                console.error('Не удалось скачать трек:', err)
                // fallback: open direct url
                const link = document.createElement('a')
                link.href = url
                link.download = props.track.filename || 'track.wav'
                document.body.appendChild(link)
                link.click()
                link.remove()
            })
    }

    onMounted(() => {
        const a = audioRef.value
        if (!a) return
        a.addEventListener('timeupdate', onTimeUpdate)
        a.addEventListener('loadedmetadata', onLoadedMetadata)
        a.addEventListener('play', () => (isPlaying.value = true))
        a.addEventListener('pause', () => (isPlaying.value = false))
        a.addEventListener('ended', onEnded)
        a.addEventListener('error', (ev) => {
            console.error('Audio element error event', (ev.currentTarget as HTMLMediaElement).error)
        })
        a.muted = isMuted.value
        a.volume = volume.value

        // if there is already a key, prefetch source to avoid play errors
        const src = audioUrl()
        if (src) {
            // don't await
            fetchAndSetSource(a, src).catch((e) => console.warn('Не удалось предварительно загрузить аудиофайл', e))
        }
    })

    onUnmounted(() => {
        const a = audioRef.value
        if (a) {
            a.pause()
            a.src = ''
        }
        if (objectUrl) {
            URL.revokeObjectURL(objectUrl)
            objectUrl = null
        }
    })

    watch(() => props.track.inputKey || props.track.outputKey, () => {
        const a = audioRef.value
        if (!a) return
        const src = audioUrl()
        if (src) {
            fetchAndSetSource(a, src).catch((e) => console.warn('Не удалось предварительно загрузить аудиофайл при наблюдении за изменением ключа', e))
        }
    })
</script>

<template>
    <div class="track-card">
            <Icon :name="track.instrument" size="100" :alt="track.instrument" class="track-icon"/>
            <div class="track-content">
                <div class="track-header">
                    <div class="track-info">
                        <h3 class="track-name">{{ track.filename }}</h3>
                        <div v-if="track.error" class="error-status">Ошибка: {{ track.error }}</div>
                        <div v-else-if="track.isProcessing" class="processing-status">Обработка...</div>
                    </div>
                    <button class="control-btn" @click="emit('delete', track.id)" title="Удалить">
                        <Icon name="trash" size="18" alt="Удалить" />
                    </button>
                </div>

                <audio ref="audioRef" preload="metadata"></audio>

                <div class="timeline">
                    <input type="range"
                           class="timeline-slider"
                           :min="0"
                           :max="duration || 0"
                           step="0.01"
                           :value="currentTime"
                           @input="(e) => seekTo(Number((e.target as HTMLInputElement).value))" />
                    <div class="timeline-times">
                        <span class="time">{{ currentTime.toFixed(2) }}</span>
                        <span class="time">{{ duration ? duration.toFixed(2) : '0.00' }}</span>
                    </div>
                </div>

                <div class="controls">
                    <div class="volume-control">
                        <input type="range" class="timeline-slider" min="0" max="1" step="0.01" :value="volume" @input="(e) => changeVolume(Number((e.target as HTMLInputElement).value))" />
                    </div>
                    <button class="control-btn" @click="toggleMute" :title="isMuted ? 'Включить звук' : 'Заглушить'">
                        <Icon :name="isMuted ? 'volume-up' : 'volume-mute'" size="20" :alt="isMuted ? 'Включить' : 'Заглушить'" />
                    </button>
                    <button class="control-btn" @click="togglePlay" :title="isPlaying ? 'Пауза' : 'Воспроизвести'">
                        <Icon :name="isPlaying ? 'pause' : 'play'" size="20" :alt="isPlaying ? 'Пауза' : 'Воспроизвести'" />
                    </button>
                    <button class="control-btn" @click="downloadTrack" title="Скачать">
                        <Icon name="download" size="20" alt="Скачать" />
                    </button>
                </div>
            </div>
    </div>
</template>

<style scoped>
    .track-card {
        display: flex;
        align-items: center;
        background-color: #81679e;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        color: white;
        width: 100%;
        overflow: hidden;
    }

    .track-icon {
        margin-right: 20px;
        margin-left: 10px;
        flex-shrink: 0;
    }

    .track-header {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .instrument-icon {
        font-size: 32px;
        min-width: 40px;
        text-align: center;
    }

    .track-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-width: 0;
        gap: 8px;
    }

    .track-info {
        flex: 1;
        min-width: 0;
    }

    .track-name {
        margin: 0 0 4px 0;
        font-size: 21px;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 100%;
        min-width: 0;
    }

    .error-status,
    .processing-status {
        font-size: 12px;
        opacity: 0.8;
        margin-top: 4px;
    }

    .error-status {
        color: #ffcccc;
    }

    .processing-status {
        color: #fff3cd;
    }

    .timeline-slider {
        -webkit-appearance: none;
        width: 100%;
        height: 6px;
        background: #ffffff;
        border-radius: 4px;
        outline: none;
    }

        .timeline-slider::-webkit-slider-runnable-track {
            height: 6px;
            background: #D9D9D9;
            border-radius: 4px;
        }

        .timeline-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #ffffff;
            cursor: pointer;
            margin-top: -5px;
        }

    .timeline-times {
        display: flex;
        justify-content: space-between;
        margin-top: 6px;
        font-size: 15px;
        opacity: 0.9;
    }

    .controls {
        display: flex;
        gap: 8px;
        justify-content: center;
    }

    .control-btn {
        width: 40px;
        height: 40px;
        background-color: rgba(170,160,188,0.8);
        border: none;
        border-radius: 20px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        cursor: pointer;
        color: white;
    }

        .control-btn:hover {
            opacity: 1;
        }

    .volume-control {
        margin-top: 10px;
    }

        .volume-control input {
            width: 100%;
        }
</style>